from __future__ import annotations
import importlib.util
import pathlib
import sys
import types
from datetime import date
from io import BytesIO

ROOT = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "radis_la_toque"

# Load the exact shipped client modules without importing Home Assistant.
for name in ["custom_components", "custom_components.radis_la_toque", "custom_components.radis_la_toque.client"]:
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
    "USER_AGENT": "regression-test",
}.items():
    setattr(const, key, value)
sys.modules[const.__name__] = const

def load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module

load("custom_components.radis_la_toque.client.exceptions", ROOT / "client" / "exceptions.py")
models = load("custom_components.radis_la_toque.client.models", ROOT / "client" / "models.py")
parser = load("custom_components.radis_la_toque.client.parser", ROOT / "client" / "parser.py")
client = load("custom_components.radis_la_toque.client.client", ROOT / "client" / "client.py")

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

STYLE = getSampleStyleSheet()["BodyText"]
STYLE.fontSize = 9
STYLE.leading = 11
P = lambda value: Paragraph(value, STYLE) if value else ""


def make_pdf(weeks: list[dict]) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10, rightMargin=10, topMargin=30, bottomMargin=20)
    story = []
    for wi, week in enumerate(weeks):
        headers = [""] + [P(f"{d['weekday']}<br/>{d['date']}") for d in week["days"]]
        rows = [headers]
        for category, label in week["rows"]:
            cells = [P(label)]
            for d in week["days"]:
                cells.append(P(d.get(category, "")))
            rows.append(cells)
        col_width = 80
        day_width = (landscape(A4)[0] - 20 - col_width) / len(week["days"])
        table = Table(rows, colWidths=[col_width] + [day_width] * len(week["days"]), rowHeights=[38] + [58] * (len(rows)-1))
        table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.6, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (1,0), (-1,-1), "CENTER"),
        ]))
        story.append(table)
        if wi + 1 < len(weeks):
            story.append(PageBreak())
    doc.build(story)
    return buf.getvalue()


def parse_pdf(payload: bytes):
    tables, words, frags, text = client.RadisLaToqueClient._extract_pdf_content(payload)
    return parser.select_menu_parse(tables, words, frags, text, today=date(2026, 9, 5))

ROWS5 = [
    ("starter", "Entrée"),
    ("main_course", "Plat<br/>principal"),
    ("side", "Garniture"),
    ("dairy", "Produit<br/>laitier"),
    ("dessert", "Dessert"),
]

R00447_WEEK1 = {
    "days": [
        {"weekday":"Lundi","date":"07/09","starter":"Taboulé bio à la menthe","main_course":"Palette de porc","side":"Courgettes béchamel au lait fermier","dairy":"Camembert","dessert":"Prunes jaunes"},
        {"weekday":"Mardi","date":"08/09","starter":"Tomate et pommes de terre","main_course":"Blanc de dinde braisé","side":"Haricots beurre","dairy":"Gouda bio","dessert":"Chou au chocolat au lait fermier"},
        {"weekday":"Mercredi","date":"09/09","starter":"Melon","main_course":"Pâtes bio à la carbonara","side":"","dairy":"Petit moulé nature","dessert":"Raisin blanc"},
        {"weekday":"Jeudi","date":"10/09","starter":"Concombres à la crème","main_course":"Billes végétales","side":"Haricots blancs à la tomate","dairy":"Vache qui rit bio","dessert":"Yaourt aromatisé aux fruits"},
        {"weekday":"Vendredi","date":"11/09","starter":"Céleri et carottes rémoulade","main_course":"Brandade de saumon","side":"","dairy":"Tomme noire","dessert":"Flan caramel"},
    ],
    "rows": ROWS5,
}

R00447_WEEK2 = {
    "days": [
        {"weekday":"Lundi","date":"14/09","starter":"Salade de riz bio à la provençale et anchois","main_course":"Paupiette de veau","side":"Petits pois carottes","dairy":"Mini Cabrette","dessert":"Liégeois chocolat"},
        {"weekday":"Mardi","date":"15/09","starter":"Melon","main_course":"Chili sin carne","side":"Semoule couscous bio nature","dairy":"Champsecret","dessert":"Poire"},
        {"weekday":"Mercredi","date":"16/09","starter":"Pizza","main_course":"Colin à la crème de poivrons","side":"Ratatouille","dairy":"Emmental bio","dessert":"Prunes jaunes"},
        {"weekday":"Jeudi","date":"17/09","starter":"Accras à la morue","main_course":"Jambon braisé","side":"Haricots verts à l'ail","dairy":"Edam bio","dessert":"Compote de pommes fraises"},
        {"weekday":"Vendredi","date":"18/09","starter":"Rillettes de thon à la vanille","main_course":"Sauté de volaille au curry et lait de coco","side":"Riz bio","dairy":"Tartare","dessert":"Po'é banane"},
    ],
    "rows": ROWS5,
}


def names(day):
    return {item.category.value: item.name for item in day.items}


def run():
    checks = 0
    # 1. Exact public R00447 structure, two pages / two weeks.
    days, kind, score = parse_pdf(make_pdf([R00447_WEEK1, R00447_WEEK2]))
    assert kind == "table" and len(days) == 10 and score > 700
    monday = names(days[0])
    assert monday == {
        "starter":"Taboulé bio à la menthe",
        "main_course":"Palette de porc",
        "side":"Courgettes béchamel au lait fermier",
        "dairy":"Camembert",
        "dessert":"Prunes jaunes",
    }
    assert names(days[5])["starter"] == "Salade de riz bio à la provençale et anchois"
    checks += 1

    # 2. Four-day week (holiday/missing weekday) remains valid.
    four = {"days": R00447_WEEK1["days"][1:], "rows": ROWS5}
    days, kind, _ = parse_pdf(make_pdf([four]))
    assert kind == "table" and len(days) == 4 and days[0].menu_date.isoformat() == "2026-09-08"
    checks += 1

    # 3. Missing category (no dairy) is accepted when the rest is coherent.
    no_dairy = {"days": [dict(d) for d in R00447_WEEK1["days"]], "rows": [r for r in ROWS5 if r[0] != "dairy"]}
    days, kind, _ = parse_pdf(make_pdf([no_dairy]))
    assert kind == "table" and len(days) == 5
    assert all("dairy" not in names(day) for day in days)
    checks += 1

    # 4. Empty cells do not shift following days/categories.
    empties = {"days": [dict(d) for d in R00447_WEEK1["days"]], "rows": ROWS5}
    empties["days"][0]["starter"] = ""
    empties["days"][2]["main_course"] = ""
    days, kind, _ = parse_pdf(make_pdf([empties]))
    assert kind == "table"
    assert "starter" not in names(days[0])
    assert names(days[0])["main_course"] == "Palette de porc"
    assert "main_course" not in names(days[2])
    assert names(days[2])["dairy"] == "Petit moulé nature"
    checks += 1

    # 5. Repeated category rows (choice menus) remain multiple items, not overwritten.
    choices_rows = [
        ("starter", "Entrée"), ("starter2", "Entrée"),
        ("main_course", "Plat<br/>principal"),
        ("dairy", "Produit<br/>laitier"), ("dairy2", "Produit<br/>laitier"),
        ("dessert", "Dessert"), ("dessert2", "Dessert"),
    ]
    choice_days=[]
    for d in R00447_WEEK1["days"][:4]:
        x=dict(d); x["starter2"]="Deuxième entrée"; x["dairy2"]="Deuxième laitage"; x["dessert2"]="Deuxième dessert"; choice_days.append(x)
    choice = {"days": choice_days, "rows": choices_rows}
    days, kind, _ = parse_pdf(make_pdf([choice]))
    assert kind == "table" and len(days) == 4
    assert len(days[0].items_by_category(models.MenuCategory.STARTER)) == 2
    assert "Deuxième entrée" in days[0].items_by_category(models.MenuCategory.STARTER)
    checks += 1

    # 6. Malformed PDF with no menu table must fail rather than publish junk.
    buf=BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4); doc.build([Paragraph("Document sans tableau de menu", STYLE)])
    tables, words, frags, text = client.RadisLaToqueClient._extract_pdf_content(buf.getvalue())
    try:
        parser.select_menu_parse(tables, words, frags, text, today=date(2026,9,5))
    except Exception as err:
        assert str(err) == "menu_structure_not_recognized"
    else:
        raise AssertionError("Malformed menu was incorrectly accepted")
    checks += 1

    # 7. Catalog pagination accepts relative and absolute links.
    html='''<a href="page-3.html">3</a><a href="/les-menus-de-la-cantine/liste-des-restaurants/page-113.html">&gt;&gt;</a>'''
    assert parser.infer_last_catalog_page(html) == 113
    checks += 1


    # 8. A header may contain a day with no meal at all; later columns must not shift.
    closed = {"days": [dict(d) for d in R00447_WEEK1["days"]], "rows": ROWS5}
    for key in ("starter", "main_course", "side", "dairy", "dessert"):
        closed["days"][0][key] = ""
    days, kind, _ = parse_pdf(make_pdf([closed]))
    assert kind == "table"
    assert days[0].menu_date.isoformat() == "2026-09-08"
    assert names(days[0])["starter"] == "Tomate et pommes de terre"
    checks += 1

    # 9. Long wrapped values and accents/apostrophes must survive intact.
    wrapped = {"days": [dict(d) for d in R00447_WEEK1["days"][:4]], "rows": ROWS5}
    wrapped["days"][0]["main_course"] = "Émincé de volaille bio au Xérès et crème légère"
    wrapped["days"][1]["dessert"] = "Compote de pommes-fraises sans sucres ajoutés"
    days, kind, _ = parse_pdf(make_pdf([wrapped]))
    assert kind == "table"
    assert names(days[0])["main_course"] == "Émincé de volaille bio au Xérès et crème légère"
    assert names(days[1])["dessert"] == "Compote de pommes-fraises sans sucres ajoutés"
    checks += 1

    # 10. Legacy long-date text remains a safe, structurally distinct fallback.
    legacy = """
Lundi 7 septembre 2026
Entrée
Carottes râpées
Plat principal
Poulet rôti
Garniture
Semoule
Produit laitier
Camembert
Dessert
Compote
Mardi 8 septembre 2026
Entrée
Melon
Plat principal
Poisson
Garniture
Riz
Produit laitier
Yaourt
Dessert
Poire
"""
    legacy_days, kind, _ = parser.select_menu_parse((), (), (), legacy, today=date(2026,9,5))
    assert kind == "legacy_text" and len(legacy_days) == 2
    assert names(legacy_days[0])["main_course"] == "Poulet rôti"
    checks += 1

    print(f"OK - {checks} regression scenarios passed")
    print(f"R00447 parsed days: {len(parse_pdf(make_pdf([R00447_WEEK1,R00447_WEEK2]))[0])}")

if __name__ == "__main__":
    run()
