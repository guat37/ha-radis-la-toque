# Test report — 0.3.0-dev.3

This build fixes the semantic-enrichment regression by restoring the exact parser path from 0.3.0-dev.1 and moving semantic labels to the presentation layer only.

Validation performed before packaging:

- Parser output comparison versus 0.3.0-dev.1 on the 10 real raw PDFs: **IDENTICAL PASS**.
  - Same menu dates.
  - Same labels.
  - Same item names.
  - Same meal categories.
  - Same parser-produced item labels.
- Real corpus used: R00436, R00442, R00447, R00784, R02797, R02929, R03382, R04300, R04387, R91012.
- Semantic presentation tests: **PASS**.
- False-positive guards: potato is not fruit; coconut milk does not imply dairy; whole-word matching retained.
- Python compileall: **PASS**.

Architectural rule: semantic enrichment must never influence whether a PDF parses successfully.
