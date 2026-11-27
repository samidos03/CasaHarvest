"""Fichier multi-villes : relevés de prix (DH/kg) vérifiés à la main dans la presse
+ série hebdomadaire Casablanca.

Usage : python -I construire_fichier_villes.py
"""
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

# (date du relevé, ville, produit, type, min, max, source, url/titre)
# Relevés lus et vérifiés un par un dans les articles collectés par collecte_villes.py
R = [
    # 7 mai 2019 : relevé officiel du ministère de l'Agriculture, tomate, marchés de gros
    *[("2019-05-07", v, "Tomate", "gros", p, p, "Ministère de l'Agriculture via LesEco/La Vie éco",
       "https://leseco.ma (09/05/2019) Hausse du prix de l'oignon. Les explications du ministère")
      for v, p in [("Fès", 3.40), ("Casablanca", 4.33), ("Oujda", 3.50), ("Marrakech", 3.50),
                   ("Rabat", 3.50), ("Tanger", 4.00)]],
    # 17 avril 2018 : plateforme ASAAR
    ("2018-04-17", "Fès", "Tomate", "gros", 1.50, 1.50, "ASAAR via La Vie éco", "lavieeco.com (20/04/2018) Tomates : les prix au plus bas"),
    *[("2018-04-17", v, "Tomate", "gros", None, 2.50, "ASAAR via La Vie éco", "lavieeco.com (20/04/2018) Tomates : les prix au plus bas")
      for v in ["Casablanca", "Rabat", "Marrakech", "Oujda", "Tanger"]],
    # novembre 2019 : marchés de gros de Marrakech (Al Massae via H24info)
    *[("2019-11-13", "Marrakech", p, "gros", lo, hi, "Al Massae via H24info", "h24info.ma (14/11/2019) Flambée des prix des fruits et légumes")
      for p, lo, hi in [("Tomate", None, 5), ("Pomme de terre", None, 6), ("Oignon sec", None, 5),
                        ("Haricot vert", 12, 14), ("Petit pois", 13, 15), ("Concombre", None, 5)]],
    # mars 2022 : Inezgane (Agadir), gros
    ("2022-03-14", "Agadir (Inezgane)", "Tomate", "gros", None, 5, "Consonews", "consonews.ma (21/03/2022) Flambée des prix de la tomate"),
    ("2022-03-14", "Rabat", "Tomate", "détail", 12, 13, "Consonews", "consonews.ma (21/03/2022) Flambée des prix de la tomate"),
    ("2022-03-14", "Casablanca", "Tomate", "détail", 12, 13, "Consonews", "consonews.ma (21/03/2022) Flambée des prix de la tomate"),
    # mars 2024 : Marrakech, wilaya (détail)
    ("2024-03-11", "Marrakech", "Tomate", "détail", None, 5, "Wilaya Marrakech-Safi via La Vie éco", "lavieeco.com (12/03/2024) Ramadan : Dans les marchés à Marrakech"),
    ("2024-03-11", "Marrakech", "Oignon sec", "détail", None, 8, "Wilaya Marrakech-Safi via La Vie éco", "lavieeco.com (12/03/2024) Ramadan : Dans les marchés à Marrakech"),
    # 30 décembre 2025 : hypermarchés d'Agadir et Casablanca (détail)
    *[("2025-12-30", "Agadir", p, "détail (hypermarché)", lo, hi, "LesEco", "leseco.ma (02/01/2026) Fruits et Légumes : le froid bouscule la production")
      for p, lo, hi in [("Courgette", 14, 15.95), ("Poivron", 7.95, 9.95), ("Tomate", 7.96, 7.96),
                        ("Pomme de terre", 6.95, 10.95), ("Oignon sec", 10.50, 10.50)]],
    *[("2025-12-30", "Casablanca", p, "détail (hypermarché)", lo, hi, "LesEco", "leseco.ma (02/01/2026) Fruits et Légumes : le froid bouscule la production")
      for p, lo, hi in [("Courgette", 16.95, 16.95), ("Poivron", 19.95, 19.95), ("Tomate", 7.96, 7.96), ("Oignon sec", 10.50, 10.50)]],
    # mars 2026 : Agadir, oignon (détail)
    ("2026-03-25", "Agadir", "Oignon sec", "détail", None, 18, "Consonews", "consonews.ma (26/03/2026) Marchés d'Agadir : l'oignon espagnol"),
    # avril 2026 : Rabat, tomate détail
    ("2026-04-08", "Rabat", "Tomate", "détail", 14, 14, "H24info / Consonews", "h24info.ma (16/04/2026) Tomates: le Maroc freine les exportations"),
    ("2026-04-15", "Rabat", "Tomate", "détail", 11, 11, "H24info / Consonews", "h24info.ma (16/04/2026) Tomates: le Maroc freine les exportations"),
    # fin octobre 2026 : Meknès (Hespress via Consonews)
    ("2026-10-28", "Meknès", "Tomate", "gros", None, 8, "Hespress via Consonews", "consonews.ma (30/10/2026) Tomate: le prix de détail atteint 11 DH"),
    ("2026-10-28", "Meknès", "Tomate", "détail", 10, 11, "Hespress via Consonews", "consonews.ma (30/10/2026) Tomate: le prix de détail atteint 11 DH"),
    # début novembre 2026
    ("2026-11-01", "Agadir", "Tomate", "détail", 15, None, "Hibapress", "fr.hibapress.com (02/11/2026) Agadir.. Les prix de la tomate dépassent 15 dirhams"),
    ("2026-11-01", "Rabat", "Tomate", "détail", 15, None, "Hibapress", "fr.hibapress.com (02/11/2026) Les tomates dépassent 15 dirhams"),
    *[("2026-11-01", "Rabat", p, "détail", 7, 10, "Hibapress", "fr.hibapress.com (02/11/2026) Les tomates dépassent 15 dirhams")
      for p in ["Oignon sec", "Pomme de terre", "Poivron"]],
    ("2026-11-07", "Rabat", "Tomate", "détail", 13, 15, "Hespress FR via AgriMaroc", "agrimaroc.ma (11/11/2026) Tomate : l'export vers l'Afrique gelé"),
    ("2026-11-07", "Agadir (Inezgane)", "Tomate", "gros", 6.7, 6.7, "Hespress FR via AgriMaroc", "agrimaroc.ma (11/11/2026) Tomate : l'export vers l'Afrique gelé"),
]
rel = pd.DataFrame(R, columns=["date_releve", "ville", "produit", "type_prix", "prix_min_DH_kg", "prix_max_DH_kg", "source", "reference"])
rel["prix_moyen_DH_kg"] = rel[["prix_min_DH_kg", "prix_max_DH_kg"]].mean(axis=1, skipna=False).round(2)
rel = rel.sort_values(["ville", "produit", "date_releve"])

casa = pd.read_csv("prix_hebdo_casablanca_moyen.csv", index_col=0)

couv = rel.groupby(["ville", "type_prix"]).agg(nb_releves=("produit", "size"),
                                               produits=("produit", lambda s: ", ".join(sorted(set(s)))),
                                               premier=("date_releve", "min"), dernier=("date_releve", "max"))

notes = [
    "Aucune source publique ne publie de prix hebdomadaires par produit pour les villes autres que Casablanca "
    "(la plateforme ASAAR du ministère, qui couvrait Fès, Rabat, Marrakech, Oujda, Tanger et Inezgane, est hors ligne).",
    "Feuille Releves_villes : prix en DH/kg trouvés dans la presse (45 articles examinés), vérifiés un par un. "
    "Ce sont des relevés ponctuels, pas une série continue. type_prix = gros ou détail : ne pas les mélanger dans un modèle.",
    "Prix min/max vides = l'article donne seulement un plafond (« jusqu'à X ») ou un plancher (« dépasse X »). "
    "Prix moyen calculé seulement quand min et max sont connus.",
    "Feuille Casablanca_hebdo : prix de gros hebdomadaires moyens de Casablanca (référence nationale, voir prix_hebdo_casablanca.xlsx).",
]
with pd.ExcelWriter("prix_villes_maroc.xlsx") as x:
    pd.DataFrame({"Note": notes}).to_excel(x, sheet_name="Lisez-moi", index=False)
    rel.to_excel(x, sheet_name="Releves_villes", index=False)
    couv.to_excel(x, sheet_name="Couverture_releves")
    casa.to_excel(x, sheet_name="Casablanca_hebdo")
rel.to_csv("prix_releves_villes.csv", index=False, encoding="utf-8-sig")
print(len(rel), "relevés,", rel.ville.nunique(), "villes")
print(couv.to_string())
