# Contribuer

Merci de contribuer à Radis la Toque pour Home Assistant.

## Principes du projet

1. **Le parser est le chemin critique.** Aucun enrichissement visuel ou sémantique ne doit modifier son résultat ni sa disponibilité.
2. Une nouvelle heuristique de parsing doit être accompagnée d'un test de non-régression.
3. Un résultat partiel ne doit jamais être publié comme un menu valide si sa structure est incohérente.
4. Les PDF réels de test ne sont pas commités ni redistribués.
5. Aucun asset graphique RESTORIA/Radis la Toque n'est repris dans le dépôt.

## Validation locale

```bash
python -m pip install -r requirements-dev.txt
python tests/run_regression.py
node --check custom_components/radis_la_toque/www/radis-la-toque-card.js
```

Pour le corpus réel :

```bash
RLT_REAL_PDF_DIR=/chemin/vers/corpus python tests/test_real_pdf_corpus.py
```

## Pull requests

- décrire le problème et la solution ;
- préciser les tests exécutés ;
- ne pas changer le comportement du parser sans fixture ou corpus permettant de reproduire le cas ;
- maintenir la compatibilité des attributs existants sauf changement majeur documenté.
