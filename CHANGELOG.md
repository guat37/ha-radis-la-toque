# Changelog

## 0.4.0-beta.3

- Corrige les raccourcis clavier Home Assistant déclenchés pendant la saisie dans l’éditeur de la carte Lovelace.
- Les événements clavier des champs éditables de la carte restent confinés à l’éditeur sans bloquer la saisie native.


## 0.4.0-beta.2

### Fixed
- identité des établissements basée sur l'identifiant stable de la fiche `entry-xxxx` au lieu du code de menu `Rxxxxx` ;
- résolution automatique du code `Rxxxxx` courant à chaque cycle de mise à jour ;
- migration transparente des entrées existantes sans renommer les entités ni recréer les appareils ;
- carte Lovelace chargée automatiquement par l'intégration, sans ressource manuelle.

### Regression coverage
- test dédié à la rotation de code observée sur Saint-Étienne-de-Chigny (`R03436` historique → `R03803` courant) ;
- validation des deux corpus réels de 10 établissements : 20/20 réponses gérées ;
- test de migration v1 → v2 et test d'auto-chargement frontend.

## 0.4.0-beta.1

### Added
- packaging HACS communautaire unifié ;
- carte Lovelace embarquée dans l'intégration ;
- icône locale originale compatible Home Assistant 2026.3+ ;
- workflows HACS, hassfest et tests de régression ;
- documentation de publication et de contribution.

### Baseline fonctionnelle
- parser issu de 0.3.0-dev.4 ;
- carte issue de 0.1.0-dev.6 ;
- 20 établissements réels validés sur deux corpus indépendants ;
- gestion des PDF valides sans menu publié.
