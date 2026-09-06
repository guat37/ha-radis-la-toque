# Architecture

```text
Site public Radis la Toque
        │
        ├── catalogue établissements
        │       └── code métier Rxxxxx
        │
        └── PDF menu
                │
                ▼
      RadisLaToqueClient
                │
        extraction pdfplumber
                │
                ▼
          parser métier
                │
          WeeklyMenu / DayMenu
                │
                ▼
      DataUpdateCoordinator
          ├── sensors
          ├── calendar
          └── présentation sémantique
                     │
                     ▼
             carte Lovelace
```

## Séparation des responsabilités

- `client/client.py` : HTTP, cache conditionnel, téléchargement et extraction PDF.
- `client/parser.py` : reconstruction des jours/catégories. Ne dépend pas de Home Assistant.
- `client/models.py` : modèles immuables.
- `client/presentation.py` : semaine sélectionnée, calendrier et enrichissement sémantique non bloquant.
- `coordinator.py` : orchestration des mises à jour Home Assistant.
- `sensor.py` / `calendar.py` : entités Home Assistant.
- `frontend.py` : exposition sécurisée du JavaScript embarqué via `async_register_static_paths`.
- `www/radis-la-toque-card.js` : carte Lovelace autonome.

Le projet impose une règle : **la présentation et les badges ne peuvent jamais influencer le parsing**.
