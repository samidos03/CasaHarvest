"""Génère et exécute le notebook CasaHarvest_modules_1_2.ipynb (après python run_casaharvest.py)."""
from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

HERE = Path(__file__).resolve().parent
nb = nbf.v4.new_notebook()
C = []
md = lambda t: C.append(nbf.v4.new_markdown_cell(t))  # noqa: E731
code = lambda t: C.append(nbf.v4.new_code_cell(t))   # noqa: E731

md("""# CasaHarvest — modules 1 et 2 : de l'eau à la récolte

**Région** : Casablanca-Settat, 4 zones (Settat-Berrechid, El Jadida-Sidi Bennour, Benslimane, préfectures de Casablanca), **depuis 2010**.

| Module | Question | Données | Modèles |
|---|---|---|---|
| 1. Rendement agricole | Quel rendement de céréales cette année ? | Rendements HCP par province (FEWS NET), 2010-2023 ; pluie CHIRPS ; humidité du sol ERA5-Land | Ridge, XGBoost, hybride |
| 2. Risque de sécheresse | Y aura-t-il une sécheresse le mois prochain ? | Indice SPI mensuel (CHIRPS), humidité du sol, 2010-2026 | Ridge, XGBoost |

Les résultats sont calculés par `run_casaharvest.py` et lus ici dans `resultats/`.""")

code("""import sys
from pathlib import Path
import pandas as pd
from IPython.display import Image, display
pd.set_option("display.precision", 2); pd.set_option("display.width", 200)
R = Path("resultats")""")

md("""## Module 1 — Prévision du rendement des céréales

**Cible** : rendement (q/ha) du blé tendre, du blé dur et de l'orge, par zone et par campagne (167 observations : 4 zones × 14 campagnes × 3 cultures).

**Deux moments de prévision** :
- **fin mars** (prévision précoce) : SPI-6 de mars (sécheresse des 6 derniers mois) + humidité du sol en hiver ;
- **fin mai** (fin de campagne) : SPI-6 de mars + humidité du sol au printemps + nombre de jours ≥ 30 °C au printemps.

**Choix des variables** : avec seulement 14 campagnes, un jeu réduit est plus stable. Le SPI-6 de mars seul explique déjà l'essentiel (R² ≈ 0,47 avec XGBoost) ; les cumuls de pluie sont redondants avec lui.

**Évaluation** : validation croisée *une campagne laissée de côté* — toutes les zones d'une même année sont mises de côté ensemble (elles partagent la même météo ; sinon l'évaluation serait trop optimiste).""")

code("""print("Précision (validation croisée, toutes zones et cultures) :")
display(pd.read_csv(R / "m1_metriques.csv", index_col=[0, 1]))
print("Au niveau de la région (rendement moyen pondéré par les surfaces) :")
display(pd.read_csv(R / "m1_metriques_region.csv", index_col=[0, 1]))
display(Image(R / "fig_m1_rendement.png"))""")

md("""**Lecture**

- La **sécheresse de mars (SPI-6)** est le facteur dominant : quand il est sous −1, le rendement s'effondre (souvent < 10 q/ha) ; au-dessus de 0, il dépasse en général 20 q/ha.
- **XGBoost** capte mieux cette relation en « marche d'escalier » que la Ridge linéaire (R² 0,47 contre 0,37, erreur moyenne ±6,3 q/ha).
- Mais **XGBoost ne sait pas extrapoler** : en 2026, le SPI-6 de mars atteint **+1,91** en moyenne sur la région, plus humide que toutes les années 2010-2023 (maximum régional +1,44, zone grisée sur la figure). XGBoost répète alors ce qu'il a vu pour l'année la plus humide connue et prévoit 18,9 q/ha.
- D'où le **modèle hybride** : XGBoost quand le climat ressemble au passé, Ridge (qui prolonge la tendance) quand une variable sort de la plage observée. En validation croisée, il est un peu moins précis que XGBoost (R² 0,43), mais il est robuste aux années exceptionnelles.
- Cas particulier : **2010** était très humide mais avec un rendement moyen (≈ 10 q/ha) ; l'excès d'eau peut aussi nuire aux cultures, ce que le modèle ne capte pas.""")

code("""print("Prévisions des campagnes sans rendement publié (fin mai) :")
display(pd.read_csv(R / "m1_previsions_region_2024_2026.csv", header=[0, 1], index_col=0))""")

md("""**Contrôle externe (campagne 2026)** : la Direction régionale de l'agriculture annonce environ **25,8 millions de quintaux** de céréales pour Casablanca-Settat (≈ 30 q/ha sur 852 555 ha). Le modèle hybride prévoit **26,3 millions de quintaux (31,9 q/ha)** — un écart d'environ 2 % ; XGBoost seul aurait prévu 15,6 Mqx.

*Limites* : 2024 et 2025 n'ont pas pu être vérifiées (pas de bilan régional publié trouvé) ; au niveau national, 2025 a été meilleure que 2024 (≈ 44 contre 31 Mqx), alors que le modèle prévoit l'inverse pour la région — la pluie tardive de mars 2025 est peut-être mal captée. La production prévue utilise la surface moyenne des 3 dernières campagnes connues.""")

md("""## Module 2 — Prévision du risque de sécheresse

**Cible** : SPI-3 du mois suivant (h = 1, 2, 3 mois), par zone. SPI ≤ −1 : sécheresse modérée ; ≤ −1,5 : sévère ; ≤ −2 : extrême.
**Variables** (connues au mois t) : SPI-1, SPI-3, SPI-6, SPI-12, anomalie d'humidité du sol, mois visé, zone.
**Saison** : mois visés d'octobre à mai uniquement (en été il ne pleut presque pas, le SPI n'a pas de sens).
**Évaluation** : validation temporelle à fenêtre croissante — chaque année de 2018 à 2026 est prévue avec un modèle entraîné sur les années précédentes seulement.
**Alerte** : la régression ramène les prévisions vers la normale ; on déclenche une alerte dès que le SPI-3 prévu est ≤ −0,5 (seuil choisi sur la validation).""")

code("""display(pd.read_csv(R / "m2_metriques.csv", index_col=[0, 1]))
display(Image(R / "fig_m2_secheresse.png"))""")

md("""**Lecture**

- **À 1 mois**, la prévision est fiable : R² 0,63, et le système d'alerte repère **76 % des sécheresses** à l'avance (41 % de fausses alertes). C'est en partie mécanique : le SPI-3 du mois prochain contient déjà 2 mois de pluie connus.
- **À 2 mois**, la fiabilité est faible (R² 0,26) ; **à 3 mois**, le modèle ne fait pas mieux que la normale (R² négatif) : la pluie au Maroc est imprévisible au-delà de quelques semaines à partir des seules observations locales.
- La **Ridge** est meilleure que XGBoost ici : la relation est essentiellement linéaire (persistance) et les données sont peu nombreuses.""")

code("""print("Situation actuelle (dernier mois connu) :")
display(pd.read_csv(R / "m2_etat_actuel.csv"))
print("Prévision des 3 prochains mois (Ridge) :")
display(pd.read_csv(R / "m2_prevision_3_mois.csv"))""")

md("""## Conclusions et lien avec le module 3 (prix)

1. **Eau → récolte** : la sécheresse de fin d'hiver (SPI-6 de mars) explique environ la moitié des variations de rendement des céréales dans la région. Le modèle hybride donne une prévision dès **fin mars**, trois mois avant la récolte, et a reproduit à 2 % près la prévision officielle 2026.
2. **Sécheresse** : une alerte fiable est possible **un mois à l'avance** ; au-delà, il faudrait des prévisions saisonnières météorologiques (non disponibles en données ouvertes ici).
3. **Récolte → marché** : les céréales et les fruits et légumes du module 3 ne réagissent pas de la même façon ; le lien entre rendement céréalier et prix des légumes à Casablanca est indirect et à présenter avec prudence.
4. **Limites** : 14 campagnes seulement ; SPI calibré sur 17 ans (30 ans recommandés) ; rendements 2024-2026 non encore publiés.""")

nb["cells"] = C
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
ExecutePreprocessor(timeout=1200, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(HERE)}})
nbf.write(nb, HERE / "CasaHarvest_modules_1_2.ipynb")
print("notebook écrit :", HERE / "CasaHarvest_modules_1_2.ipynb")
