"""Regression tests for rotating Rxxxxx codes and stable restaurant identity."""
from __future__ import annotations

import asyncio
import pathlib
import runpy

ns = runpy.run_path(str(pathlib.Path(__file__).with_name("run_regression.py")), run_name="fixture_loader")
parser = ns["parser"]
client_mod = ns["client"]


def run() -> None:
    # Stable identity comes from the restaurant fiche, not the volatile menu code.
    assert parser.restaurant_id_from_url(
        "https://www.radislatoque.fr/les-menus-de-la-cantine/liste-des-restaurants/entry-1247-rs-st-etienne-de-chigny.html"
    ) == "entry-1247"
    assert parser.restaurant_id_from_url(
        "https://www.radislatoque.fr/les-menus-de-la-cantine/liste-des-restaurants/entry-1239-restaurant-scolaire-ecole-perrault-engerand.html"
    ) == "entry-1239"

    async def resolve() -> None:
        api = object.__new__(client_mod.RadisLaToqueClient)

        async def fake_get_text(url: str) -> str:
            assert "entry-1247" in url
            # Reproduces the current fiche after the site's code rotation.
            return '<a href="/restaurants/R03803">Consulter le menu</a>'

        api._get_text = fake_get_text
        code = await api.async_resolve_code(
            "https://www.radislatoque.fr/les-menus-de-la-cantine/liste-des-restaurants/entry-1247-rs-st-etienne-de-chigny.html"
        )
        assert code == "R03803"

    asyncio.run(resolve())
    print("ROTATING RESTAURANT CODE: PASS")


if __name__ == "__main__":
    run()
