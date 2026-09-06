# v0.4.0-beta.3 — Keyboard editor fix validation

## Bug reproduced

Typing in the optional custom-title field of the Lovelace card editor could bubble keyboard events to Home Assistant global shortcuts. In particular, pressing `A` could open Assist instead of remaining confined to the text input.

## Fix

Keyboard events (`keydown`, `keypress`, `keyup`) originating from editable controls inside `radis-la-toque-card-editor` are stopped at the editor host. `preventDefault()` is deliberately not used, so native text input remains unaffected. The suppression is scoped to editable controls only; keyboard events outside the editor still propagate normally.

## Browser-level test

Executed with Chromium + Playwright against the exact bundled JavaScript:

- typed `Cantine` in the title input: PASS
- input value preserved exactly: PASS
- no keyboard event reached the simulated Home Assistant global shortcut listener: PASS
- blur emitted `config-changed` with title `Cantine`: PASS
- key `A` outside the editor still propagated normally: PASS

## Regression validation

- parser synthetic regression: 10/10 PASS
- first real PDF corpus: 10/10 PASS
- second real PDF corpus: 10/10 PASS
- first corpus presentation: 10/10 PASS
- calendar platform stub: PASS
- config-entry migration v1→v2 stub: PASS
- frontend autoload stub: PASS
- rotating restaurant code: PASS
- presentation suite: 10/10 PASS
- real-world table regression: 10/10 PASS
- JavaScript syntax: PASS
- Python compilation: PASS
- JSON validation: PASS

No parser or menu-data logic was changed.
