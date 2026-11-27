# CasaHarvest — application web (React + Bootstrap + API Python)

```
app/
├── backend/main.py   API FastAPI : charge les modèles (ml/, data/) et sert les résultats en JSON
└── frontend/         interface React (Vite) + Bootstrap 5 + graphiques Recharts
```

## Lancer l'application (un seul serveur)

```bash
cd app/frontend
npm install          # la première fois seulement
npm run build        # compile l'interface dans app/frontend/dist
cd ../..
python -m uvicorn main:app --app-dir app/backend --port 8000
```

Puis ouvrir http://localhost:8000 (le démarrage prend ~10 s : entraînement des modèles XGBoost de prix).

## Développement (rechargement automatique de l'interface)

Deux terminaux :

```bash
python -m uvicorn main:app --app-dir app/backend --port 8000 --reload
```

```bash
cd app/frontend && npm run dev     # http://localhost:5173 (les appels /api sont redirigés vers le port 8000)
```

## Pages

| Page | Module | Modèle |
|---|---|---|
| Accueil | les deux chaînes : eau → récolte → marché | — |
| Eau & sécheresse | module 2 : SPI-3 par zone, prévision 1 à 3 mois | Ridge |
| Récolte | module 1 : rendement des céréales, simulateur climatique | hybride XGBoost + garde-fou Ridge |
| Prix du marché | module 3 : prix de gros hebdomadaires (19 produits) | XGBoost |
| À propos | schéma grand public, données, limites | — |

Les résultats d'évaluation sont lus dans `ml/resultats/` : relancer `python ml/run_all.py` (prix) et
`python ml/run_casaharvest.py` (récolte et sécheresse) après une mise à jour des données.
