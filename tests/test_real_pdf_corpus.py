"""End-to-end regression against the first local corpus of real public PDFs.

The PDF files are intentionally not committed/distributed. Set RLT_REAL_PDF_DIR
when running this test manually.
"""
from __future__ import annotations

from datetime import date
import os
from pathlib import Path

from _standalone import load_runtime

client, parser, models, _presentation = load_runtime()

CORPUS = {
    "R00436": ("Salade piémontaise", "Colin Dugléré"),
    "R00442": ("Taboulé bio à la menthe", "Palette de porc"),
    "R00447": ("Taboulé bio à la menthe", "Palette de porc"),
    "R00784": ("Salade piémontaise", "Colin Dugléré"),
    "R02797": ("Taboulé bio à la menthe", "Palette de porc"),
    "R02929": ("Salade piémontaise aux pommes de terre bio", "Colin Dugléré"),
    "R03382": ("Gougère au cantadou au lait fermier", "Aiguillettes panées de blé"),
    "R04300": ("Taboulé bio à la menthe", "Palette de porc"),
    "R04387": ("Salade piémontaise aux pommes de terre bio", "Colin Dugléré"),
    "R91012": ("Saucisson à l'ail", "Curry de volaille"),
}


def run(corpus_dir: Path) -> None:
    passed = 0
    for code, (starter, main_course) in CORPUS.items():
        payload = (corpus_dir / f"{code}.pdf").read_bytes()
        tables, words, layout, text = client.RadisLaToqueClient._extract_pdf_content(payload)
        days, parser_kind, score = parser.select_menu_parse(
            tables, words, layout, text, today=date(2026, 9, 5)
        )
        assert parser_kind == "table", (code, parser_kind)
        assert len(days) == 10, (code, len(days))
        assert days[0].menu_date == date(2026, 9, 7), (code, days[0].menu_date)
        starters = days[0].items_by_category(models.MenuCategory.STARTER)
        mains = days[0].items_by_category(models.MenuCategory.MAIN_COURSE)
        assert starter in starters, (code, starter, starters)
        assert main_course in mains, (code, main_course, mains)
        assert score >= 650, (code, score)
        print(f"PASS {code}: {len(days)} days, parser={parser_kind}, score={score}")
        passed += 1
    print(f"FIRST REAL PDF CORPUS: {passed}/{len(CORPUS)} PASS")


if __name__ == "__main__":
    raw = os.environ.get("RLT_REAL_PDF_DIR")
    if not raw:
        raise SystemExit("Set RLT_REAL_PDF_DIR to the first real PDF corpus directory")
    run(Path(raw))
