from __future__ import annotations
import importlib.util, pathlib, sys, types
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1] / 'custom_components' / 'radis_la_toque'
for name in ['custom_components','custom_components.radis_la_toque','custom_components.radis_la_toque.client']:
    mod=types.ModuleType(name); mod.__path__=[]; sys.modules[name]=mod
const=types.ModuleType('custom_components.radis_la_toque.const')
for k,v in {'BASE_URL':'https://www.radislatoque.fr','CATALOG_CONCURRENCY':4,'LIST_URL':'','MAX_CATALOG_PAGES':200,'PDF_URL':'','REQUEST_TIMEOUT':30,'RESTAURANT_URL':'','USER_AGENT':'test'}.items(): setattr(const,k,v)
sys.modules[const.__name__]=const

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
load('custom_components.radis_la_toque.client.exceptions',ROOT/'client'/'exceptions.py')
models=load('custom_components.radis_la_toque.client.models',ROOT/'client'/'models.py')
parser=load('custom_components.radis_la_toque.client.parser',ROOT/'client'/'parser.py')
MC=models.MenuCategory
TODAY=date(2026,9,5)

def T(headers, rows):
    return ((tuple(['']+headers),)+tuple(tuple(r) for r in rows),)

def bydate(days,d):
    return next(x for x in days if x.menu_date==d)

def vals(day,cat): return day.items_by_category(cat)

def run(code,name,table,checks, expected_days):
    days=parser.parse_menu_tables(table,today=TODAY)
    assert len(days)==expected_days, (code,len(days),[(x.menu_date,x.items) for x in days])
    for d,cat,expected in checks:
        got=vals(bydate(days,d),cat)
        assert got==expected, f'{code} {name} {d} {cat}: {got!r} != {expected!r}'
    assert parser._quality_ok(days), f'{code}: quality failed'
    return parser.menu_quality_score(days)

CASES=[]
# 1 R91012 — Moncé-en-Belin, standard 5x5 table with one blank side.
CASES.append(('R91012','RS primaire Moncé-en-Belin',T(
 ['Lundi\n01/06','Mardi\n02/06','Mercredi\n03/06','Jeudi\n04/06','Vendredi\n05/06'],[
 ['Entrée','Salade de concombre','Radis beurre','Betteraves vinaigrette bio','Salade piémontaise','Salade verte Arlequin'],
 ['Plat principal','Pomme rosties','Pâtes tortis bio façon carbonara','Blanquette de veau','Colin à la crème de poivrons','Colombo de lentilles'],
 ['Garniture','Petits pois Bio','','Riz doré','Poêlée de légumes bio',"Boulette d'agneau à l'ail"],
 ['Produit laitier','Emmental','Tomme grise','Yaourt nature','Cantal AOP','Vache picon'],
 ['Dessert','Fruit de saison','Entremets au chocolat (lait BBC)','Fruit de saison','Ile flottante','Tarte aux pommes'],
]),[(date(2026,6,1),MC.STARTER,('Salade de concombre',)),(date(2026,6,2),MC.SIDE,()),(date(2026,6,5),MC.DESSERT,('Tarte aux pommes',))],5))
# 2 R02797 — Mazières, 4-day week and blank Friday side.
CASES.append(('R02797','RS Mazières de Touraine',T(
 ['Mardi 26/05','Mercredi 27/05','Jeudi 28/05','Vendredi 29/05'],[
 ['Entrée','Tomate,pommes de terre,oeuf,vinaigrette','Radis et beurre','Crêpe au fromage','Pamplemousse rose'],
 ['Plat principal','Pané de poisson blanc','Paupiette de veau','Blanc de dinde braisé','Pâtes sauce au kiri et lentilles bio'],
 ['Garniture','Petits pois nature','Carottes bio','Courgettes bio persillées',''],
 ['Produit laitier','Chanteneige bio','Tomme noire','Petit fromage frais sucré',"Pont l'Evêque AOP"],
 ['Dessert','Crème dessert vanille','Flan nature au lait fermier','Compote de pommes bio','Banane bio'],
]),[(date(2026,5,26),MC.MAIN_COURSE,('Pané de poisson blanc',)),(date(2026,5,29),MC.SIDE,()),(date(2026,5,29),MC.DAIRY,("Pont l'Evêque AOP",))],4))
# 3 R03382 — Les Montils, 4-day standard, blank Tuesday side.
CASES.append(('R03382','ALSH Les Montils',T(
 ['Mardi 26/05','Mercredi 27/05','Jeudi 28/05','Vendredi 29/05'],[
 ['Entrée','Chou fleur vinaigrette','Radis et beurre','Salade verte arlequin','Cake au fromage'],
 ['Plat principal','Pâtes bio à la bolognaise','Paupiette de veau','Sauté de porc sauce diable','Oeufs brouillés aux pommes de terre'],
 ['Garniture','','Carottes bio','Flageolets','Epinards hachés béchamel au lait fermier'],
 ['Produit laitier','Cantal AOP','Tomme noire','Chanteneige bio','Yaourt sucré'],
 ['Dessert','Compote de pommes fraises','Flan nature au lait fermier','Liégeois chocolat','Fraises nature'],
]),[(date(2026,5,26),MC.SIDE,()),(date(2026,5,28),MC.DESSERT,('Liégeois chocolat',))],4))
# 4 R04300 — La Tardière, no dairy row at all.
CASES.append(('R04300','ALSH Laguepie La Tardière',T(
 ['Lundi\n01/06','Mardi\n02/06','Mercredi\n03/06','Jeudi\n04/06','Vendredi\n05/06'],[
 ['Entrée','Salade de pâtes bio en couleur','Tomate nature','Concombres à la crème','Carottes râpées','Taboulé bio à la menthe'],
 ['Plat principal','Tajine de volaille','Billes de blé façon thaï nature','Poulet façon Yassa','Colin Duglére','Emincé de porc'],
 ['Garniture','Haricots verts','Flageolets','Semoule couscous bio nature','Riz bio','Ratatouille bio'],
 ['Dessert','Crème dessert chocolat','Yaourt sucré vanille bio','Fraises nature','Chou à la crème au lait fermier','Abricots frais'],
]),[(date(2026,6,1),MC.DAIRY,()),(date(2026,6,3),MC.SIDE,('Semoule couscous bio nature',)),(date(2026,6,5),MC.DESSERT,('Abricots frais',))],5))
# 5 R04387 — Châteaubriant, standard, internal blank side.
CASES.append(('R04387','Restaurant scolaire Claude Monet',T(
 ['Lundi\n01/06','Mardi\n02/06','Mercredi\n03/06','Jeudi\n04/06','Vendredi\n05/06'],[
 ['Entrée','Salade de riz bio et pois chiches','Betteraves bio vinaigrette','Concombres bio à la crème','Salade verte arlequin','Pommes de terre à la crème'],
 ['Plat principal','Pané de blé, emmental, épinard et graines','Hachis parmentier','Sauté de poulet bio teriyaki','Knack','Blanquette de poisson'],
 ['Garniture','Tajine de légumes','','Semoule couscous bio nature','Flageolets','Haricots verts'],
 ['Produit laitier','Champsecret','Tomme blanche','Camembert bio','Yaourt sucré bio','Bûchette laitière'],
 ['Dessert','Fromage blanc sucré','Cocktail de fruits','Fraises nature','Banane bio','Nuage tutti frutti'],
]),[(date(2026,6,2),MC.SIDE,()),(date(2026,6,4),MC.DAIRY,('Yaourt sucré bio',))],5))
# 6 R00784 — Saint-Yves Nantes, alternative starter/dairy/dessert rows without labels.
CASES.append(('R00784','Ecole Saint Yves Nantes',T(
 ['Mardi 26/05','Mercredi 27/05','Jeudi 28/05','Vendredi 29/05'],[
 ['Entrée','Taboulé bio à la menthe','Radis et beurre','Carottes râpées','Concombres bio au fromage blanc'],
 ['','Salade de riz et maïs vinaigrette',"Tomate à l'huile d'olives",'Crudités arc en ciel','Pamplemousse rose'],
 ['Plat principal','Colin à la crème de moutarde','Paupiette de veau','Pâtes sauce au kiri et lentilles bio','Rôti de porc BBC'],
 ['Garniture','Julienne de légumes','Carottes bio','','Haricots blanc nature'],
 ['Produit laitier','Petit moulé nature','Gouda','Petit fromage frais sucré','Saint Paulin bio'],
 ['','Vache qui rit','Montcadi croûte noire','Fromage blanc sucré','Tomme blanche'],
 ['Dessert','Yaourt fermier arôme citron','Flan nature au lait fermier','Ananas frais','Flan caramel'],
 ['','Crème dessert vanille','Riz au lait fermier','Banane bio','Entremet chocolat au lait fermier'],
]),[(date(2026,5,26),MC.STARTER,('Taboulé bio à la menthe','Salade de riz et maïs vinaigrette')),(date(2026,5,26),MC.DAIRY,('Petit moulé nature','Vache qui rit')),(date(2026,5,29),MC.DESSERT,('Flan caramel','Entremet chocolat au lait fermier'))],4))
# 7 R02929 — Périgourd St-Cyr-sur-Loire, alternatives and multi-line source cells collapsed.
CASES.append(('R02929','Restaurant scolaire Périgourd',T(
 ['Mardi 26/05','Mercredi 27/05','Jeudi 28/05','Vendredi 29/05'],[
 ['Entrée','Taboulé bio à la menthe','Radis et beurre','Carottes râpées','Concombres bio au fromage blanc'],
 ['','Salade de riz et maïs vinaigrette',"Tomate à l'huile d'olives",'Crudités arc en ciel','Pamplemousse rose'],
 ['Plat principal','Colin à la crème de moutarde','Oeufs brouillés aux pommes de terre','Pâtes bio sauce au kiri et lentilles bio','Porc bio au caramel'],
 ['Garniture','Julienne de légumes','Carottes bio','','Haricots blanc nature'],
 ['Produit laitier','Emmental','Gouda','Fromage blanc nature bio sans sucre','Saint Paulin bio'],
 ['','Bûchette laitière','Tomme noire','Petit fromage frais sucré',"Pont l'Evêque AOP"],
 ['Dessert','Yaourt sucré vanille bio','Flan nature au lait fermier','Ananas frais','Flan vanille nappé caramel bio'],
 ['','Yaourt sucré bio','Riz au lait fermier','Banane bio','Entremet chocolat au lait fermier'],
]),[(date(2026,5,27),MC.MAIN_COURSE,('Oeufs brouillés aux pommes de terre',)),(date(2026,5,28),MC.DAIRY,('Fromage blanc nature bio sans sucre','Petit fromage frais sucré'))],4))
# 8 R03188 — Notre-Dame, current same contemporary template as Chinon.
CASES.append(('R03188','RS Notre Dame Saint-Florent-des-Bois',T(
 ['Lundi\n07/09','Mardi\n08/09','Mercredi\n09/09','Jeudi\n10/09','Vendredi\n11/09'],[
 ['Entrée','Taboulé bio à la menthe','Tomate et pommes de terre','Melon','Concombres à la crème','Céleri et carottes rémoulade'],
 ['Plat principal','Palette de porc','Blanc de dinde braisé','Pâtes bio à la carbonara','Billes végétales','Brandade de saumon'],
 ['Garniture','Courgettes béchamel au lait fermier','','Haricots beurre','Haricots blancs à la tomate',''],
 ['Produit laitier','Camembert','Gouda bio','Petit moulé nature','Vache qui rit bio','Tomme noire'],
 ['Dessert','Prunes jaunes','Chou au chocolat au lait fermier','Raisin blanc','Yaourt aromatisé aux fruits','Flan caramel'],
]),[(date(2026,9,7),MC.MAIN_COURSE,('Palette de porc',)),(date(2026,9,7),MC.SIDE,('Courgettes béchamel au lait fermier',)),(date(2026,9,11),MC.DESSERT,('Flan caramel',))],5))
# 9 R00436 — Pont-Saint-Martin, current summer week, multiple dairy/dessert choice rows and empty entries.
CASES.append(('R00436','Restaurant scolaire Pont-Saint-Martin',T(
 ['Lundi\n06/07','Mardi\n07/07','Mercredi\n08/07','Jeudi\n09/07','Vendredi\n10/07'],[
 ['Entrée',"Tomate et huile d'olives bio",'Concombres bio à la crème','','Carottes râpées au citron','Melon'],
 ['Plat principal','Sauté de volaille sauce suprême','Rôti de porc BBC','Pâtes bio et légumes sauce provençale','Blanc de dinde braisé','Paëlla de poisson au riz bio'],
 ['Garniture','Julienne de légumes et semoule','Courgettes bio béchamel au lait fermier','','Purée de pommes de terre',''],
 ['Produit laitier','Edam bio','Montcadi croûte noire','Coulommiers','',''],
 ['','Emmental','Brie','Tomme noire','',''],
 ['Dessert','Abricots frais','Semoule au lait fermier','Yaourt sucré bio','Mousse au chocolat','Banane bio'],
 ['','Nectarine','Flan pâtissier au lait fermier','Entremets praliné au lait fermier','Crème dessert vanille','Pêche'],
]),[(date(2026,7,6),MC.DAIRY,('Edam bio','Emmental')),(date(2026,7,8),MC.STARTER,()),(date(2026,7,10),MC.DESSERT,('Banane bio','Pêche'))],5))
# 10 R00442 — Vallet known two-choice template (week 01/06 from public PDF index).
CASES.append(('R00442','Restaurant scolaire Vallet',T(
 ['Lundi 01/06','Mardi 02/06','Mercredi 03/06','Jeudi 04/06','Vendredi 05/06'],[
 ['Entrée','Salade de pâtes bio en couleur','Tomate nature','Concombres à la crème','Carottes râpées','Taboulé bio à la menthe'],
 ['','Salade de riz et pois chiches','Radis et beurre','Pastèque','Salade verte arlequin','Pommes de terre à la crème'],
 ['Plat principal','Tajine de volaille','Billes de blé façon thaï nature','Poulet façon Yassa','Colin Dugléré','Emincé de porc'],
 ['Garniture','Haricots verts','Flageolets','Semoule couscous bio nature','Riz bio','Ratatouille bio'],
 ['Produit laitier','Brie','Petit moulé nature','Camembert bio','Carré président','Petit fromage frais sucré'],
 ['','Champsecret','Coulommiers','Rondelé','Fromage de chèvre','Yaourt sucré'],
 ['Dessert','Crème dessert chocolat','Yaourt sucré vanille bio','Fraises nature','Chou à la crème au lait fermier','Abricots frais'],
 ['','Fromage blanc sucré','Yaourt aromatisé aux fruits','Ananas frais','Timbale de frambotine','Pêche'],
]),[(date(2026,6,1),MC.STARTER,('Salade de pâtes bio en couleur','Salade de riz et pois chiches')),(date(2026,6,4),MC.DAIRY,('Carré président','Fromage de chèvre')),(date(2026,6,5),MC.DESSERT,('Abricots frais','Pêche'))],5))

if __name__=='__main__':
    print('REAL-WORLD TABLE REGRESSION — 10 distinct establishments')
    passed=0
    for code,name,table,checks,n in CASES:
        score=run(code,name,table,checks,n)
        passed+=1
        print(f'PASS {code:7s} | {name:42s} | {n} days | score={score}')
    print(f'RESULT {passed}/{len(CASES)} PASS')
