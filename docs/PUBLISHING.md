# Publication HACS / GitHub

## Avant la première publication

1. Remplacer `guat37` avec :

```bash
python scripts/set_github_owner.py <github_username>
```

2. Créer le dépôt GitHub `ha-radis-la-toque` et pousser cette arborescence.
3. Vérifier que les workflows **HACS**, **hassfest** et **tests** sont verts.
4. Créer une GitHub Release `v0.4.0-beta.2`.
5. Tester l'installation en ajoutant le dépôt comme dépôt personnalisé HACS de catégorie `Integration`.
6. Après une période de bêta et des retours utilisateurs, préparer une version stable avant de demander l'inclusion dans les dépôts HACS par défaut.

## Branding

Depuis Home Assistant 2026.3, les custom integrations peuvent livrer leurs images dans `custom_components/radis_la_toque/brand/`. Le projet fournit donc `icon.png` (256×256) et `icon@2x.png` (512×512), créations originales sans asset RESTORIA.

## Carte Lovelace

La carte est embarquée dans `custom_components/radis_la_toque/www/`. L'intégration la sert via `/radis_la_toque/radis-la-toque-card.js` et charge automatiquement le module frontend avec une URL versionnée. Aucun ajout manuel dans **Tableaux de bord → Ressources** n'est nécessaire.
