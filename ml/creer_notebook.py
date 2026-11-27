"""Génère et exécute le notebook de synthèse Projet_ML_prevision_prix.ipynb.

Usage : python creer_notebook.py    (après python run_all.py)
"""
from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

HERE = Path(__file__).resolve().parent
nb = nbf.v4.new_notebook()
C = []


def md(t):
    C.append(nbf.v4.new_markdown_cell(t))


def code(t):
    C.append(nbf.v4.new_code_cell(t))


md("""# Prévision des prix des produits alimentaires au Maroc — XGBoost

**Sujet 26** : prévoir les prix (tomate, pomme de terre, oignon, agrumes, viandes…) selon la saison et l'offre.

**Données** : prix de gros **hebdomadaires** en DH/kg du marché de gros de Casablanca, 2024-2026, 19 produits.
**Modèle** : XGBoost global, stratégie multi-horizon directe (1 à 8 semaines).

**Protocole** : backtest à origines glissantes — à chaque date d'origine, le modèle est ré-entraîné avec les seules données connues à cette date, puis ses prévisions sont comparées aux prix réels.

Les calculs sont faits par `run_all.py` (environ 1 minute) ; ce notebook lit les résultats dans `resultats/`. Pour tout recalculer, mettre `RECALCULER = True`.""")

code("""import subprocess, sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import Image, display
pd.set_option("display.precision", 2)
R = Path("resultats")
RECALCULER = False
if RECALCULER:
    subprocess.run([sys.executable, "run_all.py"], check=True)""")

md("""## 1. Les données

- **Prix hebdomadaires** : bulletins hebdomadaires de Casablanca Prestations (marché de gros des fruits et légumes et abattoirs), collectés dans la presse marocaine en français et en arabe (31 sites), contrôlés (écart médian de 0 % entre les deux langues sur les fourchettes min-max). Prix moyen = (min + max) / 2.
- **Variables exogènes** : météo hebdomadaire (Open-Meteo/ERA5) du Souss (principal bassin de production) et de Casablanca, calendrier (Ramadan, Aïd al-Adha).
- Les semaines sans bulletin dans la presse sont interpolées pour calculer les variables, mais **seules les semaines réellement relevées servent de cible** d'apprentissage et d'évaluation.""")

code("""sys.path.insert(0, ".")
from donnees import series_hebdo
w, observe, exo = series_hebdo()
print(f"{w.shape[1]} produits, {len(w)} semaines ({w.index[0]:%Y-%m-%d} -> {w.index[-1]:%Y-%m-%d}), "
      f"{int(observe.values.sum())} prix relevés")
fig, ax = plt.subplots(figsize=(12, 4))
for p in ["Tomate", "Pomme de terre", "Carotte", "Orange"]:
    ax.plot(w.index, w[p], label=p)
    ax.scatter(w.index[observe[p]], w[p][observe[p]], s=8)
ax.set(title="Prix de gros hebdomadaires — marché de gros de Casablanca", ylabel="DH/kg"); ax.legend(); ax.grid(alpha=.3)
plt.show()
display(observe.sum().sort_values(ascending=False).rename("semaines relevées").to_frame().T)""")

md("""## 2. Le modèle XGBoost

**Formulation** : stratégie *directe* — un modèle par horizon h = 1…8 semaines, global (tous les produits ensemble). La cible est la variation du log-prix `log p(t+h) − log p(t)`, ce qui rend les produits comparables (quelques DH/kg pour la tomate, plus de 100 DH/kg pour la viande). La prévision est `p(t) × exp(ŷ)`.

**Variables** (toutes connues à la date t) :

| Groupe | Variables |
|---|---|
| Dynamique du prix | variations sur 1, 4 et 13 semaines ; écart à la moyenne et volatilité sur 8 semaines |
| Saisonnalité | effet saisonnier attendu (profil harmonique estimé sur l'historique) ; évolution l'an passé à la même période ; semaine et mois cibles |
| Demande | Ramadan, semaine avant Ramadan, Aïd al-Adha, semaine avant l'Aïd (dans la semaine cible) |
| Offre | pluie et températures du Souss sur 4 semaines ; pluie à Casablanca |
| Produit | produit et famille (légume, fruit, viande), en variables catégorielles |

**Réglage** : 4 configurations testées, choix sur la première moitié des origines (validation) → arbres de profondeur 2, 400 arbres, taux d'apprentissage 0,01, forte régularisation (λ = 30, poids minimal des feuilles = 30). Perte de Huber (robuste aux pics de prix).

**Sans fuite de données** : à chaque origine, la série est reconstruite avec les seuls relevés connus, et la prévision part du dernier prix réellement relevé.""")

md("""## 3. Résultats

Métriques par horizon :
- **MAPE** : erreur absolue moyenne en % ;
- **erreur médiane** : la moitié des prévisions font mieux ;
- **RMSE (log)** : racine de l'erreur quadratique moyenne sur le log-prix ;
- **à ±10 %** : part des prévisions à moins de 10 % du prix réel ;
- **sens correct** : part des cas où XGBoost prévoit le bon sens de variation (hausse/baisse), quand le prix réel bouge d'au moins 2 %.""")

code("""display(pd.read_csv(R / "xgb_hebdo_erreur_horizon.csv", index_col=0))
display(Image(R / "fig1_xgb_hebdo.png"))""")

code("""print("Erreur par produit (tous horizons) :")
display(pd.read_csv(R / "xgb_hebdo_erreur_produit.csv", index_col=0))""")

md("""**Lecture des résultats**

- À **1 semaine**, l'erreur médiane n'est que de **2,7 %** et **3 prévisions sur 4** sont à moins de 10 % du prix réel. L'erreur moyenne (12,9 %) est plus élevée car quelques **chocs de prix** (vagues de chaleur, maladies, arrêts des exportations) produisent de grosses erreurs.
- La précision **diminue avec l'horizon** : erreur médiane de 17 % et un tiers des prévisions à ±10 % à 8 semaines.
- Le **sens de variation** est correct dans un peu plus de la moitié des cas (≈ 52-55 %) : prévoir la direction des prix de gros reste difficile à court terme.
- Les produits les plus prévisibles sont les produits importés ou stockables (pomme importée, viande ovine, banane) ; les plus difficiles sont les légumes frais (tomate, courgette, concombre, clémentine).
- L'**importance des variables** est conforme à l'intuition économique : l'effet saisonnier attendu, l'écart à la moyenne récente (retour à la moyenne), le Ramadan et la météo du Souss sont les facteurs les plus utilisés.""")

code("""prev = pd.read_csv(R / "xgb_hebdo_prevision_8_semaines.csv")
print("Prévision XGBoost des 8 prochaines semaines (DH/kg) :")
display(prev.pivot_table(index="produit", columns="semaine", values="prevision_XGBoost_DH_kg"))""")

md("""## 4. Conclusions

1. **XGBoost** prévoit les prix de gros hebdomadaires de Casablanca avec une erreur médiane de 2,7 % à 1 semaine et 17 % à 8 semaines ; l'erreur moyenne (13 % à 27 %) est dominée par quelques chocs de prix imprévisibles.
2. Le modèle **identifie les facteurs** des prix : saison, retour à la moyenne, Ramadan, météo du Souss.
3. **Limites** : un seul marché (Casablanca) ; semaines manquantes dans la presse (81 semaines relevées sur 147) ; environ 2,5 ans d'historique, ce qui limite l'apprentissage — quelques années de bulletins supplémentaires permettraient à XGBoost d'exploiter davantage les variables d'offre ; prix de gros et non de détail.""")

nb["cells"] = C
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
ep = ExecutePreprocessor(timeout=1200, kernel_name="python3")
ep.preprocess(nb, {"metadata": {"path": str(HERE)}})
nbf.write(nb, HERE / "Projet_ML_prevision_prix.ipynb")
print("notebook écrit et exécuté :", HERE / "Projet_ML_prevision_prix.ipynb")
