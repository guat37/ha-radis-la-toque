"""Load the exact shipped parser/client modules without importing Home Assistant."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "radis_la_toque"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_runtime():
    for name in (
        "custom_components",
        "custom_components.radis_la_toque",
        "custom_components.radis_la_toque.client",
    ):
        if name not in sys.modules:
            mod = types.ModuleType(name)
            mod.__path__ = []
            sys.modules[name] = mod

    const = types.ModuleType("custom_components.radis_la_toque.const")
    for key, value in {
        "BASE_URL": "https://www.radislatoque.fr",
        "CATALOG_CONCURRENCY": 4,
        "LIST_URL": "https://www.radislatoque.fr/les-menus-de-la-cantine/liste-des-restaurants",
        "MAX_CATALOG_PAGES": 200,
        "PDF_URL": "https://www.radislatoque.fr/action-DownloadPDF-{code}",
        "REQUEST_TIMEOUT": 30,
        "RESTAURANT_URL": "https://www.radislatoque.fr/restaurants/{code}",
        "USER_AGENT": "standalone-regression-test",
    }.items():
        setattr(const, key, value)
    sys.modules[const.__name__] = const

    _load("custom_components.radis_la_toque.client.exceptions", ROOT / "client" / "exceptions.py")
    models = _load("custom_components.radis_la_toque.client.models", ROOT / "client" / "models.py")
    parser = _load("custom_components.radis_la_toque.client.parser", ROOT / "client" / "parser.py")
    presentation = _load(
        "custom_components.radis_la_toque.client.presentation",
        ROOT / "client" / "presentation.py",
    )
    client = _load("custom_components.radis_la_toque.client.client", ROOT / "client" / "client.py")
    return client, parser, models, presentation
