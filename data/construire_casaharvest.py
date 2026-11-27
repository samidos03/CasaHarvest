"""CasaHarvest — données des modules 1 (rendement agricole) et 2 (sécheresse), région Casablanca-Settat, depuis 2010.

Sources :
  - Rendements : FEWS NET Data Warehouse (statistiques officielles du HCP, usage public), par province
  - Pluie : CHIRPS v2.0 mensuel (UCSB, via IRI Data Library), moyenne sur la surface de chaque zone (limites geoBoundaries ADM2)
  - Humidité du sol, évapotranspiration, température : ERA5-Land / ERA5 via Open-Meteo (point central de chaque zone)
  - Production végétale nationale 2010-2022 : data.gov.ma (ministère de l'Agriculture)

Zones (regroupements stables depuis 2010 : Berrechid et Sidi Bennour n'apparaissent séparément qu'à partir de 2012) :
  Settat-Berrechid, El Jadida-Sidi Bennour, Benslimane, Casablanca (préfectures : Casablanca, Mohammédia, Médiouna, Nouaceur)

Usage : python -I construire_casaharvest.py   (sources dans casaharvest/sources/)
Sorties : dossier casaharvest/ (CSV) + CasaHarvest_donnees.xlsx
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.path import Path as MPath
from scipy import stats
from scipy.io import netcdf_file

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(__file__).resolve().parent / "casaharvest"
OUT.mkdir(exist_ok=True)
SRC = OUT / "sources"
FEWS = SRC / "fews_production_casablanca_settat.csv"
GEOJSON = SRC / "geoBoundaries-MAR-ADM2_simplified.geojson"
CHIRPS = SRC / "chirps_v2_casablanca_settat_2009_2026.nc"
PRODVEG = SRC / "production_vegetale_2010_2022.xlsx"
DEBUT = 2010

ZONES = {  # zone -> (noms FEWS admin_2, noms geoBoundaries)
    "Settat-Berrechid": (["Settat", "Berrechid"], ["Settat Province", "Berrechid Province"]),
    "El Jadida-Sidi Bennour": (["El Jadida", "Sidi Bennour"],
                               ["El Jadida Province", "Province de Sidi Bennour إقليم سيدي بنور"]),
    "Benslimane": (["Benslimane", "Ben Slimane"], ["Province de Benslimane إقليم بن سليمان"]),
    "Casablanca (préfectures)": (["Casablanca", "Mediouna", "Mohammedia", "Nouaceur"],
                                 ["Prefecture of Casablanca", "Prefecture of Mohammédia", "Médiouna Province",
                                  "Nouaceur Province"]),
}
REGIONS_FEWS = ["Casablanca-Settat", "Chaouia-Ouardigha", "Doukkala-Abda", "Grand Casablanca"]
CULTURES = {"Wheat Grain": "Blé tendre", "Wheat (Durum)": "Blé dur", "Barley (Unspecified)": "Orge",
            "Maize (Corn)": "Maïs", "Broad Beans": "Fève", "Chick Peas": "Pois chiche", "Lentils": "Lentille",
            "Pea (unspecified)": "Petit pois", "Sugar beet": "Betterave sucrière"}

# ================================================================ 1. RENDEMENTS (module 1)
f = pd.read_csv(FEWS, low_memory=False)
f["campagne"] = f.season_year.str[-4:].astype(int)  # année de récolte : 2010 = campagne 2009/2010
f = f[f.admin_1.isin(REGIONS_FEWS) & (f.campagne >= DEBUT) & f["product"].isin(CULTURES)
      & f.indicator.isin(["Area Planted", "Quantity Produced"]) & (f.status == "Collected")]
# surface emblavée (« Area Planted » : la surface récoltée n'est pas renseignée) ; un 0 signifie « non publié »
f = f[f.value > 0]
prov2zone = {p: z for z, (fews, _) in ZONES.items() for p in fews}
f["zone"] = f.admin_2.map(prov2zone)
f = f[f.zone.notna()]
# une province ne compte que si surface ET production sont publiées (sinon le rendement serait faussé)
complet = f.groupby(["admin_2", "campagne", "product"]).indicator.transform("nunique") == 2
f = f[complet]
agg = (f.pivot_table(index=["zone", "campagne", "product"], columns="indicator", values="value", aggfunc="sum")
       .rename(columns={"Area Planted": "surface_ha", "Quantity Produced": "production_t"}).reset_index())
nprov = f.groupby(["zone", "campagne", "product"]).admin_2.nunique().rename("nb_provinces").reset_index()
agg = agg.merge(nprov, on=["zone", "campagne", "product"])
tot = agg.groupby(["campagne", "product"])[["surface_ha", "production_t"]].sum().reset_index()
tot["zone"], tot["nb_provinces"] = "Région Casablanca-Settat", np.nan
rend = pd.concat([agg, tot], ignore_index=True)
rend["culture"] = rend["product"].map(CULTURES)
rend["rendement_qx_ha"] = (rend.production_t / rend.surface_ha * 10).round(2)
rend.loc[rend.surface_ha <= 0, "rendement_qx_ha"] = np.nan
rend = rend[["zone", "campagne", "culture", "surface_ha", "production_t", "rendement_qx_ha", "nb_provinces"]] \
    .sort_values(["culture", "zone", "campagne"])
rend.to_csv(OUT / "rendements_zones_2010_2023.csv", index=False, encoding="utf-8-sig")
print("1. rendements :", len(rend), "lignes,", rend.campagne.min(), "->", rend.campagne.max())

# ================================================================ 2. CLIMAT
geo = json.load(open(GEOJSON, encoding="utf-8"))
polys = {ft["properties"]["shapeName"]: ft["geometry"] for ft in geo["features"]}


def anneaux(geom):
    cs = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [np.array(p[0]) for p in cs]


# CHIRPS v2.0 mensuel, découpé sur la région (IRI Data Library, Columbia University) :
# https://iridl.ldeo.columbia.edu/SOURCES/.UCSB/.CHIRPS/.v2p0/.monthly/.global/.precipitation/
#   X/(-9.4)(-6.6)RANGEEDGES/Y/(32.0)(34.0)RANGEEDGES/T/(Sep 2009)(Oct 2026)RANGEEDGES/data.nc
nc = netcdf_file(CHIRPS, "r", mmap=False)
lon, lat = nc.variables["X"][:].astype(float), nc.variables["Y"][:].astype(float)
P = nc.variables["precipitation"][:].astype(float)            # (temps, lat, lon), mm/mois
mois_t = [(pd.Timestamp("1960-01-01") + pd.DateOffset(months=int(t))).strftime("%Y-%m")
          for t in nc.variables["T"][:]]
LO, LA = np.meshgrid(lon, lat)
pts = np.column_stack([LO.ravel(), LA.ravel()])
masques, centres = {}, {}
for z, (_, gb) in ZONES.items():
    m = np.zeros(len(pts), bool)
    for n in gb:
        for r in anneaux(polys[n]):
            m |= MPath(r).contains_points(pts)
    masques[z] = m.reshape(LO.shape)
    centres[z] = (float(LA[masques[z]].mean()), float(LO[masques[z]].mean()))
    print(f"   {z}: {int(m.sum())} pixels CHIRPS, centre {centres[z][0]:.2f}N {centres[z][1]:.2f}E")
lignes = []
for k, mo in enumerate(mois_t):
    for z, m in masques.items():
        v = P[k][m]
        v = v[(v >= 0) & (v < 2000)]
        lignes.append({"zone": z, "mois": mo, "pluie_mm": round(float(v.mean()), 1)})
pluie = pd.DataFrame(lignes)

# Open-Meteo (ERA5-Land / ERA5) : quotidien au centre de chaque zone, agrégé par mois
vars_j = "precipitation_sum,temperature_2m_max,temperature_2m_mean,et0_fao_evapotranspiration," \
         "soil_moisture_0_to_7cm_mean,soil_moisture_7_to_28cm_mean"
la = ",".join(f"{c[0]:.3f}" for c in centres.values())
lo = ",".join(f"{c[1]:.3f}" for c in centres.values())
url = (f"https://archive-api.open-meteo.com/v1/archive?latitude={la}&longitude={lo}&start_date=2009-09-01"
       f"&end_date={pd.Timestamp.today() - pd.Timedelta(days=7):%Y-%m-%d}&daily={vars_j}&timezone=Africa%2FCasablanca")
rep = json.loads(subprocess.run(["curl", "-sL", "-m", "600", url], capture_output=True).stdout)
rep = rep if isinstance(rep, list) else [rep]
jour = []
for z, r in zip(ZONES, rep):
    d = pd.DataFrame(r["daily"])
    d["zone"] = z
    jour.append(d)
jour = pd.concat(jour)
jour["time"] = pd.to_datetime(jour.time)
jour["mois"] = jour.time.dt.strftime("%Y-%m")
jour["jour_chaud"] = (jour.temperature_2m_max >= 30).astype(int)
mens = jour.groupby(["zone", "mois"]).agg(
    tmax_moy_C=("temperature_2m_max", "mean"), tmoy_C=("temperature_2m_mean", "mean"),
    jours_chauds_30C=("jour_chaud", "sum"), et0_mm=("et0_fao_evapotranspiration", "sum"),
    humidite_sol_0_7cm=("soil_moisture_0_to_7cm_mean", "mean"),
    humidite_sol_7_28cm=("soil_moisture_7_to_28cm_mean", "mean"),
    nb_jours=("time", "size")).reset_index()
clim = pluie.merge(mens, on=["zone", "mois"], how="outer").sort_values(["zone", "mois"])
clim = clim[clim.nb_jours.fillna(28) >= 25].drop(columns="nb_jours")  # mois incomplets (le mois en cours)
clim["bilan_hydrique_mm"] = (clim.pluie_mm - clim.et0_mm).round(1)
for c in ["tmax_moy_C", "tmoy_C", "et0_mm"]:
    clim[c] = clim[c].round(1)
for c in ["humidite_sol_0_7cm", "humidite_sol_7_28cm"]:
    clim[c] = clim[c].round(3)
print("2. climat :", len(clim), "lignes,", clim.mois.min(), "->", clim.mois.max())


# ================================================================ 3. SÉCHERESSE (module 2)
def spi(serie, k):
    """SPI-k (McKee et al., 1993) : cumul de pluie sur k mois, loi gamma ajustée par mois calendaire."""
    cum = serie.rolling(k).sum()
    out = pd.Series(np.nan, index=serie.index)
    mois = pd.PeriodIndex(serie.index, freq="M").month
    for m in range(1, 13):
        x = cum[(mois == m) & cum.notna()]
        if len(x) < 8:
            continue
        q0 = (x <= 0).mean()
        pos = x[x > 0]
        a, _, b = stats.gamma.fit(pos, floc=0)
        p = q0 + (1 - q0) * stats.gamma.cdf(x.clip(lower=0), a, scale=b)
        out[x.index] = stats.norm.ppf(np.clip(p, 1e-6, 1 - 1e-6))
    return out


def classe(v):
    if pd.isna(v):
        return None
    return ("sécheresse extrême" if v <= -2 else "sécheresse sévère" if v <= -1.5 else
            "sécheresse modérée" if v <= -1 else "normal" if v < 1 else "humide")


sech = []
for z, g in clim.groupby("zone"):
    g = g.set_index("mois").sort_index()
    d = pd.DataFrame(index=g.index)
    d["zone"] = z
    d["pluie_mm"] = g.pluie_mm
    for k in (1, 3, 6, 12):
        d[f"spi_{k}"] = spi(g.pluie_mm, k).round(2)
    m = pd.PeriodIndex(g.index, freq="M").month
    hs = g.humidite_sol_7_28cm
    d["anomalie_humidite_sol"] = ((hs - hs.groupby(m).transform("mean")) / hs.groupby(m).transform("std")).round(2)
    d["classe_secheresse_spi3"] = d.spi_3.map(classe)
    sech.append(d.reset_index())
sech = pd.concat(sech, ignore_index=True)
sech["mois_dt"] = pd.to_datetime(sech.mois)
sech = sech[sech.mois_dt >= f"{DEBUT}-01-01"].drop(columns="mois_dt")
sech.to_csv(OUT / "secheresse_mensuelle_zones.csv", index=False, encoding="utf-8-sig")
clim = clim[pd.to_datetime(clim.mois) >= "2009-09-01"]
clim.to_csv(OUT / "climat_mensuel_zones.csv", index=False, encoding="utf-8-sig")
print("3. sécheresse :", len(sech), "lignes ; mois en sécheresse (SPI-3 <= -1) :",
      int((sech.spi_3 <= -1).sum()))

# ================================================================ 4. TABLE ML : zone × campagne × culture
c = clim.copy()
d = pd.to_datetime(c.mois)
c["campagne"] = np.where(d.dt.month >= 9, d.dt.year + 1, d.dt.year)  # septembre Y-1 -> août Y
c["m"] = d.dt.month
periodes = {"automne": [9, 10, 11, 12], "hiver": [1, 2, 3], "printemps": [4, 5]}
feat = []
for (z, camp), g in c.groupby(["zone", "campagne"]):
    if not set(range(1, 6)).issubset(g.m) or not {9, 10, 11, 12}.issubset(g.m):
        continue  # campagne incomplète (septembre -> mai nécessaires)
    r = {"zone": z, "campagne": camp}
    for p, ms in periodes.items():
        gp = g[g.m.isin(ms)]
        r[f"pluie_{p}_mm"] = round(gp.pluie_mm.sum(), 1)
    gc = g[g.m.isin([9, 10, 11, 12, 1, 2, 3, 4, 5])]
    r["pluie_campagne_mm"] = round(gc.pluie_mm.sum(), 1)
    r["bilan_hydrique_campagne_mm"] = round(gc.bilan_hydrique_mm.sum(), 1)
    r["humidite_sol_hiver"] = round(g[g.m.isin([1, 2, 3])].humidite_sol_7_28cm.mean(), 3)
    r["humidite_sol_printemps"] = round(g[g.m.isin([3, 4])].humidite_sol_7_28cm.mean(), 3)
    r["tmax_printemps_C"] = round(g[g.m.isin([3, 4, 5])].tmax_moy_C.mean(), 1)
    r["jours_chauds_printemps"] = int(g[g.m.isin([3, 4, 5])].jours_chauds_30C.sum())
    s = sech[(sech.zone == z) & (sech.mois == f"{camp}-03")]
    r["spi_6_mars"] = float(s.spi_6.iloc[0]) if len(s) else np.nan
    feat.append(r)
feat = pd.DataFrame(feat)
reg = feat.groupby("campagne").mean(numeric_only=True).round(3).reset_index()
reg["zone"] = "Région Casablanca-Settat"
feat = pd.concat([feat, reg], ignore_index=True)
ml = rend.merge(feat, on=["zone", "campagne"], how="left")
ml = ml[ml.rendement_qx_ha.notna()].sort_values(["culture", "zone", "campagne"])
ml.to_csv(OUT / "table_ml_rendement_climat.csv", index=False, encoding="utf-8-sig")
feat.to_csv(OUT / "climat_par_campagne_zones.csv", index=False, encoding="utf-8-sig")
print("4. table ML :", ml.shape, "| campagnes climat :", feat.campagne.min(), "->", feat.campagne.max())

# ================================================================ 5. PRODUCTION VÉGÉTALE NATIONALE (data.gov.ma)
pv = pd.read_excel(PRODVEG)
pv.columns = ["campagne_txt", "filiere", "produit", "indicateur", "valeur"]
pv["campagne"] = pv.campagne_txt.str[-4:].astype(int)
pv = pv.pivot_table(index=["campagne", "filiere", "produit"], columns="indicateur", values="valeur").reset_index()
pv.columns.name = None
pv = pv.rename(columns={c: ("production_t" if "Production" in c else "surface_ha" if "Superficie" in c else c)
                        for c in pv.columns})
if {"production_t", "surface_ha"} <= set(pv.columns):
    pv["rendement_t_ha"] = (pv.production_t / pv.surface_ha).round(2)
pv.to_csv(OUT / "production_vegetale_nationale_2010_2022.csv", index=False, encoding="utf-8-sig")
print("5. production nationale :", pv.shape, "| filières :", pv.filiere.nunique(), "| produits :", pv.produit.nunique())

# ================================================================ 6. EXCEL
cov = rend[rend.zone != "Région Casablanca-Settat"].pivot_table(index="culture", columns="zone", values="campagne",
                                                                aggfunc="count")
notes = [
    "CasaHarvest — données des modules 1 (rendement agricole) et 2 (risque de sécheresse), région Casablanca-Settat, depuis 2010.",
    "Zones : Settat-Berrechid, El Jadida-Sidi Bennour, Benslimane, Casablanca (préfectures). Regroupements nécessaires car "
    "Berrechid et Sidi Bennour ne sont publiées séparément qu'à partir de 2012. Région = somme des 4 zones.",
    "Rendements : FEWS NET Data Warehouse, statistiques officielles du HCP (usage public). campagne = année de récolte "
    "(2010 = campagne 2009/2010). rendement_qx_ha = production / surface récoltée.",
    "Pluie : CHIRPS v2.0 (UCSB, via IRI Data Library), moyenne mensuelle sur toute la surface de la zone (limites geoBoundaries).",
    "Humidité du sol (m³/m³, 0-7 cm et 7-28 cm), évapotranspiration ET0, températures : ERA5-Land / ERA5 via Open-Meteo, "
    "au centre de la zone. bilan_hydrique = pluie - ET0.",
    "Sécheresse : SPI-1/3/6/12 (indice de précipitations standardisé, loi gamma par mois calendaire). SPI <= -1 : "
    "sécheresse modérée, <= -1,5 sévère, <= -2 extrême. Calibré sur 2009-2026 (17 ans) : une période de référence de 30 ans "
    "serait préférable. anomalie_humidite_sol = écart à la moyenne du mois / écart-type (7-28 cm).",
    "Table_ML_rendement : une ligne par zone × campagne × culture, rendement + variables climatiques de la campagne "
    "(pluie d'automne, d'hiver, de printemps, humidité du sol, chaleur au printemps, SPI-6 en mars).",
    "Production_nationale : production végétale par produit, Maroc, 2010-2022 (data.gov.ma) — complément national.",
]
with pd.ExcelWriter(Path(__file__).resolve().parent / "CasaHarvest_donnees.xlsx") as x:
    pd.DataFrame({"Note": notes}).to_excel(x, sheet_name="Lisez-moi", index=False)
    cov.to_excel(x, sheet_name="Couverture_rendements")
    ml.to_excel(x, sheet_name="Table_ML_rendement", index=False)
    rend.to_excel(x, sheet_name="Rendements", index=False)
    sech.to_excel(x, sheet_name="Secheresse_mensuelle", index=False)
    clim.to_excel(x, sheet_name="Climat_mensuel", index=False)
    pv.to_excel(x, sheet_name="Production_nationale", index=False)
print("Excel écrit : CasaHarvest_donnees.xlsx")
print(cov.to_string())
