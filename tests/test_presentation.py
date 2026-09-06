"""Pure presentation regression tests (no Home Assistant dependency)."""
from __future__ import annotations

from datetime import date
import pathlib
import runpy

# Load shipped client modules without importing Home Assistant.
ns = runpy.run_path(str(pathlib.Path(__file__).with_name("run_regression.py")), run_name="fixture_loader")
load = ns["load"]
ROOT = ns["ROOT"]
models = ns["models"]
presentation = load(
    "custom_components.radis_la_toque.client.presentation",
    ROOT / "client" / "presentation.py",
)

MenuCategory = models.MenuCategory
MenuItem = models.MenuItem
DayMenu = models.DayMenu
WeeklyMenu = models.WeeklyMenu


def make_day(iso: str, main: str, side: str = "", starter: tuple[str, ...] = ()):
    d = date.fromisoformat(iso)
    items = [MenuItem(v, MenuCategory.STARTER) for v in starter]
    items.append(MenuItem(main, MenuCategory.MAIN_COURSE))
    if side:
        items.append(MenuItem(side, MenuCategory.SIDE))
    return DayMenu(d, d.strftime("%A %d/%m"), tuple(items))


def make_menu(days):
    return WeeklyMenu("RTEST", "Test", "https://example.invalid/menu.pdf", tuple(days))


def run() -> None:
    checks = 0
    menu = make_menu([
        make_day("2026-09-07", "Plat lundi", "Garniture lundi", ("Entrée A", "Entrée B")),
        make_day("2026-09-08", "Plat mardi"),
        make_day("2026-09-10", "Plat jeudi"),
        make_day("2026-09-14", "Plat lundi suivant"),
        make_day("2026-09-15", "Plat mardi suivant"),
    ])

    # 1. Weekday -> current week.
    week = presentation.display_week(menu, date(2026, 9, 8))
    assert [d.menu_date.isoformat() for d in week] == ["2026-09-07", "2026-09-08", "2026-09-10"]
    checks += 1

    # 2. Weekend -> next available week.
    week = presentation.display_week(menu, date(2026, 9, 12))
    assert [d.menu_date.isoformat() for d in week] == ["2026-09-14", "2026-09-15"]
    checks += 1

    # 3. Before first published menu -> first future week.
    week = presentation.display_week(menu, date(2026, 9, 5))
    assert week[0].menu_date.isoformat() == "2026-09-07"
    checks += 1

    # 4. After the corpus -> latest published week fallback.
    week = presentation.display_week(menu, date(2026, 10, 1))
    assert [d.menu_date.isoformat() for d in week] == ["2026-09-14", "2026-09-15"]
    checks += 1

    # 5. Week sensor state is always the Monday of the displayed week.
    assert presentation.week_start(menu, date(2026, 9, 12)).isoformat() == "2026-09-14"
    checks += 1

    # 6. Stable nested attributes preserve multi-choice categories.
    payload = presentation.day_to_dict(menu.days[0])
    assert payload["starter"] == ["Entrée A", "Entrée B"]
    assert payload["main_course"] == ["Plat lundi"]
    assert payload["side"] == ["Garniture lundi"]
    checks += 1

    # 7. Calendar summary prioritizes main course and side.
    assert presentation.menu_summary(menu.days[0]) == "Plat lundi · Garniture lundi"
    checks += 1

    # 8. Calendar description keeps all choices.
    desc = presentation.menu_description(menu.days[0])
    assert "Entrée A / Entrée B" in desc and "Plat lundi" in desc and "Garniture lundi" in desc
    checks += 1

    # 9. Empty data is handled safely.
    assert presentation.display_week(None, date(2026, 9, 5)) == ()
    assert presentation.week_start(None, date(2026, 9, 5)) is None
    checks += 1

    # 10. Single sparse day remains representable.
    sparse = make_day("2026-09-09", "Plat unique")
    assert presentation.menu_summary(sparse) == "Plat unique"
    assert presentation.day_to_dict(sparse)["dairy"] == []
    checks += 1

    print(f"PRESENTATION: {checks}/10 PASS")


if __name__ == "__main__":
    run()
