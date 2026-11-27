"""Fusionne toutes les données en un jeu de données enrichi pour la prévision.

Entrées : prix_gros_casablanca_hebdo_long.csv (presse française), prix_gros_arabe_long.csv (presse arabe),
          meteo_hebdo_villes.csv, calendrier_fetes.csv
Sorties : prix_gros_hebdo_fusion.csv (tous les relevés, tous marchés), donnees_prevision.xlsx,
          donnees_prevision_ml.csv (table prête pour le machine learning)

Usage : python -I construire_donnees_enrichies.py
"""
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
VILLE = {"Casablanca": "Casablanca", "Inezgane (Agadir)": "Agadir", "Agadir": "Agadir", "Meknès": "Meknès",
             "Fès": "Fès", "Marrakech": "Marrakech", "Rabat": "Rabat", "Tanger": "Tanger", "Oujda": "Oujda"}

# ---------------------------------------------------------------- 1. relevés de prix
fr = pd.read_csv("prix_gros_casablanca_hebdo_long.csv").rename(columns={"date_bulletin": "semaine"})
fr["marche"] = "Casablanca"
fr["type_valeur"] = np.where(fr.prix_min_DH_kg.notna() & fr.prix_max_DH_kg.notna(), "fourchette",
                             np.where(fr.prix_max_DH_kg.notna(), "plafond", "plancher"))
fr["langue"] = "fr"
ar = pd.read_csv("prix_gros_arabe_long.csv")
cols = ["semaine", "marche", "produit", "prix_min_DH_kg", "prix_max_DH_kg", "prix_moyen_DH_kg", "type_valeur",
        "source", "url", "langue", "date_publication"]
rel = pd.concat([fr[cols], ar[cols]], ignore_index=True)
# toutes les dates ramenées au mercredi (jour du bulletin) de leur semaine : mercredi précédent ou le jour même
d = pd.to_datetime(rel.semaine)
rel["semaine"] = (d - pd.to_timedelta((d.dt.weekday - 2) % 7, unit="D")).dt.strftime("%Y-%m-%d")
# priorité : presse française (bulletin complet) > fourchette arabe > valeur arabe
rel["prio"] = rel.langue.map({"fr": 0, "ar": 1}) + rel.type_valeur.map(
    {"fourchette": 0, "moyenne": 0.3, "valeur": 0.5, "plafond": 0.8, "plancher": 0.9}).fillna(1)
rel = rel.sort_values("prio").drop_duplicates(["semaine", "marche", "produit"]).drop(columns="prio")
rel.insert(2, "ville", rel.marche.map(VILLE))
rel = rel.sort_values(["marche", "produit", "semaine"])
rel.to_csv("prix_gros_hebdo_fusion.csv", index=False, encoding="utf-8-sig")
# fiabilité : un prix cité seul (« valeur ») s'écarte en médiane de 31 % du bulletin officiel (contrôle sur Casablanca)
# -> exclu pour Casablanca (où le bulletin existe), gardé mais signalé pour les autres marchés
rel["fiabilite"] = np.where(rel.type_valeur.isin(["fourchette", "moyenne"]), "haute",
                            np.where(rel.type_valeur == "valeur", "faible", "partielle (min ou max seul)"))
utilisable = rel[rel.prix_moyen_DH_kg.notna() & ~((rel.marche == "Casablanca") & (rel.type_valeur == "valeur"))]
rel.to_csv("prix_gros_hebdo_fusion.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- 2. table ML : semaine × marché × produit
met = pd.read_csv("meteo_hebdo_villes.csv")
cal = pd.read_csv("calendrier_fetes.csv")

sem = pd.date_range("2024-03-20", rel.semaine.max(), freq="W-WED").strftime("%Y-%m-%d")
blocs = []
for (mk, p), g in utilisable[utilisable.semaine >= "2024-01-01"].groupby(["marche", "produit"]):
    if len(g) < 5:
        continue
    b = pd.DataFrame({"semaine": sem, "marche": mk, "ville": VILLE[mk], "produit": p})
    b = b.merge(g[["semaine", "prix_moyen_DH_kg", "prix_min_DH_kg", "prix_max_DH_kg", "type_valeur", "fiabilite"]],
                on="semaine", how="left")
    b["prix_releve"] = b.prix_moyen_DH_kg.notna().astype(int)
    # retards calculés sur la série interpolée (log) : utilisables comme variables explicatives
    s = np.exp(np.log(b.prix_moyen_DH_kg).interpolate(limit_area="inside"))
    b["prix_interpole_DH_kg"] = s.round(2)
    for k in (1, 2, 4, 52):
        b[f"prix_lag{k}"] = s.shift(k).round(2)
    blocs.append(b)
ml = pd.concat(blocs, ignore_index=True)
dt = pd.to_datetime(ml.semaine)
ml["annee"], ml["mois"], ml["semaine_annee"] = dt.dt.year, dt.dt.month, dt.dt.isocalendar().week.astype(int).values
ml["saison"] = ml.mois.map({12: "hiver", 1: "hiver", 2: "hiver", 3: "printemps", 4: "printemps", 5: "printemps",
                            6: "été", 7: "été", 8: "été", 9: "automne", 10: "automne", 11: "automne"})
ml = ml.merge(met, on=["semaine", "ville"], how="left")
# météo d'Agadir = bassin de production (Souss) : pertinente pour tous les marchés
souss = met[met.ville == "Agadir"].drop(columns="ville").add_suffix("_Agadir").rename(columns={"semaine_Agadir": "semaine"})
ml = ml.merge(souss, on="semaine", how="left")
ml = ml.merge(cal, on="semaine", how="left")
ml = ml.sort_values(["marche", "produit", "semaine"])
ml.to_csv("donnees_prevision_ml.csv", index=False, encoding="utf-8-sig")

# ---------------------------------------------------------------- 3. Excel
couv = (utilisable.groupby(["marche", "produit"])
        .agg(semaines=("semaine", "nunique"), premiere=("semaine", "min"), derniere=("semaine", "max"))
        .sort_values("semaines", ascending=False))
resume = (utilisable.assign(periode=np.where(utilisable.semaine >= "2024-01-01", "2024-2026", "avant 2024"))
          .groupby(["marche", "periode"]).agg(semaines=("semaine", "nunique"), releves=("produit", "size")))
notes = [
    "Jeu de données enrichi pour la prévision des prix de gros des fruits, légumes et viandes au Maroc.",
    "Releves_prix : tous les prix de gros (DH/kg) trouvés dans la presse marocaine en français (Médias24, H24info, "
    "LesEco...) et en arabe (Hespress, Alyaoum24, Barlamane, Febrayer), pour les marchés de gros de Casablanca "
    "(bulletin hebdomadaire de Casablanca Prestations), d'Inezgane/Agadir (note quotidienne du marché) et d'autres villes.",
    "type_valeur : fourchette (min-max, prix moyen = (min+max)/2) ; moyenne (prix moyen publié) ; valeur (prix unique "
    "cité) ; plafond / plancher (seulement le max / le min : pas de prix moyen).",
    "Contrôle (Casablanca, semaines présentes dans les deux langues) : fourchettes de la presse arabe = bulletin "
    "officiel (écart médian 0 % sur 63 cas) ; prix cités seuls (type « valeur ») : écart médian 31 % -> fiabilite = "
    "faible. Ils sont exclus pour Casablanca et gardés (signalés) pour les autres marchés.",
    "Table_ML : une ligne par semaine × marché × produit (2024-2026), avec prix (prix_releve = 1 si réellement publié), "
    "retards (lag 1, 2, 4, 52 semaines), calendrier (mois, saison, Ramadan, Aïd), météo de la ville et du Souss "
    "(Agadir, principal bassin de production).",
    "Pour entraîner un modèle : cible = prix_moyen_DH_kg sur les lignes prix_releve = 1 uniquement.",
    "Meteo_villes : Open-Meteo (réanalyse ERA5), 18 villes, semaines 2017-2026. "
    "Calendrier : dates de Ramadan et de l'Aïd al-Adha (± 1 jour).",
]
with pd.ExcelWriter("donnees_prevision.xlsx") as x:
    pd.DataFrame({"Note": notes}).to_excel(x, sheet_name="Lisez-moi", index=False)
    resume.to_excel(x, sheet_name="Resume")
    couv.to_excel(x, sheet_name="Couverture")
    ml.to_excel(x, sheet_name="Table_ML", index=False)
    rel.to_excel(x, sheet_name="Releves_prix", index=False)
    met.to_excel(x, sheet_name="Meteo_villes", index=False)
    cal.to_excel(x, sheet_name="Calendrier", index=False)
print(resume.to_string())
print("Table_ML :", ml.shape, "| lignes avec prix relevé :", int(ml.prix_releve.sum()),
      "| séries :", ml.groupby(["marche", "produit"]).ngroups)
print(couv.head(15).to_string())
