"""End-to-end regression against the second independent real-PDF corpus."""
from __future__ import annotations

from datetime import date
import os
from pathlib import Path

from _standalone import load_runtime

client, parser, _models, _presentation = load_runtime()

EXPECTED_DAYS = {
    "R00310": 0,
    "R00316": 10,
    "R00341": 10,
    "R02445": 10,
    "R02917": 0,
    "R02936": 10,
    "R03738": 5,
    "R90042": 9,
    "R90259": 0,
    "R90911": 5,
}


def run(corpus_dir: Path) -> None:
    passed = 0
    for code, expected_days in EXPECTED_DAYS.items():
        payload = (corpus_dir / f"{code}.pdf").read_bytes()
        tables, words, layout, text = client.RadisLaToqueClient._extract_pdf_content(payload)
        if expected_days == 0:
            assert client.RadisLaToqueClient._document_has_no_menu_content(text), code
            print(f"PASS {code}: no menu published")
        else:
            days, parser_kind, score = parser.select_menu_parse(
                tables, words, layout, text, today=date(2026, 9, 5)
            )
            assert parser_kind == "table", (code, parser_kind)
            assert len(days) == expected_days, (code, len(days), expected_days)
            assert score > 0, (code, score)
            print(f"PASS {code}: {len(days)} days, parser={parser_kind}, score={score}")
        passed += 1
    print(f"SECOND REAL PDF CORPUS: {passed}/{len(EXPECTED_DAYS)} PASS")


if __name__ == "__main__":
    raw = os.environ.get("RLT_REAL_PDF_DIR")
    if not raw:
        raise SystemExit("Set RLT_REAL_PDF_DIR to the second real PDF corpus directory")
    run(Path(raw))
