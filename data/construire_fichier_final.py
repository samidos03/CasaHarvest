"""Construit le fichier Excel final des prix hebdomadaires (Casablanca) à partir
de prix_gros_casablanca_hebdo_long.csv (produit par extract_prix_presse.py).

Usage : python -I construire_fichier_final.py
"""
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

d = pd.read_csv("prix_gros_casablanca_hebdo_long.csv")
ORDER = ["Tomate", "Pomme de terre", "Oignon frais", "Oignon sec", "Carotte", "Courgette", "Aubergine",
         "Concombre", "Chou-fleur", "Chou blanc", "Courge", "Haricot vert", "Poivron", "Petit pois", "Fève",
         "Orange", "Clémentine", "Banane locale", "Banane importée", "Pomme locale", "Pomme importée", "Poire",
         "Raisin", "Pastèque", "Melon", "Avocat", "Grenade", "Fraise", "Datte", "Viande bovine", "Viande ovine"]
cols = [p for p in ORDER if p in set(d.produit)]
# les quelques relevés isolés avant 2024 restent dans Detail_avec_sources, mais pas dans le tableau hebdomadaire
start = pd.Timestamp(d.loc[d.date_bulletin >= "2024-01-01", "date_bulletin"].min())
start = start - pd.Timedelta(days=(start.weekday() - 2) % 7)
full = pd.date_range(start, d.date_bulletin.max(), freq="W-WED").strftime("%Y-%m-%d")


def wide(v):
    w = d.pivot_table(index="date_bulletin", columns="produit", values=v).reindex(full).reindex(columns=cols)
    w.index.name = "semaine (mercredi)"
    return w


mo, mn, mx = wide("prix_moyen_DH_kg"), wide("prix_min_DH_kg"), wide("prix_max_DH_kg")
known = mn.notna() | mx.notna()
couverture = pd.DataFrame({
    "semaines_renseignees": known.sum(),
    "premiere_semaine": [known.index[known[c]].min() if known[c].any() else None for c in cols],
    "derniere_semaine": [known.index[known[c]].max() if known[c].any() else None for c in cols],
    "prix_moyen_min": mo.min().round(2), "prix_moyen_max": mo.max().round(2),
})
couverture.index.name = "produit"

n_weeks = len(full)
n_known = int(known.any(axis=1).sum())
notes = [
    "Source : bulletins hebdomadaires de Casablanca Prestations (marché de gros des fruits et légumes "
    "et abattoirs de Casablanca), repris par la presse marocaine (H24info, Challenge.ma, Médias24, LesEco...).",
    "Prix de gros en DH/kg : fourchette minimum–maximum selon la qualité. "
    "Prix moyen = (min + max) / 2, calculé seulement si les deux sont connus.",
    f"Une ligne par semaine (mercredi, jour du bulletin), du {full[0]} au {full[-1]} : "
    f"{n_known} semaines renseignées sur {n_weeks}. Case vide = semaine non couverte par la presse ou produit non cité.",
    "Extraction automatique du texte des articles (scripts collecte_articles.py et extract_prix_presse.py), "
    "vérifiée par sondage : quelques erreurs ou oublis restent possibles. "
    "La colonne url de la feuille Detail_avec_sources permet de vérifier chaque valeur.",
    "Couverture : Casablanca uniquement. Pour la tendance longue : prix FAOSTAT annuels (prix_produits_maroc.xlsx).",
]
with pd.ExcelWriter("prix_hebdo_casablanca.xlsx") as x:
    pd.DataFrame({"Note": notes}).to_excel(x, sheet_name="Lisez-moi", index=False)
    mo.to_excel(x, sheet_name="Prix_moyen_hebdo")
    mn.to_excel(x, sheet_name="Prix_min_hebdo")
    mx.to_excel(x, sheet_name="Prix_max_hebdo")
    couverture.to_excel(x, sheet_name="Couverture")
    d.to_excel(x, sheet_name="Detail_avec_sources", index=False)
mo.to_csv("prix_hebdo_casablanca_moyen.csv", encoding="utf-8-sig")
print(f"{n_known} semaines renseignées sur {n_weeks} ({full[0]} -> {full[-1]}), {len(cols)} produits")
print(couverture.semaines_renseignees.sort_values(ascending=False).head(12).to_string())
