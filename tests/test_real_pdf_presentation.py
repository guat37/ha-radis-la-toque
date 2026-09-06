"""Validate new week/calendar presentation helpers against ten raw real PDFs."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import os
import pathlib
import runpy

ns = runpy.run_path(str(pathlib.Path(__file__).with_name("run_regression.py")), run_name="fixture_loader")
load = ns["load"]
ROOT = ns["ROOT"]
client = ns["client"]
parser = ns["parser"]
presentation = load(
    "custom_components.radis_la_toque.client.presentation",
    ROOT / "client" / "presentation.py",
)

CORPUS = (
    "R00436", "R00442", "R00447", "R00784", "R02797",
    "R02929", "R03382", "R04300", "R04387", "R91012",
)


def run(corpus_dir: Path) -> None:
    passed = 0
    for code in CORPUS:
        payload = (corpus_dir / f"{code}.pdf").read_bytes()
        tables, words, fragments, text = client.RadisLaToqueClient._extract_pdf_content(payload)
        days, kind, score = parser.select_menu_parse(
            tables, words, fragments, text, today=date(2026, 9, 5)
        )
        assert kind == "table", f"{code}: unexpected parser {kind}"
        assert len(days) == 10, f"{code}: expected 10 parsed days, got {len(days)}"

        menu = ns["models"].WeeklyMenu(code, code, "https://example.invalid", days)
        week = presentation.display_week(menu, date(2026, 9, 5))
        assert week, f"{code}: no dashboard week selected"
        assert week[0].menu_date.isoformat() == "2026-09-07", f"{code}: wrong week start"
        assert presentation.week_start(menu, date(2026, 9, 5)).isoformat() == "2026-09-07"

        for day in week:
            payload_dict = presentation.day_to_dict(day)
            assert payload_dict["items"], f"{code} {day.menu_date}: empty item payload"
            assert presentation.menu_summary(day), f"{code} {day.menu_date}: empty calendar summary"
            assert presentation.menu_description(day), f"{code} {day.menu_date}: empty calendar description"

        print(f"PASS {code}: {len(days)} days, week={len(week)}, score={score}")
        passed += 1

    print(f"REAL PDF PRESENTATION: {passed}/10 PASS")


if __name__ == "__main__":
    directory = os.environ.get("RLT_REAL_PDF_DIR")
    if not directory:
        raise SystemExit("Set RLT_REAL_PDF_DIR")
    run(Path(directory))
