# Radis la Toque — v0.4.0-beta.2 candidate

## Root causes fixed

1. **Volatile `Rxxxxx` menu code used as permanent identity**
   - Restaurant fiche `entry-xxxx` is the stable CMS identity.
   - The `Rxxxxx` menu endpoint can rotate over time.
   - Existing config entries therefore became stale and only recovered after delete/recreate.

2. **Bundled Lovelace card served but not loaded automatically**
   - beta.1 exposed the JS static path but still required a manual Lovelace Resource.
   - beta.2 loads the versioned JS module through Home Assistant frontend registration.

## Migration strategy

- Config entry schema: v1 -> v2.
- Stable config-entry unique id: `entry-xxxx`.
- Existing entity/device unique IDs are preserved via `entity_prefix=<old Rxxxxx>`.
- New entries use `entity_prefix=entry-xxxx`.
- `restaurant_code` remains stored only as the last-known volatile endpoint.
- Every coordinator refresh re-resolves the current `Rxxxxx` from the stable restaurant fiche and persists a changed code.

## Tests run on the exact candidate code

- parser regression suite: PASS (10 scenarios)
- first real PDF corpus: PASS (10/10)
- second real PDF corpus: PASS (10/10, including 3 valid blank-menu PDFs)
- stable fiche ID extraction: PASS
- rotating code resolution (`entry-1247` -> `R03803` fixture): PASS
- config entry v1 -> v2 migration, preserving entity prefix: PASS
- bundled card frontend auto-load + idempotence: PASS
- Python compileall: PASS
- JavaScript `node --check`: PASS

## Expected user-visible behavior

- Existing Saint-Étienne-de-Chigny entry migrates without deletion/recreation.
- At refresh/startup the current menu code is resolved from its fiche.
- Existing entity IDs remain unchanged.
- Manual Lovelace resource can be removed after beta.2 is installed and HA restarted.
