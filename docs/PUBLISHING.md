# Publication HACS / GitHub

## Publication d'une version stable

1. Vérifier que la branche de release contient l'ensemble des modifications validées sur Home Assistant.
2. Vérifier que les workflows **HACS**, **hassfest** et **tests** sont verts.
3. Vérifier que la version est cohérente dans :
   - `custom_components/radis_la_toque/manifest.json` ;
   - `custom_components/radis_la_toque/const.py` ;
   - la carte Lovelace embarquée.
4. Créer une GitHub Release correspondant au tag de version, par exemple `v1.0.0`.
5. Tester l'installation ou la mise à jour depuis HACS en utilisant le dépôt comme dépôt personnalisé de catégorie `Integration`.
6. Après validation de la release stable, demander l'inclusion du dépôt dans les dépôts HACS par défaut.

## Première publication stable

La première version stable du projet est `v1.0.0`.

Avant sa publication :

- exécuter les tests de régression ;
- exécuter les tests des plateformes et du chargement frontend ;
- vérifier la compilation Python ;
- vérifier les diagnostics Home Assistant ;
- tester le fonctionnement réel sur Home Assistant ;
- vérifier la documentation et les captures d'écran.

## Branding

Depuis Home Assistant 2026.3, les custom integrations peuvent livrer leurs images dans `custom_components/radis_la_toque/brand/`.

Le projet fournit :

- `icon.png` en 256×256 ;
- `icon@2x.png` en 512×512.

Ces images sont des créations originales et ne réutilisent pas d'asset RESTORIA.

## Carte Lovelace

La carte est embarquée dans :

`custom_components/radis_la_toque/www/`

L'intégration la sert via :

`/radis_la_toque/radis-la-toque-card.js`

Le module frontend est chargé automatiquement avec une URL versionnée afin d'éviter les problèmes de cache lors des mises à jour.

Aucun ajout manuel dans **Tableaux de bord → Ressources** n'est nécessaire.

## Publication HACS

Une fois la version stable validée :

1. pousser la branche de release sur GitHub ;
2. fusionner dans `main` ;
3. créer le tag et la GitHub Release correspondante ;
4. vérifier l'installation depuis HACS ;
5. soumettre ensuite le dépôt au catalogue HACS par défaut.