# Second independent real-PDF validation

Date: 2026-09-05

A second corpus of ten different public Radis la Toque PDF responses was collected independently from Home Assistant and tested using the production PDF extraction/parsing code.

## Results

| Code | Result | Parsed days | Notes |
|---|---|---:|---|
| R00310 | PASS / no menu | 0 | Valid PDF shell, no menu content published |
| R00316 | PASS | 10 | Table parser, score 940 |
| R00341 | PASS | 10 | Table parser, score 940 |
| R02445 | PASS | 10 | Table parser, score 940 |
| R02917 | PASS / no menu | 0 | Valid PDF shell, no menu content published |
| R02936 | PASS | 10 | Table parser, score 940 |
| R03738 | PASS | 5 | Only future week published, score 440 |
| R90042 | PASS | 9 | One day absent/empty, score 900 |
| R90259 | PASS / no menu | 0 | Valid PDF shell, no menu content published |
| R90911 | PASS | 5 | One week published, score 350 |

Summary: **10/10 responses handled correctly** after the blank-menu fix: 7 menu PDFs parsed, 3 empty publication shells classified as `MenuNotAvailable`, 0 unsupported-structure failures.

The original ten-real-PDF corpus was rerun after the fix: **10/10 parsed, zero regressions**.

Presentation/week/calendar payload helpers were also exercised on every parsed menu from both corpora: **17/17 PASS**.

## Robustness issue found and fixed

The provider can return HTTP 200 + a syntactically valid PDF that contains only branding/legal boilerplate and no menu grid. Previously this reached the parser and raised `menu_structure_not_recognized`, incorrectly treating absence of a published menu as a parser failure.

The fix adds a conservative pre-parse detector. A PDF is considered a blank menu shell only when it contains no weekday, no menu date, and no recognized meal-category marker. Any plausible new menu format still goes through the parser and will fail loudly if unsupported.
