"""Asynchronous HTTP client for the public Radis la Toque website."""
from __future__ import annotations
import asyncio
import logging
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Final
from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout
from pypdf import PdfReader
import pdfplumber
from ..const import BASE_URL, CATALOG_CONCURRENCY, LIST_URL, MAX_CATALOG_PAGES, PDF_URL, REQUEST_TIMEOUT, RESTAURANT_URL, USER_AGENT
from .exceptions import CannotConnect, InvalidPdf, MenuNotAvailable, MenuParseError, RestaurantNotFound
from .models import Restaurant, WeeklyMenu
_LOGGER = logging.getLogger(__name__)

from .parser import (
    PdfTextFragment,
    PdfWord,
    decorate_menu_table,
    infer_last_catalog_page,
    normalize,
    parse_listing_page,
    select_menu_parse,
    parse_restaurant_page,
    restaurant_id_from_url,
)

@dataclass(slots=True)
class _DocumentCache:
    etag: str | None = None
    last_modified: str | None = None
    menu: WeeklyMenu | None = None

class RadisLaToqueClient:
    """Small, dependency-injected async client."""
    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._timeout = ClientTimeout(total=REQUEST_TIMEOUT)
        self._headers: Final = {"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.8"}
        self._catalog_cache: tuple[Restaurant, ...] | None = None
        self._document_cache: dict[str, _DocumentCache] = {}

    async def _request(self, url: str, *, headers: dict[str, str] | None = None) -> ClientResponse:
        merged = dict(self._headers)
        if headers:
            merged.update(headers)
        try:
            response = await self._session.get(url, headers=merged, timeout=self._timeout)
            if response.status >= 500:
                response.release()
                raise CannotConnect(f"server_error:{response.status}")
            return response
        except (ClientError, asyncio.TimeoutError) as err:
            raise CannotConnect(url) from err

    async def _get_text(self, url: str) -> str:
        response = await self._request(url)
        async with response:
            if response.status == 404:
                raise RestaurantNotFound(url)
            if response.status >= 400:
                raise CannotConnect(f"http_{response.status}")
            return await response.text(errors="replace")

    async def async_catalog(self, *, force: bool = False) -> tuple[Restaurant, ...]:
        """Fetch and cache the public restaurant catalog.

        The website currently redirects the unpaginated catalog URL (and the
        trailing-slash variant) back to the generic menu landing page.  That
        page contains no restaurant entries.  The first reliable listing URL
        is ``page-2.html``.  Start there, discover the real final page from the
        pager's last control, then fetch pages 3..N.  Deliberately never request
        page 1: on the live site it resolves to the non-listing landing page.
        """
        if self._catalog_cache is not None and not force:
            return self._catalog_cache

        seed_page = 2
        seed_url = f"{LIST_URL}/page-{seed_page}.html"
        seed_html = await self._get_text(seed_url)
        seed_restaurants = parse_listing_page(seed_html, seed_url)
        if not seed_restaurants:
            raise RestaurantNotFound("restaurant_catalog_seed_empty")

        last_page = min(
            max(infer_last_catalog_page(seed_html), seed_page),
            MAX_CATALOG_PAGES,
        )

        semaphore = asyncio.Semaphore(CATALOG_CONCURRENCY)

        async def fetch(page: int) -> list[Restaurant]:
            async with semaphore:
                url = f"{LIST_URL}/page-{page}.html"
                try:
                    html = await self._get_text(url)
                except RestaurantNotFound:
                    # A missing individual catalog page must not make the
                    # complete discovery unusable.  This also protects us from
                    # harmless holes if the CMS pagination changes.
                    return []
                return parse_listing_page(html, url)

        # Page 2 is already parsed.  The live catalog starts there; page 1 is
        # intentionally excluded because it redirects to the landing page.
        pages = await asyncio.gather(
            *(fetch(page) for page in range(seed_page + 1, last_page + 1))
        )

        by_url = {restaurant.page_url: restaurant for restaurant in seed_restaurants}
        for restaurants in pages:
            by_url.update({restaurant.page_url: restaurant for restaurant in restaurants})

        if not by_url:
            raise RestaurantNotFound("restaurant_catalog_empty")

        self._catalog_cache = tuple(
            sorted(by_url.values(), key=lambda restaurant: restaurant.label.casefold())
        )
        _LOGGER.debug("Loaded %d Radis la Toque restaurants from pages %d..%d", len(self._catalog_cache), seed_page, last_page)
        return self._catalog_cache

    async def async_find_restaurants(self, query: str) -> list[Restaurant]:
        needle = normalize(query)
        if len(needle) < 2:
            return []
        catalog = await self.async_catalog()
        raw_query = query.strip()
        exact_postal = raw_query.isdigit() and len(raw_query) == 5
        tokens = tuple(token for token in needle.split(" ") if token)
        results = []
        for restaurant in catalog:
            haystack = normalize(f"{restaurant.name} {restaurant.address or ''} {restaurant.postal_code} {restaurant.city}")
            # Multi-word searches do not need to be contiguous or in exactly
            # the same order as the website label.
            if all(token in haystack for token in tokens):
                results.append(restaurant)
        _LOGGER.debug("Radis la Toque search %r matched %d/%d restaurants", query, len(results), len(catalog))
        return sorted(
            results,
            key=lambda r: (
                0 if exact_postal and r.postal_code == raw_query else 1,
                0 if needle == normalize(r.city) else 1,
                r.label.casefold(),
            ),
        )[:100]

    async def async_resolve_restaurant(self, restaurant: Restaurant) -> Restaurant:
        return parse_restaurant_page(await self._get_text(restaurant.page_url), restaurant)

    async def async_resolve_code(self, page_url: str) -> str:
        """Resolve the current volatile Rxxxxx menu code from a stable fiche URL."""
        restaurant_id_from_url(page_url)  # validate stable fiche URL early
        html = await self._get_text(page_url)
        match = re.search(r"/restaurants/(?P<code>R\d+)", html, re.I)
        if not match:
            raise RestaurantNotFound("restaurant_code_not_found")
        return match.group("code").upper()

    async def async_validate_restaurant(self, code: str) -> None:
        html = await self._get_text(RESTAURANT_URL.format(code=code))
        if not html.strip():
            raise MenuNotAvailable("empty_restaurant_page")

    async def async_get_menu(self, code: str, name: str, *, today=None) -> WeeklyMenu:
        """Fetch a menu using HTTP validators and return cached data on 304."""
        url = PDF_URL.format(code=code)
        cache = self._document_cache.setdefault(code, _DocumentCache())
        conditional: dict[str, str] = {}
        if cache.etag:
            conditional["If-None-Match"] = cache.etag
        if cache.last_modified:
            conditional["If-Modified-Since"] = cache.last_modified
        response = await self._request(url, headers=conditional)
        async with response:
            if response.status == 304 and cache.menu is not None:
                return cache.menu
            if response.status == 404:
                raise MenuNotAvailable(code)
            if response.status >= 400:
                raise CannotConnect(f"http_{response.status}")
            payload = await response.read()
            content_type = response.headers.get("Content-Type", "").lower()
            if not payload.startswith(b"%PDF") and "pdf" not in content_type:
                raise MenuNotAvailable("response_is_not_pdf")
            tables, word_pages, pages, text = await asyncio.to_thread(self._extract_pdf_content, payload)

            if self._document_has_no_menu_content(text):
                raise MenuNotAvailable("menu_not_published")

            days, parser_kind, score = select_menu_parse(
                tables, word_pages, pages, text, today=today
            )
            _LOGGER.debug(
                "Parsed Radis la Toque menu %s with %s parser: %d day(s), score=%d",
                code,
                parser_kind,
                len(days),
                score,
            )
            menu = WeeklyMenu(
                code,
                name,
                url,
                days,
                response.headers.get("ETag"),
                response.headers.get("Last-Modified"),
                parser_kind,
                score,
            )
            cache.etag = menu.document_etag
            cache.last_modified = menu.document_last_modified
            cache.menu = menu
            return menu


    @staticmethod
    def _document_has_no_menu_content(text: str) -> bool:
        """Return True only for a conservative blank-menu PDF template.

        RESTORIA can return a valid PDF shell containing branding/legal text but
        no actual menu grid.  Treat that as "no menu published", not as an
        unsupported menu format.  The detection is deliberately conservative:
        any weekday, menu date, or meal-category marker keeps the document on
        the normal parser path so a new/changed layout is never silently hidden.
        """
        normalized = normalize(text)
        if re.search(r"\b(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b", normalized):
            return False
        if re.search(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", normalized):
            return False
        category_markers = (
            "entree",
            "plat principal",
            "garniture",
            "accompagnement",
            "produit laitier",
            "laitage",
            "dessert",
        )
        if any(marker in normalized for marker in category_markers):
            return False
        return True

    @staticmethod
    def _extract_pdf_content(
        payload: bytes,
    ) -> tuple[
        tuple[tuple[tuple[str | None, ...], ...], ...],
        tuple[tuple[PdfWord, ...], ...],
        tuple[tuple[PdfTextFragment, ...], ...],
        str,
    ]:
        """Extract decorated semantic tables, positioned words and text.

        In the live RESTORIA PDF template the ruled grid contains only the
        weekday columns; category labels are printed in the left margin.
        Preserve the table geometry long enough to associate those labels
        with their physical rows before passing the table to the pure parser.
        """
        try:
            extracted_tables: list[tuple[tuple[str | None, ...], ...]] = []
            extracted_word_pages: list[tuple[PdfWord, ...]] = []
            with pdfplumber.open(BytesIO(payload)) as pdf:
                table_settings = (
                    {
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                        "snap_tolerance": 4,
                        "join_tolerance": 4,
                        "intersection_tolerance": 6,
                        "text_tolerance": 3,
                    },
                    {
                        "vertical_strategy": "lines_strict",
                        "horizontal_strategy": "lines_strict",
                        "snap_tolerance": 5,
                        "join_tolerance": 5,
                        "intersection_tolerance": 7,
                        "text_tolerance": 3,
                    },
                )
                seen_tables: set[tuple[tuple[str | None, ...], ...]] = set()
                for page in pdf.pages:
                    raw_words = page.extract_words(
                        x_tolerance=2,
                        y_tolerance=2,
                        keep_blank_chars=False,
                        use_text_flow=False,
                    ) or []
                    page_words = tuple(
                        PdfWord(
                            str(w.get("text", "")),
                            float(w.get("x0", 0.0)),
                            float(w.get("x1", 0.0)),
                            float(w.get("top", 0.0)),
                            float(w.get("bottom", 0.0)),
                        )
                        for w in raw_words
                        if str(w.get("text", "")).strip()
                    )
                    extracted_word_pages.append(page_words)

                    for settings in table_settings:
                        for table in page.find_tables(table_settings=settings) or []:
                            raw_table = table.extract(x_tolerance=2, y_tolerance=2)
                            if not raw_table:
                                continue
                            rows = tuple(
                                tuple(cell for cell in row)
                                for row in raw_table
                                if row
                            )
                            if not rows or len(rows) != len(table.rows):
                                continue

                            row_bounds: list[tuple[float, float]] = []
                            valid_geometry = True
                            for table_row in table.rows:
                                cells = [cell for cell in table_row.cells if cell is not None]
                                if not cells:
                                    valid_geometry = False
                                    break
                                row_bounds.append((
                                    min(float(cell[1]) for cell in cells),
                                    max(float(cell[3]) for cell in cells),
                                ))
                            if not valid_geometry:
                                continue

                            table_left = float(table.bbox[0])
                            table_top = float(table.bbox[1])
                            table_bottom = float(table.bbox[3])
                            left_words = tuple(
                                word for word in page_words
                                if word.x1 < table_left - 1.0
                                and word.top >= table_top - 5.0
                                and word.bottom <= table_bottom + 5.0
                            )
                            decorated = decorate_menu_table(
                                rows,
                                tuple(row_bounds),
                                left_words,
                            )
                            if decorated and decorated not in seen_tables:
                                seen_tables.add(decorated)
                                extracted_tables.append(decorated)

            reader = PdfReader(BytesIO(payload))
            pages: list[tuple[PdfTextFragment, ...]] = []
            plain_pages: list[str] = []
            for page in reader.pages:
                fragments: list[PdfTextFragment] = []

                def visitor(text, cm, tm, font_dict, font_size):
                    if not text or not text.strip():
                        return
                    x = float(tm[4]) * float(cm[0]) + float(tm[5]) * float(cm[2]) + float(cm[4])
                    y = float(tm[4]) * float(cm[1]) + float(tm[5]) * float(cm[3]) + float(cm[5])
                    for part in text.replace("\r", "\n").split("\n"):
                        part = part.strip()
                        if part:
                            fragments.append(PdfTextFragment(part, x, y))

                plain = page.extract_text(visitor_text=visitor) or ""
                plain_pages.append(plain.strip())
                pages.append(tuple(fragments))
        except Exception as err:
            raise InvalidPdf("invalid_pdf") from err

        text = "\n".join(filter(None, plain_pages))
        if not text.strip():
            raise InvalidPdf("empty_pdf_text")
        return tuple(extracted_tables), tuple(extracted_word_pages), tuple(pages), text
