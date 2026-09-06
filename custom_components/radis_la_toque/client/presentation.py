"""Pure presentation helpers shared by Home Assistant entities.

This module deliberately has no Home Assistant dependency so the menu selection
and rendering rules can be regression-tested against real PDF fixtures.
"""
from __future__ import annotations

from datetime import date, timedelta

from .models import DayMenu, MenuCategory, WeeklyMenu

_CATEGORY_ORDER = (
    MenuCategory.STARTER,
    MenuCategory.MAIN_COURSE,
    MenuCategory.SIDE,
    MenuCategory.DAIRY,
    MenuCategory.DESSERT,
    MenuCategory.OTHER,
)

_CATEGORY_ICONS = {
    MenuCategory.STARTER: "🥗",
    MenuCategory.MAIN_COURSE: "🍽️",
    MenuCategory.SIDE: "🥕",
    MenuCategory.DAIRY: "🧀",
    MenuCategory.DESSERT: "🍎",
    MenuCategory.OTHER: "•",
}


def _normalize_semantic(value: str) -> str:
    """Normalize a menu item for conservative semantic matching."""
    import re
    import unicodedata
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"\s+", " ", value).strip()


def _contains_term(haystack: str, term: str) -> bool:
    import re
    token = _normalize_semantic(term)
    return re.search(rf"(?<!\w){re.escape(token)}(?!\w)", haystack) is not None


def _semantic_labels(name: str, category: MenuCategory) -> list[str]:
    """Derive generic labels after parsing, never affecting parser success."""
    import re
    n = _normalize_semantic(name)
    labels: list[str] = []

    def add(label: str) -> None:
        if label not in labels:
            labels.append(label)

    if re.search(r"\bbio\b", n): add("organic")
    if re.search(r"\blocal(?:e|es|aux)?\b", n): add("local")
    if "label rouge" in n: add("label_rouge")
    for raw in ("aop", "igp", "msc", "hve"):
        if re.search(rf"\b{raw}\b", n): add(raw)
    if "fait maison" in n or " maison" in f" {n}": add("home_made")

    meat=("boeuf","veau","porc","poulet","dinde","canard","agneau","jambon","lardon","lardons","saucisse","chipolata","chipolatas","merguez","palette","steak","hachis","salami","mortadelle","chorizo")
    fish=("poisson","colin","saumon","thon","cabillaud","merlu","lieu","haddock","sardine","maquereau","calamar","calamars","crevette","crevettes")
    eggs=("oeuf","oeufs","omelette")
    dairy=("lait","yaourt","yogourt","fromage","camembert","coulommiers","chanteneige","cantadou","saint paulin","montcadi","parmesan","mozzarella","emmental","comte","chevre","brique de vache","buchette laitiere","creme dessert","fromage blanc")
    fruits=("pomme","pommes","poire","poires","banane","bananes","raisin","raisins","melon","pasteque","ananas","prune","prunes","orange","oranges","kiwi","kiwis","peche","abricot","abricots","cerise","cerises","fraise","fraises","compote","puree de pommes")
    vegetables=("carotte","carottes","courgette","courgettes","concombre","concombres","haricot vert","haricots verts","tomate","tomates","celeri","chou","brocoli","brocolis","epinard","salade verte","betterave","poireau","poireaux","ratatouille")
    starch=("riz","pates","semoule","couscous","quinoa","lentille","lentilles","pomme de terre","pommes de terre","puree de pomme de terre","puree de pommes de terre","boulgour","ble","mais","polenta","pain")
    plant=("vegetal","vegetarien","falafel","billes vegetales")

    dairy_text=re.sub(r"(?<!\w)lait de coco(?!\w)", " ", n)
    if category == MenuCategory.DAIRY or any(_contains_term(dairy_text,t) for t in dairy): add("dairy")
    if any(_contains_term(n,t) for t in meat): add("meat")
    if any(_contains_term(n,t) for t in fish): add("fish")
    if any(_contains_term(n,t) for t in eggs): add("egg")
    if any(_contains_term(n,t) for t in plant): add("plant_based")
    fruit_text=re.sub(r"(?<!\w)pommes? de terre(?!\w)", " ", n)
    if any(_contains_term(fruit_text,t) for t in fruits): add("fruit")
    if any(_contains_term(n,t) for t in vegetables): add("vegetable")
    if any(_contains_term(n,t) for t in starch): add("starch")
    return labels


def day_to_dict(day: DayMenu) -> dict[str, object]:
    """Return a stable representation; semantic enrichment is presentation-only."""
    by_category = {
        category.value: list(day.items_by_category(category))
        for category in MenuCategory
    }
    details = {
        category.value: [
            {"name": item.name, "labels": _semantic_labels(item.name, category)}
            for item in day.items
            if item.category == category
        ]
        for category in MenuCategory
    }
    return {
        "date": day.menu_date.isoformat(),
        "label": day.label,
        "items": [item.name for item in day.items],
        "details": details,
        **by_category,
    }


def display_week(menu: WeeklyMenu | None, today: date) -> tuple[DayMenu, ...]:
    """Return the most useful week for a dashboard.

    Monday-Friday: prefer the current ISO week when it exists in the document.
    Weekend: prefer the next week containing a future menu. If the current week
    is not present at all, use the first future week. As a final fallback, use
    the latest available week in the document.
    """
    if menu is None or not menu.days:
        return ()

    days = tuple(sorted(menu.days, key=lambda day: day.menu_date))
    monday = today - timedelta(days=today.weekday())
    current_end = monday + timedelta(days=7)
    current = tuple(day for day in days if monday <= day.menu_date < current_end)

    if today.weekday() < 5 and current:
        return current

    future = tuple(day for day in days if day.menu_date > today)
    if future:
        next_monday = future[0].menu_date - timedelta(days=future[0].menu_date.weekday())
        next_end = next_monday + timedelta(days=7)
        return tuple(day for day in days if next_monday <= day.menu_date < next_end)

    if current:
        return current

    last = days[-1].menu_date
    last_monday = last - timedelta(days=last.weekday())
    last_end = last_monday + timedelta(days=7)
    return tuple(day for day in days if last_monday <= day.menu_date < last_end)


def week_start(menu: WeeklyMenu | None, today: date) -> date | None:
    """Return Monday of the display week, or None when no menu is available."""
    days = display_week(menu, today)
    if not days:
        return None
    return days[0].menu_date - timedelta(days=days[0].menu_date.weekday())


def menu_summary(day: DayMenu) -> str:
    """Build a compact calendar summary from the most meaningful meal items."""
    mains = day.items_by_category(MenuCategory.MAIN_COURSE)
    sides = day.items_by_category(MenuCategory.SIDE)
    if mains and sides:
        return f"{mains[0]} · {sides[0]}"
    if mains:
        return mains[0]
    if day.items:
        return day.items[0].name
    return "Menu cantine"


def menu_description(day: DayMenu) -> str:
    """Build a language-light, readable calendar description."""
    lines: list[str] = []
    for category in _CATEGORY_ORDER:
        values = day.items_by_category(category)
        if values:
            icon = _CATEGORY_ICONS[category]
            lines.append(f"{icon} " + " / ".join(values))
    return "\n".join(lines)
