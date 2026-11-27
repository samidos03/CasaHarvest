# 🌾 CasaHarvest — de l'eau à la récolte, de la récolte au marché

Projet de Master IA/ML : plateforme d'apprentissage automatique pour la **région Casablanca-Settat**
(chef-lieu : Casablanca ; 9 préfectures et provinces — préfectures de Casablanca et Mohammedia ; provinces de Settat,
El Jadida, Sidi Bennour, Berrechid, Benslimane, Nouaceur et Médiouna).

## Région Casablanca-Settat : espace citoyen et espace analytique

| Thème | Données (réelles) | Modèle | Résultat principal |
|---|---|---|---|
| 🌧️ Précipitations | CHIRPS v2.0, 9 provinces, sept. 2009 → sept. 2026 | SPI-3 ; prévision sec/normal/pluvieux (régression logistique) | Saison 2025-26 : ~150 % de la normale ; la pluie du mois suivant n'est **pas** prévisible (RPSS ≈ 0) |
| 🌱 Humidité du sol | ERA5-Land (Open-Meteo), 2009 → oct. 2026 | Ridge / forêt aléatoire / XGBoost vs persistance | R² 0,70 à 1 mois (persistance : 0,49) |
| 🌾 Récoltes | HCP par province (FEWS NET), blé tendre, blé dur, orge, 2010-2023 | Ridge / forêt aléatoire / XGBoost, validation « une campagne laissée de côté » | XGBoost : 6,8 q/ha d'erreur, R² 0,48 ; 2026 : 22,9 Mqx prévus (officiel 25,8) ; zones à risque ; scénarios 2027 |
| 💧 Barrage Al Massira | 39 relevés officiels 2019-2026 (ministère de l'Équipement et de l'Eau, via la presse) | Bilan hydrique calibré + ensemble de scénarios de pluie | Niveau à 7, 30, 90 jours avec intervalle 80 % ; risque de pénurie |

- **Espace citoyen** (`/citoyen`) : une province, 4 cartes (pluie, sol, récolte, eau), un code couleur et une phrase ; français / arabe (`/citoyen?langue=ar`).
- **Espace analytique** (`/analytique`) : cartes choroplèthes des 9 provinces, séries, SPI, comparaison des modèles, importance des variables, réel vs prévu, scénarios, relevés sourcés, tableau du statut des données.

```bash
python data/construire_provinces.py      # données des 9 provinces (data/region/)
python ml/run_region.py                  # modèles (ml/resultats/r_*)  ~30 s
# facultatif, sur un PC connecté : ERA5-Land par province (+ T min), NDVI MODIS, SoilGrids
python data/collecte_provinces.py && python data/construire_provinces.py && python ml/run_region.py
```

Limites : ERA5-Land est disponible pour 4 zones (attribuées aux 9 provinces) tant que `collecte_provinces.py` n'a pas été
lancé ; NDVI et SoilGrids sont à télécharger avec ce script ; les apports et transferts vers Al Massira ne sont pas publiés
en série (estimés par la pluie efficace) ; les rendements 2024-2026 ne sont pas encore publiés par province.

## Autres analyses du projet

**Volet campagne — région Casablanca-Settat**

| Module | Question | Modèle |
|---|---|---|
| 1 · 💧 Eau & sécheresse | Y aura-t-il une sécheresse le mois prochain ? | Ridge (indice SPI-3) |
| 2 · 🌾 Récolte | Quel rendement de céréales cette année ? | Hybride XGBoost + garde-fou Ridge |
| 3 · 🧺 Prix du marché | Quel prix de gros pour les fruits et légumes ? | XGBoost (1 à 8 semaines) |

La sécheresse explique la récolte, la récolte pèse sur les prix.

## Organisation

```
data/   collecte et préparation des données (presse marocaine, FEWS NET/HCP, CHIRPS, ERA5-Land)
ml/     modèles, évaluation, notebooks (Projet_ML_prevision_prix.ipynb, CasaHarvest_modules_1_2.ipynb)
app/    application web : API Python (FastAPI) + interface React / Bootstrap
```

## Lancer l'application

```bash
cd app/frontend && npm install && npm run build
cd ../.. && python -m uvicorn main:app --app-dir app/backend --port 8000
```

Puis ouvrir http://localhost:8000 — détails dans [app/README.md](app/README.md).

## Recalculer les résultats

```bash
python data/construire_casaharvest.py   # données des modules 1 et 2
python ml/run_all.py                    # module prix (XGBoost)
python ml/run_casaharvest.py            # modules récolte et sécheresse
```
