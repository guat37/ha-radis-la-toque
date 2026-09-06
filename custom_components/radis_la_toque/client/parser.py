"""Pure parsing helpers for Radis la Toque HTML and menu PDF text."""
from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import date
import re
import unicodedata
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .exceptions import MenuParseError, RestaurantNotFound
from .models import DayMenu, MenuCategory, MenuItem, Restaurant

DAY_NAMES = {"lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"}
MONTHS = {"janvier":1,"fevrier":2,"mars":3,"avril":4,"mai":5,"juin":6,"juillet":7,"aout":8,"septembre":9,"octobre":10,"novembre":11,"decembre":12}
DATE_RE = re.compile(r"(?im)\b(?P<weekday>lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b\s*(?:[-:–—]?\s*)?(?P<day>\d{1,2})(?:er)?\s+(?P<month>[A-Za-zÀ-ÿ]+)(?:\s+(?P<year>20\d{2}))?")
CODE_RE = re.compile(r"/restaurants/(?P<code>R\d+)", re.I)
ENTRY_RE = re.compile(r"/les-menus-de-la-cantine/liste-des-restaurants/entry-", re.I)
ENTRY_ID_RE = re.compile(r"/entry-(?P<id>\d+)(?:-|\.html|/|$)", re.I)
POSTAL_RE = re.compile(r"\b(?P<postal>\d{5})\b")

CATEGORY_ALIASES = {
    MenuCategory.STARTER: ("entree", "entrées", "entrees"),
    MenuCategory.MAIN_COURSE: ("plat", "plat principal", "plats"),
    MenuCategory.SIDE: ("garniture", "accompagnement", "legume", "féculent", "feculent"),
    MenuCategory.DAIRY: ("produit laitier", "fromage", "laitage"),
    MenuCategory.DESSERT: ("dessert", "fruit"),
}
NOISE_PREFIXES = ("radis la toque", "restoria", "origine", "allerg", "menu susceptible", "sous reserve", "sous réserve")
KNOWN_LABELS = ("bio", "local", "label rouge", "aop", "igp", "msc", "hve")

def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"\s+", " ", value).strip()

def parse_listing_page(html: str, page_url: str) -> list[Restaurant]:
    """Parse one restaurant listing page using local DOM proximity.

    The live website does not expose a stable semantic card wrapper.  Walking
    up the DOM from the ``Voir la fiche`` link can therefore reach a common
    list container and associate several restaurants with the first postal
    code on the page.  Instead, anchor each result on the fiche link itself
    and use the *nearest preceding* heading and postal-code text node.

    This matches the rendered sequence used by the site:

        <heading>Restaurant name</heading>
        address
        CITY - 12345
        <a ...entry-...>Voir la fiche</a>
    """
    soup = BeautifulSoup(html, "html.parser")
    found: dict[str, Restaurant] = {}

    for link in soup.find_all("a", href=True):
        href = str(link.get("href", "")).strip()
        link_text = normalize(link.get_text(" ", strip=True))

        # Be tolerant of absolute/relative URL variants and minor CMS path
        # changes.  The stable public characteristic is the entry-* fiche URL.
        if "entry-" not in href.casefold():
            continue
        if "liste-des-restaurants" not in href.casefold() and link_text != "voir la fiche":
            continue

        absolute = urljoin(page_url, href)

        # The closest preceding heading belongs to this card on the live site.
        heading = link.find_previous(["h2", "h3", "h4"])
        name = heading.get_text(" ", strip=True) if heading else ""

        # Likewise, the closest preceding text node containing a French postal
        # code is the location line of this restaurant.  This avoids relying on
        # a card wrapper that the CMS does not guarantee.
        location_node = link.find_previous(string=POSTAL_RE)
        location_text = re.sub(r"\s+", " ", str(location_node)).strip() if location_node else ""
        postal_match = POSTAL_RE.search(location_text)
        postal = postal_match.group("postal") if postal_match else ""

        city = ""
        if postal_match:
            before = location_text[:postal_match.start()].strip(" -–—,|")
            # Common live forms are either ``CITY - 12345`` or
            # ``12345 - City``.  First try the text preceding the postcode.
            if before:
                parts = re.split(r"\s+[-–—]\s+", before)
                city = parts[-1].strip(" -–—,|")
            else:
                after = location_text[postal_match.end():].strip(" -–—,|")
                if after:
                    city = after.split(" - ", 1)[0].strip()

        # Fallback to slug only if the heading could not be identified.
        if not name or normalize(name) in {"voir la fiche", "fiche", "liste des restaurants"}:
            slug = absolute.rsplit("/", 1)[-1]
            name = re.sub(r"^entry-\d+-|\.html$", "", slug, flags=re.I).replace("-", " ").title()

        # Collect a compact address hint from text between the heading and the
        # location line when possible.  It is optional and never used as an ID.
        address = None
        if heading is not None and location_node is not None:
            candidates: list[str] = []
            node = heading.next_element
            while node is not None and node is not link and node is not location_node:
                if isinstance(node, str):
                    value = re.sub(r"\s+", " ", node).strip()
                    if value and normalize(value) not in {normalize(name), "voir la fiche"}:
                        if not POSTAL_RE.search(value):
                            candidates.append(value)
                node = getattr(node, "next_element", None)
                if len(candidates) > 6:
                    break
            if candidates:
                address = " ".join(dict.fromkeys(candidates))[:255]

        found[absolute] = Restaurant(None, name, address, city, postal, absolute)

    return list(found.values())

def infer_last_catalog_page(html: str) -> int:
    """Return the real last catalog page, not only the visible pager window.

    The site displays a sliding pagination window (for example 43..53 while
    browsing page 48).  Taking max(all visible page numbers) truncates the
    catalog.  The "last"/">>" control, however, points to the actual final
    page, so prefer it whenever present.
    """
    soup = BeautifulSoup(html, "html.parser")
    last_candidates: list[int] = []
    all_pages: list[int] = []
    for link in soup.find_all("a", href=True):
        match = re.search(r"(?:^|/)page-(\d+)\.html(?:$|[?#])", str(link["href"]))
        if not match:
            continue
        page = int(match.group(1))
        all_pages.append(page)
        text = normalize(link.get_text(" ", strip=True))
        title = normalize(str(link.get("title", "")))
        aria = normalize(str(link.get("aria-label", "")))
        rel = " ".join(link.get("rel", [])) if isinstance(link.get("rel"), list) else str(link.get("rel", ""))
        marker = f"{text} {title} {aria} {normalize(rel)}"
        if text in {">>", "»"} or any(word in marker for word in ("last", "dernier", "fin")):
            last_candidates.append(page)
    if last_candidates:
        return max(last_candidates)
    return max(all_pages, default=1)


def restaurant_id_from_url(url: str) -> str:
    """Return the stable CMS entry identifier for a restaurant fiche URL.

    The public ``Rxxxxx`` menu code is not stable: RESTORIA can rotate it while
    the restaurant fiche (``entry-1234-...``) remains the same.
    """
    match = ENTRY_ID_RE.search(url)
    if not match:
        raise RestaurantNotFound("restaurant_entry_id_not_found")
    return f"entry-{match.group('id')}"

def parse_restaurant_page(html: str, restaurant: Restaurant) -> Restaurant:
    code_match = CODE_RE.search(html)
    if not code_match:
        raise RestaurantNotFound("restaurant_code_not_found")
    soup = BeautifulSoup(html, "html.parser")
    address = None
    heading = soup.find(["h1", "h2"], string=re.compile(re.escape(restaurant.name), re.I))
    if heading:
        nxt = heading.find_next(string=POSTAL_RE)
        if nxt:
            address = re.sub(r"\s+", " ", str(nxt)).strip() or None
    return replace(restaurant, code=code_match.group("code").upper(), address=address)

def _parse_date(match: re.Match[str], today: date) -> date:
    month = MONTHS.get(normalize(match.group("month")))
    if month is None:
        raise MenuParseError("unsupported_month")
    day = int(match.group("day"))
    year_text = match.group("year")
    if year_text:
        return date(int(year_text), month, day)
    candidates = [date(today.year + offset, month, day) for offset in (-1, 0, 1)]
    return min(candidates, key=lambda value: abs((value - today).days))

def _category_from_line(line: str) -> MenuCategory | None:
    n = normalize(line).rstrip(" :")
    for category, aliases in CATEGORY_ALIASES.items():
        if any(n == normalize(alias) for alias in aliases):
            return category
    return None

def _clean_item(raw: str, category: MenuCategory) -> MenuItem | None:
    line = re.sub(r"^[•·▪►*\-–—]+\s*", "", re.sub(r"\s+", " ", raw)).strip()
    if len(line) < 2:
        return None
    n = normalize(line)
    if n in DAY_NAMES or any(n.startswith(normalize(p)) for p in NOISE_PREFIXES):
        return None
    labels = tuple(label for label in KNOWN_LABELS if re.search(rf"\b{re.escape(normalize(label))}\b", n))
    return MenuItem(line[:255], category, labels)






# ---------------------------------------------------------------------------
# Word/geometry parser (preferred)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class PdfWord:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.top + self.bottom) / 2


def _join_words(words: list[PdfWord]) -> str:
    if not words:
        return ""
    # pdfplumber uses top-origin coordinates. Group words by baseline, then
    # read each line left-to-right and lines top-to-bottom.
    lines: list[list[PdfWord]] = []
    for word in sorted(words, key=lambda w: (w.top, w.x0)):
        line = next((ln for ln in lines if abs(ln[0].top - word.top) <= 3.0), None)
        if line is None:
            lines.append([word])
        else:
            line.append(word)
    parts: list[str] = []
    for line in sorted(lines, key=lambda ln: ln[0].top):
        txt = " ".join(w.text.strip() for w in sorted(line, key=lambda w: w.x0) if w.text.strip())
        if txt:
            parts.append(txt)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _is_category_text(text: str) -> MenuCategory | None:
    n = normalize(text).strip(' :')
    if n == 'entree' or n.startswith('entree '):
        return MenuCategory.STARTER
    if n == 'plat' or n.startswith('plat principal'):
        return MenuCategory.MAIN_COURSE
    if n == 'garniture' or n.startswith('garniture ') or n.startswith('accompagnement'):
        return MenuCategory.SIDE
    if n == 'produit' or n.startswith('produit laitier') or n.startswith('laitage'):
        return MenuCategory.DAIRY
    if n == 'dessert' or n.startswith('dessert '):
        return MenuCategory.DESSERT
    return None


def menu_quality_score(days: tuple[DayMenu, ...]) -> int:
    """Return a conservative semantic quality score for a parsed menu.

    The score rewards distinct meal categories rather than raw item count. This
    prevents a geometrically shifted parse from looking healthy merely because
    it produced several text fragments. Repeated rows (e.g. two starter choices)
    are allowed and do not reduce the score.
    """
    if not days:
        return 0
    score = 0
    for day in days:
        categories = {
            item.category for item in day.items if item.category != MenuCategory.OTHER
        }
        other_count = sum(1 for item in day.items if item.category == MenuCategory.OTHER)
        score += 10 + len(categories) * 10
        if len(categories) >= 3:
            score += 10
        if len(categories) >= 4:
            score += 10
        if len(categories) >= 5:
            score += 20
        score -= other_count * 3
    return max(score, 0)


def _quality_ok(days: tuple[DayMenu, ...]) -> bool:
    """Reject partial/ambiguous parses instead of publishing wrong meals."""
    if not days:
        return False
    good_days = 0
    total_categories = 0
    for day in days:
        cats = {item.category for item in day.items if item.category != MenuCategory.OTHER}
        total_categories += len(cats)
        if len(cats) >= 3 and len(day.items) >= 3:
            good_days += 1
    return (
        good_days >= max(1, (len(days) + 1) // 2)
        and total_categories >= max(3, len(days) * 3)
        and menu_quality_score(days) >= len(days) * 45
    )


def parse_menu_words(
    pages: tuple[tuple[PdfWord, ...], ...], *, today: date | None = None
) -> tuple[DayMenu, ...]:
    """Parse current Radis la Toque menu PDFs from positioned words.

    This avoids relying on pdfplumber's table-cell reconstruction, which can
    merge/split cells inconsistently. We derive weekday columns from the
    header itself and category row bands from the left-side labels.
    """
    today = today or date.today()
    by_date: dict[date, DayMenu] = {}

    for words_tuple in pages:
        words = [w for w in words_tuple if w.text.strip()]
        if not words:
            continue

        # Header weekdays and short dates. Restrict to upper half to avoid legend text.
        page_bottom = max((w.bottom for w in words), default=0.0)
        upper = [w for w in words if w.top < page_bottom * 0.55]
        weekday_words = [w for w in upper if normalize(w.text) in DAY_NAMES]
        date_words = [w for w in upper if SHORT_DATE_RE.match(w.text.strip())]
        if len(weekday_words) < 2 or len(date_words) < 2:
            continue

        weekday_words.sort(key=lambda w: w.x0)
        columns: list[tuple[str, date, float]] = []
        used: set[int] = set()
        for wd in weekday_words[:7]:
            candidates = [(i, d) for i, d in enumerate(date_words) if i not in used]
            if not candidates:
                break
            i, d = min(candidates, key=lambda it: abs(it[1].cx - wd.cx) + abs(it[1].top - wd.bottom) * 0.05)
            used.add(i)
            try:
                menu_date = _date_from_short(d.text.strip(), today)
            except Exception:
                continue
            columns.append((wd.text.capitalize(), menu_date, (wd.cx + d.cx) / 2))
        columns.sort(key=lambda x: x[2])
        if len(columns) < 2:
            continue

        centers = [c[2] for c in columns]
        mids = [(a+b)/2 for a,b in zip(centers, centers[1:])]
        # extrapolate sensible outer bounds from inter-column spacing
        left_gap = (centers[1]-centers[0]) / 2 if len(centers) > 1 else 60
        right_gap = (centers[-1]-centers[-2]) / 2 if len(centers) > 1 else 60
        x_bounds = [centers[0]-left_gap, *mids, centers[-1]+right_gap]

        # Find category anchors in the left area. Multi-word labels are often split.
        first_col_left = x_bounds[0]
        left_words = [w for w in words if w.x1 < first_col_left + 8]
        anchors: list[tuple[MenuCategory, float]] = []
        # cluster left words into visual lines
        line_groups: list[list[PdfWord]] = []
        for w in sorted(left_words, key=lambda w: (w.top, w.x0)):
            ln = next((ln for ln in line_groups if abs(ln[0].top-w.top) <= 4), None)
            if ln is None: line_groups.append([w])
            else: ln.append(w)
        for ln in line_groups:
            txt = _join_words(ln)
            cat = _is_category_text(txt)
            if cat is not None:
                anchors.append((cat, sum(w.cy for w in ln)/len(ln)))
        # handle labels split across two lines: Plat/principal, Produit/laitier
        for w in left_words:
            cat = _is_category_text(w.text)
            if cat is not None and not any(a[0] == cat and abs(a[1]-w.cy) < 8 for a in anchors):
                anchors.append((cat, w.cy))
        dedup: dict[MenuCategory,float] = {}
        for cat,y in sorted(anchors, key=lambda x:x[1]):
            dedup.setdefault(cat,y)
        anchors = sorted(dedup.items(), key=lambda x:x[1])
        if len(anchors) < 3:
            continue

        # header bottom is below weekday/date labels; footer begins after last category row.
        header_bottom = max(w.bottom for w in weekday_words + date_words)
        row_ys = [y for _,y in anchors]
        row_bounds: list[float] = [header_bottom + 2]
        row_bounds.extend((a+b)/2 for a,b in zip(row_ys,row_ys[1:]))
        # Last row ends before legend/footer. Generous extension based on previous row spacing.
        last_gap = (row_ys[-1]-row_ys[-2]) if len(row_ys)>1 else 45
        row_bounds.append(row_ys[-1] + max(20, last_gap*0.7))

        day_items: list[list[MenuItem]] = [[] for _ in columns]
        for ridx,(cat,_) in enumerate(anchors):
            y0,y1 = row_bounds[ridx], row_bounds[ridx+1]
            for cidx in range(len(columns)):
                x0,x1 = x_bounds[cidx], x_bounds[cidx+1]
                cell_words = [
                    w for w in words
                    if w.cx >= x0 and w.cx < x1 and w.cy >= y0 and w.cy < y1
                ]
                value = _join_words(cell_words)
                item = _clean_item(value, cat) if value else None
                if item:
                    day_items[cidx].append(item)

        for idx,(weekday,menu_date,_) in enumerate(columns):
            items = tuple(day_items[idx])
            if items:
                by_date[menu_date] = DayMenu(menu_date, f"{weekday} {menu_date:%d/%m}", items)

    days = tuple(by_date[k] for k in sorted(by_date))
    return days if _quality_ok(days) else ()


# ---------------------------------------------------------------------------
# Table parser (preferred)
# ---------------------------------------------------------------------------
# Current Radis la Toque PDFs are generated by TCPDF and contain a real ruled
# table.  pdfplumber can recover that table directly, which is considerably
# more robust than inferring cells from individual text-fragment coordinates.

TABLE_HEADER_RE = re.compile(
    r"(?i)\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b.*?(\d{1,2}/\d{1,2}(?:/\d{2,4})?)"
)

def _clean_table_cell(value: str | None) -> str:
    if not value:
        return ""
    # Keep ordinary punctuation/accents, but remove pictogram glyphs and
    # private-use characters injected by the PDF icon font.
    chars: list[str] = []
    for ch in str(value).replace("\r", "\n"):
        cat = unicodedata.category(ch)
        if cat in {"Co", "So"}:
            continue
        chars.append(ch)
    text = "".join(chars)
    # Drop isolated icon-font artefacts while retaining meaningful words.
    parts = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        if len(line) == 1 and not line.isalnum():
            continue
        parts.append(line)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()

def _category_from_cell(value: str | None) -> MenuCategory | None:
    n = normalize(_clean_table_cell(value)).strip(" :")
    if not n:
        return None
    if n == "entree" or n.startswith("entree "):
        return MenuCategory.STARTER
    if n == "plat" or n.startswith("plat principal"):
        return MenuCategory.MAIN_COURSE
    if n == "garniture" or n.startswith("garniture ") or n.startswith("accompagnement"):
        return MenuCategory.SIDE
    if n == "produit" or n.startswith("produit laitier") or n.startswith("laitage"):
        return MenuCategory.DAIRY
    if n == "dessert" or n.startswith("dessert "):
        return MenuCategory.DESSERT
    return None

def _header_day(value: str | None, today: date) -> tuple[str, date] | None:
    text = _clean_table_cell(value)
    match = TABLE_HEADER_RE.search(text)
    if not match:
        return None
    weekday = match.group(1).capitalize()
    try:
        menu_date = _date_from_short(match.group(2), today)
    except (ValueError, MenuParseError):
        return None
    return weekday, menu_date

def parse_menu_tables(
    tables: tuple[tuple[tuple[str | None, ...], ...], ...], *, today: date | None = None
) -> tuple[DayMenu, ...]:
    """Parse semantic tables extracted from Radis la Toque PDFs.

    pdfplumber may omit the empty top-left header cell.  Consequently the
    header can contain five cells (Mon..Fri) while category rows contain six
    cells (label + five meals).  Do not reuse raw header column indexes for
    category rows.  Instead, detect the category-label cell independently and
    map the following meal cells sequentially to the detected day headers.
    """
    today = today or date.today()
    by_date: dict[date, DayMenu] = {}

    for table in tables:
        if not table:
            continue

        # Locate the row carrying weekday/date cells.  Some PDFs expose one
        # leading empty cell, others don't; both forms are intentionally valid.
        header_idx: int | None = None
        header_days: list[tuple[str, date]] = []
        for idx, row in enumerate(table[:6]):
            found: list[tuple[str, date]] = []
            for cell in row:
                parsed = _header_day(cell, today)
                if parsed:
                    found.append(parsed)
            if len(found) >= 2:
                header_idx = idx
                header_days = found
                break

        if header_idx is None:
            continue

        # Preserve visual left-to-right order from the extracted row.  A normal
        # school week has 4 or 5 columns, but 2..7 keeps atypical templates safe.
        header_days = header_days[:7]
        day_items: list[list[MenuItem]] = [[] for _ in header_days]
        category_rows = 0

        previous_category: MenuCategory | None = None
        previous_label_idx: int | None = None

        for row in table[header_idx + 1:]:
            cells = list(row)
            if not cells:
                continue

            # Find an explicit category label wherever pdfplumber put it.
            # Several Radis la Toque templates use an *unlabelled continuation
            # row* for a second starter/dairy/dessert choice.  In that case the
            # first cell is empty and the row must inherit the immediately
            # preceding category without shifting day columns.
            label_idx: int | None = None
            category: MenuCategory | None = None
            for idx, cell in enumerate(cells):
                cat = _category_from_cell(cell)
                if cat is not None:
                    label_idx = idx
                    category = cat
                    break

            if label_idx is None or category is None:
                # Only inherit when the previous category exists and the cell
                # at the previous label position is blank.  This deliberately
                # refuses arbitrary legend/footer rows.
                if previous_category is None or previous_label_idx is None:
                    continue
                if previous_label_idx >= len(cells):
                    continue
                if _clean_table_cell(cells[previous_label_idx]):
                    continue
                label_idx = previous_label_idx
                category = previous_category
            else:
                previous_category = category
                previous_label_idx = label_idx
                category_rows += 1

            meal_cells = cells[label_idx + 1:]

            # Preserve intentional empty menu cells: an empty Monday must not
            # shift Tuesday into Monday. Only discard *surplus* leading blanks
            # when the extracted row has more cells than the header requires.
            while (
                len(meal_cells) > len(header_days)
                and meal_cells
                and not _clean_table_cell(meal_cells[0])
            ):
                meal_cells.pop(0)

            # If a malformed extraction still has too many cells, align from
            # the left after the category label. Never compact internal blanks.
            for day_idx, cell in enumerate(meal_cells[: len(header_days)]):
                value = _clean_table_cell(cell)
                if not value:
                    continue
                item = _clean_item(value, category)
                if item:
                    day_items[day_idx].append(item)

        if category_rows < 2:
            continue

        for day_idx, (weekday, menu_date) in enumerate(header_days):
            items = tuple(day_items[day_idx])
            if not items:
                continue
            by_date[menu_date] = DayMenu(
                menu_date,
                f"{weekday} {menu_date:%d/%m}",
                items,
            )

    days = tuple(by_date[key] for key in sorted(by_date))
    return days if _quality_ok(days) else ()



def decorate_menu_table(
    rows: tuple[tuple[str | None, ...], ...],
    row_bounds: tuple[tuple[float, float], ...],
    left_words: tuple[PdfWord, ...],
    *,
    today: date | None = None,
) -> tuple[tuple[str | None, ...], ...] | None:
    """Inject external category labels into a ruled menu table.

    Current Radis la Toque PDFs draw the five day columns as a ruled table,
    while the category labels (Entrée, Plat principal, Garniture, Produit
    laitier, Dessert) are printed *outside* that table in the left margin.
    ``pdfplumber.extract_table()`` therefore returns only the day cells.

    This helper associates those left-margin labels with the physical table
    row that contains them, then prepends a synthetic category-label column.
    Rows without an explicit label are deliberately left blank so
    ``parse_menu_tables`` can inherit the previous category for alternate
    choices.
    """
    if not rows or len(rows) != len(row_bounds):
        return None
    today = today or date.today()

    # Accept only a real menu header. This prevents title/footer tables from
    # being decorated accidentally.
    header_matches = sum(1 for cell in rows[0] if _header_day(cell, today))
    if header_matches < 2:
        return None

    # Alternate/synthetic templates may already include the category-label
    # column inside the ruled grid. Preserve those tables unchanged.
    explicit_categories = sum(
        1
        for row in rows[1:]
        if any(_category_from_cell(cell) is not None for cell in row)
    )
    if explicit_categories >= 3:
        return rows

    labels: list[str | None] = [None] * len(rows)
    for word in left_words:
        category = _is_category_text(word.text)
        if category is None:
            continue
        cy = word.cy
        for row_idx, (top, bottom) in enumerate(row_bounds):
            if row_idx == 0:
                continue
            if top - 2.0 <= cy <= bottom + 2.0:
                # The first distinctive word is enough for split labels such
                # as ``Plat`` / ``principal`` and ``Produit`` / ``laitier``.
                labels[row_idx] = word.text.strip()
                break

    # A trustworthy current-template table must expose at least three meal
    # category anchors. Four-category menus (no dairy) are valid.
    if sum(label is not None for label in labels[1:]) < 3:
        return None

    decorated: list[tuple[str | None, ...]] = []
    decorated.append((None, *rows[0]))
    for idx, row in enumerate(rows[1:], start=1):
        decorated.append((labels[idx], *row))
    return tuple(decorated)

# ---------------------------------------------------------------------------
# PDF layout parser
# ---------------------------------------------------------------------------
# Radis la Toque's current PDF is a table: weekdays are columns and meal
# categories are rows.  Plain text extraction destroys that structure, so the
# primary parser consumes positioned PDF text fragments.  The older linear
# parser below is retained as a fallback for historical/alternate templates.


@dataclass(frozen=True, slots=True)
class PdfTextFragment:
    """One text fragment extracted from a PDF page with its text matrix position."""
    text: str
    x: float
    y: float

SHORT_DATE_RE = re.compile(r"^(?P<day>\d{1,2})/(?P<month>\d{1,2})(?:/(?P<year>\d{2,4}))?$")
WEEKDAY_ORDER = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")


def _date_from_short(value: str, today: date) -> date:
    match = SHORT_DATE_RE.match(value.strip())
    if not match:
        raise MenuParseError("invalid_short_date")
    day = int(match.group("day"))
    month = int(match.group("month"))
    year_text = match.group("year")
    if year_text:
        year = int(year_text)
        if year < 100:
            year += 2000
        return date(year, month, day)
    candidates = [date(today.year + offset, month, day) for offset in (-1, 0, 1)]
    return min(candidates, key=lambda candidate: abs((candidate - today).days))


def _merge_fragments(fragments: list[PdfTextFragment]) -> str:
    """Join cell fragments in visual reading order."""
    if not fragments:
        return ""
    # PDF Y coordinates normally increase from bottom to top.  Group fragments
    # on approximately the same baseline, then read rows from top to bottom.
    rows: list[list[PdfTextFragment]] = []
    for frag in sorted(fragments, key=lambda f: (-f.y, f.x)):
        row = next((row for row in rows if abs(row[0].y - frag.y) <= 3.5), None)
        if row is None:
            rows.append([frag])
        else:
            row.append(frag)
    parts: list[str] = []
    for row in rows:
        text = " ".join(
            re.sub(r"\s+", " ", frag.text).strip()
            for frag in sorted(row, key=lambda f: f.x)
            if re.sub(r"\s+", " ", frag.text).strip()
        )
        if text:
            parts.append(text)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _category_anchor(fragment: PdfTextFragment) -> MenuCategory | None:
    n = normalize(fragment.text).strip(" :")
    # Current TCPDF template often splits the two-word labels into separate
    # fragments/lines, so matching the first distinctive word is intentional.
    if n == "entree" or n.startswith("entree "):
        return MenuCategory.STARTER
    if n == "plat" or n.startswith("plat principal"):
        return MenuCategory.MAIN_COURSE
    if n == "garniture" or n.startswith("garniture "):
        return MenuCategory.SIDE
    if n == "produit" or n.startswith("produit laitier"):
        return MenuCategory.DAIRY
    if n == "dessert" or n.startswith("dessert "):
        return MenuCategory.DESSERT
    return None


def _parse_menu_page_layout(
    fragments: tuple[PdfTextFragment, ...], *, today: date
) -> tuple[DayMenu, ...]:
    """Parse one table-formatted Radis la Toque PDF page."""
    cleaned = tuple(
        PdfTextFragment(re.sub(r"\s+", " ", f.text).strip(), f.x, f.y)
        for f in fragments
        if re.sub(r"\s+", " ", f.text).strip()
    )
    if not cleaned:
        return ()

    weekdays = [f for f in cleaned if normalize(f.text) in DAY_NAMES]
    dates = [f for f in cleaned if SHORT_DATE_RE.match(f.text.strip())]
    if len(weekdays) < 2 or len(dates) < 2:
        return ()

    # A page normally has one weekday header row. Keep the uppermost coherent
    # group to avoid matching weekday words in footer/legal copy.
    weekdays.sort(key=lambda f: (-f.y, f.x))
    header_y = weekdays[0].y
    header = [f for f in weekdays if abs(f.y - header_y) <= 8.0]
    if len(header) < 2:
        # TCPDF may place each label on slightly different baselines; use the
        # first seven weekday fragments before the date row as a fallback.
        header = weekdays[:7]
    header.sort(key=lambda f: f.x)

    # Associate each weekday with the nearest date below it in the same column.
    columns: list[tuple[PdfTextFragment, PdfTextFragment]] = []
    used_dates: set[int] = set()
    for weekday in header:
        candidates = [
            (idx, d) for idx, d in enumerate(dates)
            if idx not in used_dates and d.y <= weekday.y + 10
        ]
        if not candidates:
            candidates = [(idx, d) for idx, d in enumerate(dates) if idx not in used_dates]
        if not candidates:
            continue
        idx, date_frag = min(
            candidates,
            key=lambda pair: abs(pair[1].x - weekday.x) + 0.15 * abs(pair[1].y - weekday.y),
        )
        used_dates.add(idx)
        columns.append((weekday, date_frag))
    columns.sort(key=lambda pair: pair[0].x)
    if len(columns) < 2:
        return ()

    # Column boundaries are halfway between weekday anchors.  The left bound
    # deliberately starts before the first weekday because cell text can be
    # slightly left-aligned relative to its header.
    centers = [pair[0].x for pair in columns]
    boundaries: list[float] = [-float("inf")]
    boundaries.extend((a + b) / 2 for a, b in zip(centers, centers[1:]))
    boundaries.append(float("inf"))

    category_frags = [(f, _category_anchor(f)) for f in cleaned]
    category_frags = [(f, cat) for f, cat in category_frags if cat is not None]
    if len(category_frags) < 2:
        return ()

    # Category labels live to the left of the meal columns.  Prefer those
    # anchors and discard accidental food text such as "plat" inside a cell.
    first_center = centers[0]
    left_anchors = [(f, cat) for f, cat in category_frags if f.x < first_center]
    if len(left_anchors) >= 2:
        category_frags = left_anchors

    # One anchor per category, in visual top-to-bottom order.
    anchors_by_category: dict[MenuCategory, PdfTextFragment] = {}
    for frag, cat in sorted(category_frags, key=lambda pair: -pair[0].y):
        anchors_by_category.setdefault(cat, frag)
    anchors = sorted(((frag, cat) for cat, frag in anchors_by_category.items()), key=lambda pair: -pair[0].y)
    if len(anchors) < 2:
        return ()

    header_floor = min(pair[1].y for pair in columns)
    day_items: list[list[MenuItem]] = [[] for _ in columns]

    for anchor_idx, (anchor, category) in enumerate(anchors):
        upper = header_floor if anchor_idx == 0 else (anchors[anchor_idx - 1][0].y + anchor.y) / 2
        lower = (
            (anchor.y + anchors[anchor_idx + 1][0].y) / 2
            if anchor_idx + 1 < len(anchors)
            else anchor.y - max(35.0, abs(anchors[-2][0].y - anchor.y) * 0.75)
        )
        if upper < lower:
            upper, lower = lower, upper

        # Ignore the category-label column and footer/legend text.  Assign each
        # remaining fragment by its starting X coordinate to the nearest day.
        for col_idx in range(len(columns)):
            left, right = boundaries[col_idx], boundaries[col_idx + 1]
            cell = [
                f for f in cleaned
                if lower <= f.y <= upper
                and left <= f.x < right
                and f.x >= first_center - 8
                and not SHORT_DATE_RE.match(f.text.strip())
                and normalize(f.text) not in DAY_NAMES
                and _category_anchor(f) is None
            ]
            value = _merge_fragments(cell)
            if not value:
                continue
            # Stop obvious footer/legend bleed if a last-row band is generous.
            n = normalize(value)
            for marker in ("legende des groupes alimentaires", "legende de nos engagements", "restoria se reserve"):
                pos = n.find(marker)
                if pos >= 0:
                    value = value[:pos].strip()
                    break
            item = _clean_item(value, category)
            if item:
                day_items[col_idx].append(item)

    result: list[DayMenu] = []
    for idx, (weekday_frag, date_frag) in enumerate(columns):
        try:
            menu_date = _date_from_short(date_frag.text, today)
        except (ValueError, MenuParseError):
            continue
        weekday = weekday_frag.text.strip().capitalize()
        label = f"{weekday} {date_frag.text.strip()}"
        items = tuple(day_items[idx])
        # A valid page can legitimately have an empty cell for one category,
        # but a completely empty day is likely a layout parsing failure.
        if items:
            result.append(DayMenu(menu_date, label, items))
    return tuple(result)


def parse_menu_layout(
    pages: tuple[tuple[PdfTextFragment, ...], ...], *, today: date | None = None
) -> tuple[DayMenu, ...]:
    """Parse positioned PDF text from all pages, de-duplicating menu dates."""
    today = today or date.today()
    by_date: dict[date, DayMenu] = {}
    for page in pages:
        for day in _parse_menu_page_layout(page, today=today):
            by_date[day.menu_date] = day
    return tuple(by_date[key] for key in sorted(by_date))




def select_menu_parse(
    tables: tuple[tuple[tuple[str | None, ...], ...], ...],
    word_pages: tuple[tuple[PdfWord, ...], ...],
    layout_pages: tuple[tuple[PdfTextFragment, ...], ...],
    text: str,
    *,
    today: date | None = None,
) -> tuple[tuple[DayMenu, ...], str, int]:
    """Select a trustworthy parse without publishing heuristic guesses.

    Current Radis la Toque documents are ruled TCPDF tables. Semantic table
    extraction is therefore authoritative. Geometry-based parsers are kept in
    the module for diagnostics/development but are intentionally *not* used in
    production selection: synthetic regression tests show that a shifted
    geometry parse can look complete while assigning text to the wrong meal
    category.

    The only independent fallback accepted is the historical linear text
    format using long French dates (e.g. ``Lundi 7 septembre``), which is
    structurally distinct from the current short-date table format.
    """
    today = today or date.today()

    table_days = parse_menu_tables(tables, today=today)
    if table_days:
        return table_days, "table", menu_quality_score(table_days)

    # Historical/alternate non-tabular template. DATE_RE deliberately does
    # not match the current JJ/MM headers, so this cannot accidentally flatten
    # a current table into a plausible-but-wrong menu.
    if DATE_RE.search(text):
        try:
            legacy_days = parse_menu_text(text, today=today)
        except MenuParseError:
            legacy_days = ()
        if _quality_ok(legacy_days):
            return legacy_days, "legacy_text", menu_quality_score(legacy_days)

    raise MenuParseError("menu_structure_not_recognized")


def parse_menu_text(text: str, *, today: date | None = None) -> tuple[DayMenu, ...]:
    today = today or date.today()
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.replace("\r", "\n").splitlines()]
    lines = [line for line in lines if line]
    normalized = "\n".join(lines)
    matches = list(DATE_RE.finditer(normalized))
    if not matches:
        raise MenuParseError("menu_dates_not_found")
    days: list[DayMenu] = []
    for idx, match in enumerate(matches):
        block = normalized[match.end():(matches[idx+1].start() if idx+1 < len(matches) else len(normalized))]
        current_category = MenuCategory.OTHER
        items: list[MenuItem] = []
        for raw in block.splitlines():
            category = _category_from_line(raw)
            if category is not None:
                current_category = category
                continue
            item = _clean_item(raw, current_category)
            if item and item.name not in {existing.name for existing in items}:
                items.append(item)
        days.append(DayMenu(_parse_date(match, today), match.group(0).strip(), tuple(items[:20])))
    return tuple(days)
