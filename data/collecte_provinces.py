"""CasaHarvest Région — à lancer sur VOTRE ordinateur (connexion internet nécessaire, ~20-40 minutes).

Télécharge, pour le centre de chacune des 9 préfectures et provinces de Casablanca-Settat :
  1. ERA5-Land (Open-Meteo, gratuit, sans clé) : températures min / max / moyenne, évapotranspiration ET0,
     humidité du sol 0-7 cm et 7-28 cm, quotidien 2009-09 -> aujourd'hui, agrégé par mois
     -> data/region/era5_provinces_mensuel.csv
  2. NDVI MODIS MOD13Q1 (250 m, 16 jours ; ORNL DAAC, gratuit, sans clé) : moyenne d'un carré de 10 x 10 km
     -> data/region/ndvi_provinces.csv
  3. SoilGrids 2.0 (ISRIC, gratuit, sans clé) : argile, sable, limon, carbone organique, pH, densité, 0-30 cm
     -> data/region/sols_soilgrids.csv

Puis relancer :  python data/construire_provinces.py  &&  python ml/run_region.py
Les modèles utilisent automatiquement ces fichiers s'ils existent.

Usage : python data/collecte_provinces.py            (tout)
        python data/collecte_provinces.py era5 sol    (seulement certaines sources)
Remarque : écrit et vérifié selon la documentation publique des trois services, mais non exécuté dans
l'environnement de développement (pas d'accès internet). En cas d'erreur, le message indique la source.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ICI = Path(__file__).resolve().parent
OUT = ICI / "region"
PROV = pd.read_csv(OUT / "provinces.csv")
QUOI = set(sys.argv[1:]) or {"era5", "ndvi", "sol"}


def get_json(url, essais=4):
    for k in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "CasaHarvest"}), timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            if k == essais - 1:
                raise RuntimeError(f"Échec : {url[:120]}… ({e})")
            time.sleep(5 * (k + 1))


# ---------------------------------------------------------------- 1. ERA5-Land
if "era5" in QUOI:
    fin = (pd.Timestamp.today() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    vars_j = ("temperature_2m_max,temperature_2m_min,temperature_2m_mean,et0_fao_evapotranspiration,"
              "soil_moisture_0_to_7cm_mean,soil_moisture_7_to_28cm_mean")
    lignes = []
    for p in PROV.itertuples():
        url = (f"https://archive-api.open-meteo.com/v1/archive?latitude={p.lat}&longitude={p.lon}"
               f"&start_date=2009-09-01&end_date={fin}&daily={vars_j}&timezone=Africa%2FCasablanca")
        d = pd.DataFrame(get_json(url)["daily"])
        d["time"] = pd.to_datetime(d.time)
        d["mois"] = d.time.dt.strftime("%Y-%m")
        d["chaud"] = (d.temperature_2m_max >= 30).astype(int)
        m = d.groupby("mois").agg(tmax_moy_C=("temperature_2m_max", "mean"), tmin_moy_C=("temperature_2m_min", "mean"),
                                  tmoy_C=("temperature_2m_mean", "mean"), jours_chauds_30C=("chaud", "sum"),
                                  et0_mm=("et0_fao_evapotranspiration", "sum"),
                                  humidite_sol_0_7cm=("soil_moisture_0_to_7cm_mean", "mean"),
                                  humidite_sol_7_28cm=("soil_moisture_7_to_28cm_mean", "mean"),
                                  n=("time", "size")).reset_index()
        m = m[m.n >= 25].drop(columns="n")
        m.insert(0, "province", p.province)
        lignes.append(m.round(3))
        print(f"ERA5-Land {p.province} : {len(m)} mois")
        time.sleep(2)
    pd.concat(lignes).to_csv(OUT / "era5_provinces_mensuel.csv", index=False, encoding="utf-8")

# ---------------------------------------------------------------- 2. NDVI MODIS (ORNL DAAC)
if "ndvi" in QUOI:
    base = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
    lignes = []
    for p in PROV.itertuples():
        dates = [d["modis_date"] for d in get_json(f"{base}/dates?latitude={p.lat}&longitude={p.lon}")["dates"]
                 if d["calendar_date"] >= "2009-09-01"]
        for i in range(0, len(dates), 10):  # 10 dates maximum par requête
            q = urllib.parse.urlencode(dict(latitude=p.lat, longitude=p.lon, band="250m_16_days_NDVI",
                                            startDate=dates[i], endDate=dates[min(i + 9, len(dates) - 1)],
                                            kmAboveBelow=5, kmLeftRight=5))
            r = get_json(f"{base}/subset?{q}")
            ech = float(r.get("scale", 0.0001) or 0.0001)
            for s in r["subset"]:
                v = [x for x in s["data"] if x > -2000]
                if v:
                    lignes.append(dict(province=p.province, date=s["calendar_date"], ndvi=round(sum(v) / len(v) * ech, 4)))
        print(f"NDVI {p.province} : {sum(1 for l in lignes if l['province'] == p.province)} images")
    n = pd.DataFrame(lignes)
    n["mois"] = n.date.str[:7]
    n.groupby(["province", "mois"]).ndvi.mean().round(4).reset_index().to_csv(OUT / "ndvi_provinces.csv", index=False)

# ---------------------------------------------------------------- 3. SoilGrids
if "sol" in QUOI:
    props = ["clay", "sand", "silt", "soc", "phh2o", "bdod"]
    lignes = []
    for p in PROV.itertuples():
        q = "&".join([f"lon={p.lon}", f"lat={p.lat}", *[f"property={x}" for x in props],
                      *[f"depth={d}" for d in ["0-5cm", "5-15cm", "15-30cm"]], "value=mean"])
        r = get_json(f"https://rest.isric.org/soilgrids/v2.0/properties/query?{q}")
        ligne = {"province": p.province}
        for lay in r["properties"]["layers"]:
            f = lay["unit_measure"]["d_factor"]
            vals = [d["values"]["mean"] for d in lay["depths"] if d["values"]["mean"] is not None]
            ligne[lay["name"]] = round(sum(vals) / len(vals) / f, 2) if vals else None
        lignes.append(ligne)
        print("SoilGrids", ligne)
        time.sleep(1)
    pd.DataFrame(lignes).rename(columns={"clay": "argile_pct", "sand": "sable_pct", "silt": "limon_pct",
                                         "soc": "carbone_org_g_kg", "phh2o": "ph", "bdod": "densite_g_cm3"}) \
        .to_csv(OUT / "sols_soilgrids.csv", index=False, encoding="utf-8")
print("Terminé. Relancer : python data/construire_provinces.py && python ml/run_region.py")
