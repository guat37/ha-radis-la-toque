"""Regression for valid-but-empty RESTORIA PDF shells."""
from __future__ import annotations
from pathlib import Path
import os, sys, shutil

# This test is intended for the project test harness; corpus is external.
# The helper is tested through the production client in CI/local validation.

CODES = ("R00310", "R02917", "R90259")


def run(corpus_dir: Path, Client) -> None:
    for code in CODES:
        payload = (corpus_dir / f"{code}.pdf").read_bytes()
        tables, words, layout, text = Client._extract_pdf_content(payload)
        assert Client._document_has_no_menu_content(text), code
        print(f"PASS {code}: blank menu PDF correctly classified as no menu")
