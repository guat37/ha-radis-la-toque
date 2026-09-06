# Tests

## Suite locale sans Home Assistant

```bash
python -m pip install -r requirements-dev.txt
python tests/run_regression.py
node --check custom_components/radis_la_toque/www/radis-la-toque-card.js
```

Cette suite couvre notamment : semaine 4/5 jours, catégorie absente, cellule vide, journée vide, choix multiples, textes multilignes et fallback ancien format.

## Corpus PDF réels

Les PDF publics utilisés pour les campagnes de validation ne sont pas inclus dans le dépôt. Deux corpus indépendants de dix établissements ont été testés pendant le développement.

Pour rejouer le premier corpus :

```bash
RLT_REAL_PDF_DIR=/path/to/pdfs python tests/test_real_pdf_corpus.py
```

Trois réponses du second corpus étaient des PDF valides sans tableau de menu ; elles sont désormais classées comme `MenuNotAvailable` plutôt que comme erreur de parser.

Consulter les rapports historiques :

- `docs/TEST_REPORT_FIRST_CORPUS.md`
- `docs/TEST_REPORT_SECOND_CORPUS.md`
