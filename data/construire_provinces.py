"""CasaHarvest Région — données des 9 préfectures et provinces de Casablanca-Settat.

Région Casablanca-Settat (chef-lieu : Casablanca) :
  Préfectures : Casablanca, Mohammedia
  Provinces   : Settat, El Jadida, Sidi Bennour, Berrechid, Benslimane, Nouaceur, Médiouna

Données RÉELLES utilisées (aucune valeur inventée) :
  * Pluie         : CHIRPS v2.0 mensuel 2009-09 -> 2026-09 (UCSB / IRI Data Library), moyenne des pixels de 5 km
                    situés dans les limites de chaque province (geoBoundaries ADM2).
  * Climat & sol  : ERA5-Land / ERA5 via Open-Meteo (température, évapotranspiration ET0, humidité du sol 0-7 cm
                    et 7-28 cm), 2009-09 -> 2026-10. Collecté au centre de 4 zones agricoles ; chaque province
                    reçoit les valeurs de sa zone (colonne `source_era5`). Pour avoir une série par province,
                    lancer data/collecte_provinces.py sur un ordinateur connecté à internet : ce fichier est
                    alors utilisé automatiquement.
  * Rendements    : statistiques officielles du HCP par province (FEWS NET Data Warehouse), campagnes 2010-2023.
                    Berrechid et Sidi Bennour sont publiées séparément à partir de 2012 (avant : incluses dans
                    Settat et El Jadida).
  * Barrage       : relevés officiels du barrage Al Massira (province de Settat) publiés par le ministère de
                    l'Équipement et de l'Eau et repris par la presse (date, taux, volume, lien) — 2019 -> 2026.

Sorties : data/region/*.csv
Usage   : python data/construire_provinces.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.path import Path as MPath
from scipy.io import netcdf_file

sys.stdout.reconfigure(encoding="utf-8")
ICI = Path(__file__).resolve().parent
SRC = ICI / "casaharvest" / "sources"
OUT = ICI / "region"
OUT.mkdir(exist_ok=True)

# nom, type, nom arabe, nom(s) FEWS, nom geoBoundaries, zone ERA5, sol dominant (description qualitative)
PROVINCES = [
    ("Casablanca", "Préfecture", "الدار البيضاء", ["Casablanca"], "Prefecture of Casablanca", "Casablanca (préfectures)",
     "Zone urbaine ; sols rouges (hamri) en périphérie"),
    ("Mohammedia", "Préfecture", "المحمدية", ["Mohammedia"], "Prefecture of Mohammédia", "Casablanca (préfectures)",
     "Zone urbaine et littorale ; sols sableux à limoneux"),
    ("Settat", "Province", "سطات", ["Settat"], "Settat Province", "Settat-Berrechid",
     "Plateau de la Chaouia : tirs (vertisols noirs argileux, forte réserve en eau) et hamri"),
    ("Berrechid", "Province", "برشيد", ["Berrechid"], "Berrechid Province", "Settat-Berrechid",
     "Plaine de Berrechid : tirs et hamri, nappe phréatique exploitée"),
    ("El Jadida", "Province", "الجديدة", ["El Jadida"], "El Jadida Province", "El Jadida-Sidi Bennour",
     "Doukkala : tirs et hamri à l'intérieur, sols sableux (r'mel) près de la côte ; périmètre irrigué"),
    ("Sidi Bennour", "Province", "سيدي بنور", ["Sidi Bennour"], "Province de Sidi Bennour إقليم سيدي بنور",
     "El Jadida-Sidi Bennour", "Doukkala : tirs et hamri ; périmètre irrigué des Doukkala"),
    ("Benslimane", "Province", "بنسليمان", ["Benslimane", "Ben Slimane"], "Province de Benslimane إقليم بن سليمان",
     "Benslimane", "Sols peu profonds sur schistes, forêts de chêne-liège ; sols limono-argileux en plaine"),
    ("Nouaceur", "Province", "النواصر", ["Nouaceur"], "Nouaceur Province", "Casablanca (préfectures)",
     "Sols rouges (hamri) et tirs ; agriculture périurbaine"),
    ("Médiouna", "Province", "مديونة", ["Mediouna"], "Médiouna Province", "Casablanca (préfectures)",
     "Sols rouges (hamri) ; maraîchage périurbain"),
]
NOMS = [p[0] for p in PROVINCES]
CULTURES = {"Wheat Grain": "Blé tendre", "Wheat (Durum)": "Blé dur", "Barley (Unspecified)": "Orge"}

geo = json.load(open(SRC / "geoBoundaries-MAR-ADM2_simplified.geojson", encoding="utf-8"))
polys = {ft["properties"]["shapeName"]: ft["geometry"] for ft in geo["features"]}


def anneaux(geom):
    cs = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [np.array(p[0]) for p in cs]


def surface_km2(geom):
    s = 0.0
    for r in anneaux(geom):
        la0 = np.radians(r[:, 1].mean())
        x = np.radians(r[:, 0]) * 6371 * np.cos(la0)
        y = np.radians(r[:, 1]) * 6371
        s += abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2
    return s


# ======================================================================= 0. PROVINCES + CARTE
info, carte = [], []
for nom, typ, ar, _, gb, zone, sol in PROVINCES:
    g = polys[gb]
    rs = anneaux(g)
    tout = np.vstack(rs)
    info.append(dict(province=nom, type=typ, nom_ar=ar, zone_era5=zone, surface_km2=round(surface_km2(g)),
                     lat=round(float(tout[:, 1].mean()), 3), lon=round(float(tout[:, 0].mean()), 3), sol=sol))
    for r in rs:
        pas = max(1, len(r) // 250)
        carte.append({"province": nom, "anneau": [[round(float(x), 4), round(float(y), 4)] for x, y in r[::pas]]})
pd.DataFrame(info).to_csv(OUT / "provinces.csv", index=False, encoding="utf-8")
(OUT / "carte_region.json").write_text(json.dumps(carte, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("0. provinces :", ", ".join(f"{i['province']} ({i['surface_km2']} km²)" for i in info))

# ======================================================================= 1. PLUIE CHIRPS PAR PROVINCE
nc = netcdf_file(SRC / "chirps_v2_casablanca_settat_2009_2026.nc", "r", mmap=False)
lon, lat = nc.variables["X"][:].astype(float), nc.variables["Y"][:].astype(float)
P = nc.variables["precipitation"][:].astype(float)
mois_t = [(pd.Timestamp("1960-01-01") + pd.DateOffset(months=int(t))).strftime("%Y-%m") for t in nc.variables["T"][:]]
LO, LA = np.meshgrid(lon, lat)
pts = np.column_stack([LO.ravel(), LA.ravel()])
lignes, npix = [], {}
for nom, _, _, _, gb, _, _ in PROVINCES:
    m = np.zeros(len(pts), bool)
    for r in anneaux(polys[gb]):
        m |= MPath(r).contains_points(pts)
    if m.sum() < 3:  # très petite préfecture : on prend les pixels à moins de 5 km du contour
        cx, cy = np.vstack(anneaux(polys[gb])).mean(axis=0)
        m = (np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) < 0.08)
    m = m.reshape(LO.shape)
    npix[nom] = int(m.sum())
    for k, mo in enumerate(mois_t):
        v = P[k][m]
        v = v[(v >= 0) & (v < 2000)]
        lignes.append(dict(province=nom, mois=mo, pluie_mm=round(float(v.mean()), 1) if len(v) else np.nan))
pluie = pd.DataFrame(lignes)
pluie.to_csv(OUT / "pluie_chirps_mensuelle.csv", index=False, encoding="utf-8")
print("1. pluie CHIRPS :", pluie.mois.min(), "->", pluie.mois.max(), "| pixels :", npix)

# ======================================================================= 2. CLIMAT ERA5-LAND
fichier_prov = OUT / "era5_provinces_mensuel.csv"  # produit par data/collecte_provinces.py (si disponible)
if fichier_prov.exists():
    era = pd.read_csv(fichier_prov)
    era["source_era5"] = "ERA5-Land au centre de la province"
    print("2. ERA5-Land : série par province (collecte_provinces.py)")
else:
    z = pd.read_csv(ICI / "casaharvest" / "climat_mensuel_zones.csv", encoding="utf-8-sig")
    z = z.drop(columns=["pluie_mm", "bilan_hydrique_mm"])
    era = pd.DataFrame(info)[["province", "zone_era5"]].merge(z, left_on="zone_era5", right_on="zone").drop(columns=["zone"])
    era["source_era5"] = "ERA5-Land au centre de la zone " + era.zone_era5
    era = era.drop(columns=["zone_era5"])
    print("2. ERA5-Land : valeurs de la zone agricole (4 zones) attribuées à chaque province")
clim = pluie.merge(era, on=["province", "mois"], how="outer").sort_values(["province", "mois"])
clim["bilan_hydrique_mm"] = (clim.pluie_mm - clim.et0_mm).round(1)
clim.to_csv(OUT / "climat_mensuel_provinces.csv", index=False, encoding="utf-8")
print("   climat :", clim.mois.min(), "->", clim.mois.max(), len(clim), "lignes")

# ======================================================================= 3. RENDEMENTS HCP PAR PROVINCE
f = pd.read_csv(SRC / "fews_production_casablanca_settat.csv", low_memory=False)
f["campagne"] = f.season_year.str[-4:].astype(int)
fews2nom = {n: p[0] for p in PROVINCES for n in p[3]}
f = f[f.admin_2.isin(fews2nom) & (f.campagne >= 2010) & f["product"].isin(CULTURES)
      & f.indicator.isin(["Area Planted", "Quantity Produced"]) & (f.status == "Collected") & (f.value > 0)]
f["province"] = f.admin_2.map(fews2nom)
r = (f.pivot_table(index=["province", "campagne", "product"], columns="indicator", values="value", aggfunc="sum")
     .rename(columns={"Area Planted": "superficie_ha", "Quantity Produced": "production_t"}).reset_index()
     .dropna(subset=["superficie_ha", "production_t"]))
r["culture"] = r["product"].map(CULTURES)
r["rendement_qx_ha"] = (r.production_t / r.superficie_ha * 10).round(2)
r["note"] = np.where((r.campagne < 2012) & r.province.isin(["Settat", "El Jadida"]),
                     "inclut Berrechid / Sidi Bennour (avant le découpage de 2012)", "")
r = r[["province", "campagne", "culture", "superficie_ha", "production_t", "rendement_qx_ha", "note"]] \
    .sort_values(["province", "culture", "campagne"])
r.to_csv(OUT / "rendements_provinces_2010_2023.csv", index=False, encoding="utf-8")
c = r.groupby("province").campagne.agg(["min", "max", "nunique"])
print("3. rendements HCP :", len(r), "lignes ;", c.to_dict("index"))

# ======================================================================= 4. TYPE DE SOL
pd.DataFrame(info)[["province", "sol"]].to_csv(OUT / "sols_provinces.csv", index=False, encoding="utf-8")

# ======================================================================= 5. BARRAGE AL MASSIRA (relevés officiels)
CAP = 2649.54  # capacité normale (Mm³), ministère de l'Équipement et de l'Eau
R = [  # date, taux (%), volume (Mm³) si publié, source
    ("2019-03-25", 26.6, None, "https://medias24.com/2020/03/26/barrages-malgre-les-dernieres-pluies-les-taux-de-remplissage-sont-inquietants/"),
    ("2019-09-10", 18.6, 495.1, "https://fr.hespress.com/164571-164571.html"),
    ("2020-03-25", 16.1, None, "https://medias24.com/2020/03/26/barrages-malgre-les-dernieres-pluies-les-taux-de-remplissage-sont-inquietants/"),
    ("2020-07-23", 15.6, 413.0, "https://fnh.ma/article/actualites-marocaines/barrages-le-taux-de-remplissage-en-baisse-a-pres-de-44"),
    ("2020-09-10", 14.5, 386.5, "https://fr.hespress.com/164571-164571.html"),
    ("2020-12-12", 12.2, 324.0, "https://fr.le360.ma/economie/video-ressources-hydriques-le-deuxieme-plus-grand-barrage-du-royaume-al-massira-est-presque-a-sec-251117/"),
    ("2021-08-22", 10.2, None, "https://snrtnews.com/fr/article/barrages-le-taux-de-remplissage-inquiete-51512"),
    ("2021-12-12", 7.8, 206.0, "https://fr.le360.ma/economie/video-ressources-hydriques-le-deuxieme-plus-grand-barrage-du-royaume-al-massira-est-presque-a-sec-251117/"),
    ("2022-03-15", 6.5, None, "https://medias24.com/2022/03/15/stabilisation-du-taux-remplissage-des-barrages-grace-aux-dernieres-pluies/"),
    ("2022-04-06", 7.5, None, "https://medias24.com/2022/04/06/barrages-legere-hausse-du-taux-de-remplissage-a-338/"),
    ("2022-08-07", 5.6, None, "https://fr.le360.ma/economie/deuxieme-plus-important-barrage-au-maroc-al-massira-au-bord-de-lassechement-264907/"),
    ("2022-08-22", 4.8, 127.9, "https://snrtnews.com/fr/article/barrages-le-taux-de-remplissage-inquiete-51512"),
    ("2023-02-20", 5.0, 132.4, "https://medias24.com/2023/03/08/hausse-reserves-des-grands-barrages-du-royaume/"),
    ("2023-03-08", 5.9, 156.8, "https://medias24.com/2023/03/08/hausse-reserves-des-grands-barrages-du-royaume/"),
    ("2023-10-10", None, 82.0, "https://fr.hespress.com/389966-389966.html"),
    ("2024-04-15", 1.87, 49.69, "https://medias24.com/2024/07/19/ok-les-reserves-des-barrages-stationnaires-grace-a-la-baisse-drastique-de-lirrigation/"),
    ("2024-07-19", 1.59, 42.29, "https://medias24.com/2024/07/19/ok-les-reserves-des-barrages-stationnaires-grace-a-la-baisse-drastique-de-lirrigation/"),
    ("2024-10-10", None, 9.7, "https://fr.hespress.com/389966-389966.html"),
    ("2025-03-04", 2.3, None, "https://fr.le360.ma/societe/al-massira-a-33-de-remplissage-le-bassin-de-loum-er-rbia-reprend-des-couleurs_F3QDQPN53NDU3PWOOXATN4MOQA/"),
    ("2025-04-11", 4.29, None, "https://fr.le360.ma/societe/de-38-a-75-comment-les-barrages-ont-double-leurs-reserves-en-un-an_IR3DRDZAJZCNLFG33Q26FVH564/"),
    ("2025-05-15", None, 155.0, "https://fr.le360.ma/economie/barrage-al-massira-un-taux-de-remplissage-de-42-une-premiere-depuis-plus-de-neuf-ans_4VI4AEP6PBE2FEPLIQQR63MOJE/"),
    ("2025-07-24", 3.9, None, "https://fr.le360.ma/societe/de-39-a-413-en-chiffres-voici-comment-le-barrage-al-massira-a-decuple-son-stock-en-un-an_F6EUM2YPIVHKTGD2FFR3KOQSII/"),
    ("2025-11-13", 2.68, None, "https://telquel.ma/instant-t/2026/11/13/barrages-1127-milliards-de-m%C2%B3-en-reserve-mais-des-ecarts-persistants-entre-bassins_2018154"),
    ("2026-01-08", 8.0, None, "https://medias24.com/2026/01/08/barrages-le-taux-de-remplissage-grimpe-a-452-au-8-janvier-2026-data-et-images-satellites-1608529/"),
    ("2026-01-13", 8.5, None, "https://fr.le360.ma/economie/barrage-al-massira-85-de-remplissage-etat-des-lieux-en-images-exclusives_GOO7XJHXUVFLLG42L2IZ2MYMMI/"),
    ("2026-02-02", 15.32, 407.18, "https://medias24.com/2026/02/02/barrages-au-maroc-1025-mmm³-et-612-de-remplissage-1620707/"),
    ("2026-02-10", 18.48, 490.89, "https://medias24.com/2026/02/10/barrages-115-milliards-de-m%C2%B3-retour-aux-niveaux-exceptionnels-de-2015-1625427/"),
    ("2026-03-04", 31.73, None, "https://fr.le360.ma/societe/al-massira-a-33-de-remplissage-le-bassin-de-loum-er-rbia-reprend-des-couleurs_F3QDQPN53NDU3PWOOXATN4MOQA/"),
    ("2026-03-20", 33.12, None, "https://fr.hespress.com/466667-taux-de-remplissage-des-barrages-au-maroc-un-bond-impressionnant-a-plus-de-72-en-ce-premier-jour-de-printemps.html"),
    ("2026-04-03", 34.4, None, "https://snrtnews.com/fr/article/le-taux-de-remplissage-des-barrages-grimpe-a-741-avec-des-reserves-de-127-milliards-de-m3"),
    ("2026-04-11", 36.59, 969.57, "https://fr.le360.ma/societe/de-38-a-75-comment-les-barrages-ont-double-leurs-reserves-en-un-an_IR3DRDZAJZCNLFG33Q26FVH564/"),
    ("2026-05-18", 42.0, 1125.5, "https://le360-le-360-francais-prod.web.arc-cdn.net/economie/barrages-146-milliard-de-m-en-moins-depuis-la-mi-mai-letat-des-stocks-au-1er-septembre_P4AFCOVN5VDYRFS7W7366CBSQY/"),
    ("2026-07-24", 41.3, None, "https://fr.le360.ma/societe/de-39-a-413-en-chiffres-voici-comment-le-barrage-al-massira-a-decuple-son-stock-en-un-an_F6EUM2YPIVHKTGD2FFR3KOQSII/"),
    ("2026-09-01", 40.21, 1065.48, "https://le360-le-360-francais-prod.web.arc-cdn.net/economie/barrages-146-milliard-de-m-en-moins-depuis-la-mi-mai-letat-des-stocks-au-1er-septembre_P4AFCOVN5VDYRFS7W7366CBSQY/"),
    ("2026-11-02", 40.84, None, "https://www.lebrief.ma/barrages-le-taux-de-remplissage-atteint-6578-100172065/"),
    ("2026-11-07", 41.30, None, "https://aujourdhui.ma/societe/les-reserves-globales-ont-plus-que-double-en-une-annee-les-barrages-affichent-un-taux-de-remplissage-de-6584-au-7-novembre-2026"),
    ("2026-11-10", 41.50, None, "https://fr.le360.ma/societe/voici-les-barrages-qui-ont-le-plus-profite-des-dernieres-pluies_VMEAKZVWY5A25FENJD55QJ2WOI/"),
    ("2026-11-13", 41.64, None, "https://telquel.ma/instant-t/2026/11/13/barrages-1127-milliards-de-m%C2%B3-en-reserve-mais-des-ecarts-persistants-entre-bassins_2018154"),
    ("2026-11-15", 41.87, 1110.0, "https://fr.hespress.com/496528-barrages-le-taux-de-remplissage-atteint-6627-au-maroc.html"),
]
b = pd.DataFrame(R, columns=["date", "taux_pct", "volume_Mm3", "source"])
b["volume_Mm3"] = b.volume_Mm3.fillna(b.taux_pct / 100 * CAP).round(1)
b["taux_pct"] = b.taux_pct.fillna(b.volume_Mm3 / CAP * 100).round(2)
b.insert(0, "barrage", "Al Massira")
b.to_csv(OUT / "barrage_al_massira_releves.csv", index=False, encoding="utf-8")
print(f"5. Al Massira : {len(b)} relevés officiels, {b.date.min()} -> {b.date.max()}, dernier {b.taux_pct.iloc[-1]} %")
