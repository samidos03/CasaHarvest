"""CasaHarvest — API (FastAPI) des 3 modules, utilisée par le frontend React.

  /api/resume                      chiffres clés de l'accueil
  /api/prix/...                    module 3 : prix de gros hebdomadaires (XGBoost), Casablanca
  /api/rendement/...               module 1 : rendement des céréales (modèle hybride XGBoost + garde-fou Ridge)
  /api/secheresse/...              module 2 : risque de sécheresse (SPI-3, Ridge)
  /api/region/...                  région Casablanca-Settat (9 préfectures et provinces) : espace citoyen,
                                   pluie CHIRPS, humidité du sol ERA5-Land, récoltes, barrage Al Massira
  /api/tourisme/...                module 4 : nuitées par destination (gradient boosting quantile, 1-12 mois)
  /api/dechets/...                 module 5 : déchets par quartier (K-means + XGBoost) et tournées de collecte
  /api/air/...                     module 6 : PM10 / NO2 par station (XGBoost quantile J+1 à J+3, calibration conforme)

Lancer (depuis app/backend) :  python -m uvicorn main:app --port 8000
Si le frontend est compilé (app/frontend/dist), il est servi à la racine : http://localhost:8000
"""
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

PROJET = Path(__file__).resolve().parents[2]
DATA, ML, RES = PROJET / "data", PROJET / "ml", PROJET / "ml" / "resultats"
sys.path[:0] = [str(ML), str(DATA)]
from modele_prevision import Prevision  # noqa: E402
import rendement as R  # noqa: E402

H_MAX, Z80 = 8, 1.2816
FAMILLE = {"Viande bovine": "Viandes", "Viande ovine": "Viandes", "Orange": "Fruits", "Clémentine": "Fruits",
           "Banane locale": "Fruits", "Banane importée": "Fruits", "Pomme locale": "Fruits",
           "Pomme importée": "Fruits", "Avocat": "Fruits"}
OFFICIEL_2026 = {"production_Mqx": 25.8, "surface_ha": 852555,
                 "source": "Direction régionale de l'agriculture Casablanca-Settat (presse, juin 2026)"}

app = FastAPI(title="CasaHarvest API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def propre(x):
    """Convertit en JSON valide (NaN -> None, numpy -> types Python, dates -> texte)."""
    if isinstance(x, dict):
        return {k: propre(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [propre(v) for v in x]
    if isinstance(x, (pd.Timestamp,)):
        return x.strftime("%Y-%m-%d")
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return None if math.isnan(x) else round(float(x), 3)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def lignes(df):
    return propre(df.to_dict(orient="records"))


def lire(nom, **kw):
    f = RES / nom
    if not f.exists():
        raise HTTPException(503, f"Résultat manquant : {nom}. Lancer ml/run_all.py et ml/run_casaharvest.py.")
    return pd.read_csv(f, **kw)


# ======================================================================== MODULE 3 : PRIX
@lru_cache
def prix_donnees():
    return Prevision(avec_gb=False)


@lru_cache
def prix_xgb():
    import xgb_hebdo
    return xgb_hebdo.prevoir_tous()


@lru_cache
def sigma_xgb():
    b = lire("xgb_hebdo_backtest.csv")
    b = b[b.methode == "XGBoost"]
    s = np.log(b.prevision / b.reel).groupby(b.horizon).std().reindex(range(1, H_MAX + 1)).ffill().values
    return np.maximum.accumulate(s)


def erreur_attendue(produit, h):
    b = lire("xgb_hebdo_backtest.csv")
    b = b[b.methode == "XGBoost"]
    s = b[(b.produit == produit) & (b.horizon == h)].erreur_pct
    if len(s) < 3:
        s = b[b.horizon == h].erreur_pct
    return float(s.mean()) if len(s) else None


def prevision_prix(produit, h):
    P = prix_donnees()
    if produit not in prix_xgb():
        raise HTTPException(404, f"Produit inconnu : {produit}")
    _, hist, obs, last = P.prevoir(produit, h)
    s, _ = prix_xgb()[produit]
    v, sig = s.values[:h], sigma_xgb()[:h]
    prev = pd.DataFrame({"semaine": s.index[:h], "prevision": v, "bas": v * np.exp(-Z80 * sig),
                         "haut": v * np.exp(Z80 * sig)})
    return prev, hist, obs, last


@app.get("/api/prix/produits")
def prix_produits():
    P = prix_donnees()
    out = []
    for p in sorted(prix_xgb()):
        r = P.w[p].where(P.observe[p]).dropna()
        out.append({"produit": p, "famille": FAMILLE.get(p, "Légumes"), "dernier_prix": r.iloc[-1],
                    "date": r.index[-1]})
    return propre(sorted(out, key=lambda d: (d["famille"], d["produit"])))


@app.get("/api/prix/prevision/{produit}")
def prix_prevision(produit: str, h: int = Query(8, ge=1, le=H_MAX)):
    prev, hist, obs, last = prevision_prix(produit, h)
    hdf = pd.DataFrame({"date": hist.index, "prix": hist.values,
                        "releve": obs.reindex(hist.index).fillna(False).astype(bool).values})
    hdf = hdf[hdf.date >= last - pd.Timedelta(weeks=52)]
    return propre({"produit": produit, "famille": FAMILLE.get(produit, "Légumes"), "horizon": h,
                   "dernier_prix": hist.loc[last], "date_dernier_releve": last,
                   "erreur_attendue_pct": erreur_attendue(produit, h),
                   "historique": lignes(hdf), "prevision": lignes(prev)})


@app.get("/api/prix/marche")
def prix_marche(h: int = Query(8, ge=1, le=H_MAX)):
    out = []
    for p in sorted(prix_xgb()):
        prev, hist, obs, last = prevision_prix(p, h)
        p0, p1 = float(hist.loc[last]), float(prev.prevision.iloc[-1])
        evo = hist[hist.index >= last - pd.Timedelta(weeks=26)]
        out.append({"produit": p, "famille": FAMILLE.get(p, "Légumes"), "dernier_prix": p0, "date": last,
                    "prevision": p1, "variation_pct": (p1 / p0 - 1) * 100, "erreur_pct": erreur_attendue(p, h),
                    "evolution": [{"date": d, "prix": x} for d, x in evo.items()]})
    return propre(out)


@app.get("/api/prix/evaluation")
def prix_evaluation():
    t = lire("xgb_hebdo_erreur_horizon.csv")
    imp = lire("xgb_hebdo_importance.csv")
    imp.columns = ["variable", "importance"]
    b = lire("xgb_hebdo_backtest.csv")
    ep = b.groupby("produit").erreur_pct.mean().sort_values().reset_index()
    return {"par_horizon": lignes(t), "importance": lignes(imp.head(12)), "par_produit": lignes(ep)}


# ======================================================================== MODULE 1 : RENDEMENT
@lru_cache
def rend_donnees():
    ml, clim = R.charger()
    rend = pd.read_csv(DATA / "casaharvest" / "rendements_zones_2010_2023.csv")
    return ml, clim, rend


@app.get("/api/rendement/options")
def rendement_options():
    ml, clim, _ = rend_donnees()
    return propre({"zones": sorted(ml.zone.unique()) + ["Région Casablanca-Settat"], "cultures": R.CULTURES,
                   "plages": {v: {"min": ml[v].min(), "max": ml[v].max(), "mediane": ml[v].median()}
                              for v in R.VARS["mai"]}})


@app.get("/api/rendement/serie")
def rendement_serie(zone: str, culture: str):
    _, _, rend = rend_donnees()
    hist = rend[(rend.zone == zone) & (rend.culture == culture)][["campagne", "rendement_qx_ha", "surface_ha",
                                                                  "production_t"]]
    fut = lire("m1_previsions_2024_2026.csv")
    fut = fut[fut.culture == culture]
    if zone == "Région Casablanca-Settat":
        f = (fut.assign(p=fut.prevision_qx_ha * fut.surface_ref_ha).groupby(["campagne", "modele"])
             .agg(p=("p", "sum"), s=("surface_ref_ha", "sum")).reset_index())
        f["prevision_qx_ha"] = f.p / f.s
        f["extrapolation"] = False
    else:
        f = fut[fut.zone == zone]
    f = f[f.modele.isin([R.HYBRIDE, "XGBoost"])][["campagne", "modele", "prevision_qx_ha", "extrapolation"]]
    cv = lire("m1_validation_croisee.csv")
    cv = cv[(cv.moment == "mai") & (cv.modele == R.HYBRIDE) & (cv.culture == culture)]
    if zone != "Région Casablanca-Settat":
        cv = cv[cv.zone == zone]
    cvz = (cv.assign(p=cv.prevision * cv.surface_ha).groupby("campagne").agg(p=("p", "sum"), s=("surface_ha", "sum"))
           .assign(prevision_cv=lambda d: d.p / d.s).reset_index()[["campagne", "prevision_cv"]])
    return {"historique": lignes(hist.merge(cvz, on="campagne", how="left")), "previsions": lignes(f)}


@app.get("/api/rendement/region")
def rendement_region():
    t = lire("m1_previsions_region_2024_2026.csv", header=[0, 1], index_col=0)
    out = []
    for camp in t.index:
        for mod in [R.HYBRIDE, "XGBoost", "Ridge"]:
            out.append({"campagne": int(camp), "modele": mod,
                        "rendement_qx_ha": t.loc[camp, ("rendement_moyen_qx_ha", mod)],
                        "production_Mqx": t.loc[camp, ("production_Mqx", mod)]})
    off = dict(OFFICIEL_2026, rendement_qx_ha=OFFICIEL_2026["production_Mqx"] * 1e6 / OFFICIEL_2026["surface_ha"])
    return propre({"previsions": out, "officiel_2026": off})


@app.get("/api/rendement/simuler")
def rendement_simuler(spi6: float, humidite_sol: float, jours_chauds: float, culture: str = "Blé tendre",
                      zone: str = "Settat-Berrechid"):
    """Simulateur : rendement prévu (modèle hybride) pour un climat choisi par l'utilisateur."""
    ml, _, _ = rend_donnees()
    zones = sorted(ml.zone.unique()) if zone == "Région Casablanca-Settat" else [zone]
    X = pd.DataFrame({"spi_6_mars": spi6, "humidite_sol_printemps": humidite_sol,
                      "jours_chauds_printemps": jours_chauds, "culture": culture, "zone": zones})
    pr, hors = R.predire(ml[R.VARS["mai"] + R.CATS], ml.rendement_qx_ha, X[R.VARS["mai"] + R.CATS], "mai")
    return propre({"rendement_qx_ha": float(np.mean(pr[R.HYBRIDE])), "ridge": float(np.mean(pr["Ridge"])),
                   "xgboost": float(np.mean(pr["XGBoost"])), "extrapolation": bool(hors.any())})


@app.get("/api/rendement/evaluation")
def rendement_evaluation():
    ml, _, _ = rend_donnees()
    m = lire("m1_metriques.csv")
    mr = lire("m1_metriques_region.csv")
    pts = ml[["campagne", "zone", "culture", "spi_6_mars", "rendement_qx_ha"]]
    return {"metriques": lignes(m), "metriques_region": lignes(mr), "nuage_spi": lignes(pts)}


# ======================================================================== MODULE 2 : SÉCHERESSE
@app.get("/api/secheresse/etat")
def secheresse_etat():
    return {"etat": lignes(lire("m2_etat_actuel.csv")), "prevision": lignes(lire("m2_prevision_3_mois.csv"))}


@app.get("/api/secheresse/serie")
def secheresse_serie(zone: str):
    s = pd.read_csv(DATA / "casaharvest" / "secheresse_mensuelle_zones.csv")
    s = s[s.zone == zone][["mois", "pluie_mm", "spi_3", "spi_6", "spi_12", "anomalie_humidite_sol"]]
    if s.empty:
        raise HTTPException(404, f"Zone inconnue : {zone}")
    return lignes(s)


@app.get("/api/secheresse/evaluation")
def secheresse_evaluation():
    return lignes(lire("m2_metriques.csv"))


# ======================================================================== MODULE 4 : TOURISME
VILLE = DATA / "ville"


@lru_cache
def tour_donnees():
    return pd.read_csv(VILLE / "tourisme_mensuel.csv")


@app.get("/api/tourisme/destinations")
def tourisme_destinations():
    t = tour_donnees()
    v = lire("v4_vulnerabilite.csv")
    p = lire("v4_prevision_12_mois.csv")
    out = []
    for r in v.itertuples():
        pp = p[p.destination == r.destination]
        out.append(dict(r._asdict(), prochain_mois=pp.mois.iloc[0], prochain_mois_nuitees=pp.prevision.iloc[0],
                        lits=int(t[t.destination == r.destination].capacite_lits.iloc[-1])))
    for o in out:
        o.pop("Index", None)
    return propre(out)


@app.get("/api/tourisme/serie")
def tourisme_serie(destination: str):
    t = tour_donnees()
    s = t[t.destination == destination]
    if s.empty:
        raise HTTPException(404, f"Destination inconnue : {destination}")
    lits = int(s.capacite_lits.iloc[-1])
    hist = s[["mois", "nuitees", "evenement", "jours_ramadan"]].copy()
    hist["occupation_pct"] = s.nuitees / (lits * pd.to_datetime(s.mois).dt.days_in_month) * 100
    p = lire("v4_prevision_12_mois.csv")
    p = p[p.destination == destination].copy()
    p["mois"] = p.mois.str[:7]
    j = pd.to_datetime(p.mois).dt.days_in_month
    p["occupation_pct"], p["occupation_haut_pct"] = p.prevision / (lits * j) * 100, p.haut / (lits * j) * 100
    marches = [c for c in s.columns if c.startswith("nuitees_")]
    m = s.tail(12)[marches].sum()
    saison = s[s.mois >= "2023-01"].assign(mm=lambda d: d.mois.str[5:7]).groupby("mm").nuitees.mean()
    return propre({"historique": lignes(hist), "prevision": lignes(p), "lits": lits,
                   "marches": [{"marche": k.replace("nuitees_", ""), "nuitees": v} for k, v in m.sort_values(ascending=False).items()],
                   "saisonnalite": [{"mois": k, "indice": v / saison.mean() * 100} for k, v in saison.items()]})


@app.get("/api/tourisme/evaluation")
def tourisme_evaluation():
    return {"metriques": lignes(lire("v4_metriques.csv")), "par_horizon": lignes(lire("v4_erreur_horizon.csv")),
            "calibration": lignes(lire("v4_calibration.csv"))[0]}


# ======================================================================== MODULE 5 : DÉCHETS
@lru_cache
def dech_donnees():
    return pd.read_csv(VILLE / "dechets_quartiers.csv"), pd.read_csv(VILLE / "dechets_hebdo.csv")


@app.get("/api/dechets/quartiers")
def dechets_quartiers(ville: str = "Marrakech"):
    q, d = dech_donnees()
    prof = lire("v5_profils_quartiers.csv")
    prev = lire("v5_prevision_8_semaines.csv")
    q = q[q.ville == ville].merge(prof, on=["ville", "quartier"])
    if q.empty:
        raise HTTPException(404, f"Ville inconnue : {ville}")
    p1 = prev[(prev.ville == ville) & (prev.h == 1)].set_index("quartier")
    q["prevision_semaine"] = q.quartier.map(p1.prevision)
    q["bas"], q["haut"] = q.quartier.map(p1.bas), q.quartier.map(p1.haut)
    return lignes(q.sort_values("tonnes_jour", ascending=False))


@app.get("/api/dechets/serie")
def dechets_serie(ville: str, quartier: str = None):
    _, d = dech_donnees()
    prev = lire("v5_prevision_8_semaines.csv")
    d, prev = d[d.ville == ville], prev[prev.ville == ville]
    if quartier:
        d, prev = d[d.quartier == quartier], prev[prev.quartier == quartier]
    agg = {"tonnes": "sum", "ramadan": "max", "aid_al_adha": "max", "nuitees_quartier": "sum"}
    h = d[d.semaine >= "2024-06-01"].groupby("semaine").agg(agg).reset_index()
    p = prev.groupby("semaine")[["prevision", "bas", "haut"]].sum().reset_index()
    return {"historique": lignes(h), "prevision": lignes(p)}


@app.get("/api/dechets/tournees")
def dechets_tournees(ville: str = "Marrakech", scenario: str = "semaine"):
    f = RES / "v5_tournees.json"
    if not f.exists():
        raise HTTPException(503, "Résultat manquant : v5_tournees.json. Lancer ml/run_ville.py.")
    t = json.loads(f.read_text(encoding="utf-8"))
    if scenario not in t or ville not in t[scenario]:
        raise HTTPException(404, "Scénario ou ville inconnus")
    r = t[scenario][ville]
    r["comparaison"] = [{"scenario": s, "tonnes_jour": t[s][ville]["tonnes_jour"], "camions": t[s][ville]["camions"],
                         "km": t[s][ville]["km"]} for s in t]
    return propre(r)


@app.get("/api/dechets/evaluation")
def dechets_evaluation():
    exc = lire("v5_metriques_semaines_exceptionnelles.csv", index_col=0).valeur.to_dict()
    imp = lire("v5_importance.csv")
    prof = lire("v5_profils_quartiers.csv")
    typ = prof.groupby("typologie").agg(n=("quartier", "count"), kg_hab_j=("kg_hab_j", "mean"),
                                         part_touristique=("part_touristique", "mean"), effet_ete=("effet_ete", "mean"),
                                         effet_ramadan=("effet_ramadan", "mean"), effet_aid=("effet_aid", "mean"),
                                         quartiers=("quartier", lambda s: ", ".join(s))).reset_index()
    return {"metriques": lignes(lire("v5_metriques.csv")), "exceptionnelles": propre(exc),
            "importance": lignes(imp.head(10)), "typologies": lignes(typ)}


# ======================================================================== MODULE 6 : AIR
@lru_cache
def air_donnees():
    return pd.read_csv(VILLE / "air_journalier.csv"), pd.read_csv(VILLE / "air_stations.csv")


@app.get("/api/air/stations")
def air_stations():
    _, st = air_donnees()
    p = lire("v6_prevision_3_jours.csv")
    ev = lire("v6_evaluation_stations.csv")
    out = []
    for r in st.itertuples():
        g = p[p.station == r.station]
        e = ev[ev.station == r.station].set_index("polluant")
        out.append(dict(station=r.station, ville=r.ville, type=r.type, lat=r.lat, lon=r.lon,
                        disponibilite_pct=(1 - r.taux_manquant) * 100,
                        prevision={pol: lignes(g[g.polluant == pol][["date", "h", "bas", "prevision", "haut", "classe",
                                                                      "sans_mesure_recente", "episode_poussiere"]])
                                   for pol in ["pm10", "no2"]},
                        evaluation={pol: propre(e.loc[pol].to_dict()) if pol in e.index else None for pol in ["pm10", "no2"]}))
    return propre(out)


@app.get("/api/air/serie")
def air_serie(station: str, polluant: str = "pm10", jours: int = Query(120, ge=14, le=1500)):
    d, _ = air_donnees()
    if polluant not in ("pm10", "no2"):
        raise HTTPException(404, "Polluant inconnu")
    s = d[d.station == station]
    if s.empty:
        raise HTTPException(404, f"Station inconnue : {station}")
    s = s[s[polluant].notna()].tail(jours)[["date", polluant, "vent_m_s", "pluie_mm", "episode_poussiere"]]
    p = lire("v6_prevision_3_jours.csv")
    p = p[(p.station == station) & (p.polluant == polluant)][["date", "bas", "prevision", "haut"]]
    return {"historique": lignes(s.rename(columns={polluant: "valeur"})), "prevision": lignes(p)}


@app.get("/api/air/evaluation")
def air_evaluation():
    ev = lire("v6_evaluation_stations.csv")
    imp = lire("v6_importance_pm10.csv")
    return {"stations": lignes(ev), "importance_pm10": lignes(imp.head(10))}


# ======================================================================== RÉGION CASABLANCA-SETTAT
REGION = DATA / "region"
PROV_ORDRE = ["Casablanca", "Mohammedia", "Settat", "Berrechid", "El Jadida", "Sidi Bennour", "Benslimane",
              "Nouaceur", "Médiouna"]


def jlire(nom):
    f = RES / nom
    if not f.exists():
        raise HTTPException(503, f"Résultat manquant : {nom}. Lancer ml/run_region.py.")
    return json.loads(f.read_text(encoding="utf-8"))


@lru_cache
def reg_climat():
    c = pd.read_csv(REGION / "climat_mensuel_provinces.csv")
    return c


def _verif_province(province):
    if province not in PROV_ORDRE:
        raise HTTPException(404, f"Province inconnue : {province}")


@app.get("/api/region/carte")
def region_carte():
    return json.loads((REGION / "carte_region.json").read_text(encoding="utf-8"))


@app.get("/api/region/provinces")
def region_provinces():
    """Tableau de bord des 9 préfectures et provinces (sert à la carte et à l'accueil)."""
    info = pd.read_csv(REGION / "provinces.csv").set_index("province")
    sa = lire("r_pluie_saisons.csv")
    sa26 = sa[sa.saison == 2026].set_index("province")
    sol = lire("r_sol_etat.csv").set_index("province")
    rp = lire("r_recolte_previsions.csv")
    r26 = rp[rp.campagne == 2026].groupby("province").apply(
        lambda g: pd.Series({"production_t": g.production_prevue_t.sum(),
                             "ratio_moyenne": np.average(g.ratio_moyenne, weights=g.superficie_ha)}), include_groups=False)
    sc = lire("r_recolte_scenarios_2027.csv").groupby("province").proba_mauvaise_pct.mean()
    spi = lire("r_spi3.csv")
    spi = spi[spi.mois == spi.mois.max()].set_index("province")
    out = []
    for p in PROV_ORDRE:
        i = info.loc[p]
        out.append(dict(province=p, type=i.type, nom_ar=i.nom_ar, surface_km2=i.surface_km2, lat=i.lat, lon=i.lon,
                        sol_type=i.sol, pluie_2026_mm=sa26.pluie_mm.get(p), pluie_normale_mm=sa26.normale_mm.get(p),
                        pluie_2026_pct=sa26.pct_normale.get(p), sol_classe=sol.classe.get(p), sol_percentile=sol.percentile.get(p),
                        recolte_2026_t=r26.production_t.get(p) if p in r26.index else None,
                        recolte_2026_ratio=r26.ratio_moyenne.get(p) if p in r26.index else None,
                        risque_2027_pct=sc.get(p), spi3=spi.spi3.get(p), spi3_mois=spi.mois.max() if len(spi) else None,
                        spi3_classe=spi.classe.get(p)))
    return propre(out)


@app.get("/api/region/citoyen")
def region_citoyen(province: str = "Settat"):
    """Tout ce qu'affiche l'espace citoyen pour une province, en valeurs simples."""
    _verif_province(province)
    sa = lire("r_pluie_saisons.csv")
    sa = sa[sa.province == province].set_index("saison")
    cl = lire("r_pluie_climatologie.csv")
    cl = cl[cl.province == province].set_index("m")
    c = reg_climat()
    c = c[c.province == province].dropna(subset=["pluie_mm"])
    der_pluie = c.mois.max()
    sol = lire("r_sol_etat.csv").set_index("province").loc[province]
    sp = lire("r_sol_prevision.csv")
    sp = sp[sp.province == province].sort_values("h")
    rp = lire("r_recolte_previsions.csv")
    r26 = rp[(rp.province == province) & (rp.campagne == 2026)]
    sc = lire("r_recolte_scenarios_2027.csv")
    sc = sc[sc.province == province]
    bi = jlire("r_barrage_info.json")
    bp = lire("r_barrage_prevision.csv")
    terc = lire("r_pluie_terciles.csv").iloc[0].to_dict() if (RES / "r_pluie_terciles.csv").exists() else {}
    hist = rp[rp.province == province]
    return propre({
        "province": province,
        "pluie": {"saison": "2025-2026", "total_mm": sa.pluie_mm.get(2026), "normale_mm": sa.normale_mm.get(2026),
                  "pct": sa.pct_normale.get(2026), "saison_precedente_pct": sa.pct_normale.get(2025),
                  "dernier_mois": der_pluie, "dernier_mois_mm": c[c.mois == der_pluie].pluie_mm.iloc[0],
                  "hiver_normale_mm": float(cl.loc[[12, 1, 2]].normale.sum()),
                  "par_saison": [{"saison": int(k), "pct": v} for k, v in sa[sa.mois == 12].pct_normale.items()],
                  "rpss": terc.get("rpss")},
        "sol": {"mois": sol.mois, "classe": sol.classe, "percentile": sol.percentile,
                "prevision": [{"mois": r.mois_cible, "percentile": r.percentile} for r in sp.itertuples()]},
        "recolte": {"campagne": 2026, "par_culture": lignes(r26[["culture", "rendement_prevu", "moyenne_qx_ha", "ratio_moyenne", "production_prevue_t"]]),
                    "ratio": float(np.average(r26.ratio_moyenne, weights=r26.superficie_ha)) if len(r26) else None,
                    "production_t": float(r26.production_prevue_t.sum()) if len(r26) else None,
                    "precedentes": [{"campagne": int(k), "ratio": float(np.average(g.ratio_moyenne, weights=g.superficie_ha))}
                                    for k, g in hist.groupby("campagne")],
                    "scenarios_2027": lignes(sc[["culture", "annee_seche", "annee_normale", "annee_pluvieuse", "moyenne_qx_ha", "proba_mauvaise_pct"]])},
        "eau": {**bi["dernier"], "capacite_Mm3": bi["capacite_Mm3"], "risque": bi["risque"],
                "annees_conso_casa": bi["dernier"]["volume_Mm3"] / bi["conso_casablanca_Mm3_an"],
                "prevision": lignes(bp), "source_conso": bi["source_conso"]},
    })


@app.get("/api/region/pluie")
def region_pluie(province: str = "Settat"):
    _verif_province(province)
    c = reg_climat()
    c = c[c.province == province][["mois", "pluie_mm"]].dropna()
    cl = lire("r_pluie_climatologie.csv")
    spi = lire("r_spi3.csv")
    sa = lire("r_pluie_saisons.csv")
    return {"mensuel": lignes(c), "climatologie": lignes(cl[cl.province == province]),
            "spi3": lignes(spi[spi.province == province][["mois", "spi3", "classe"]]),
            "saisons": lignes(sa[sa.mois == 12][["province", "saison", "pluie_mm", "normale_mm", "pct_normale"]])}


@app.get("/api/region/sol")
def region_sol(province: str = "Settat"):
    _verif_province(province)
    c = reg_climat()
    c = c[c.province == province][["mois", "pluie_mm", "humidite_sol_0_7cm", "humidite_sol_7_28cm", "et0_mm",
                                    "tmax_moy_C", "source_era5"]].dropna(subset=["humidite_sol_7_28cm"])
    sp = lire("r_sol_prevision.csv")
    return {"mensuel": lignes(c.drop(columns="source_era5")), "source": c.source_era5.iloc[-1],
            "prevision": lignes(sp[sp.province == province][["mois_cible", "h", "bas", "prevision", "haut", "percentile"]]),
            "etat": lignes(lire("r_sol_etat.csv")), "metriques": lignes(lire("r_sol_metriques.csv"))}


@app.get("/api/region/recolte")
def region_recolte(province: str = None):
    rend = pd.read_csv(REGION / "rendements_provinces_2010_2023.csv")
    val = lire("r_recolte_validation.csv")
    prev = lire("r_recolte_previsions.csv")
    sc = lire("r_recolte_scenarios_2027.csv")
    if province:
        _verif_province(province)
        rend, val, prev, sc = [d[d.province == province] for d in (rend, val, prev, sc)]
    imp = lire("r_recolte_importance.csv") if (RES / "r_recolte_importance.csv").exists() else pd.DataFrame()
    return {"historique": lignes(rend), "validation": lignes(val), "previsions": lignes(prev), "scenarios": lignes(sc),
            "metriques": lignes(lire("r_recolte_metriques.csv")), "importance": lignes(imp),
            "region": lignes(lire("r_recolte_validation_region.csv")), "info": jlire("r_recolte_info.json")}


@app.get("/api/region/barrage")
def region_barrage():
    b = pd.read_csv(REGION / "barrage_al_massira_releves.csv")
    return {"releves": lignes(b), "intervalles": lignes(lire("r_barrage_intervalles.csv")),
            "trajectoire": lignes(lire("r_barrage_trajectoire.csv")), "prevision": lignes(lire("r_barrage_prevision.csv")),
            "info": jlire("r_barrage_info.json")}


@app.get("/api/region/evaluation-pluie")
def region_eval_pluie():
    return lignes(lire("r_pluie_terciles.csv"))[0]


# ======================================================================== ACCUEIL
@app.get("/api/resume")
def resume():
    P = prix_donnees()
    reg = rendement_region()
    hyb = [r for r in reg["previsions"] if r["campagne"] == 2026 and r["modele"] == R.HYBRIDE][0]
    etat = lire("m2_etat_actuel.csv")
    prev = lire("m2_prevision_3_mois.csv")
    tom = prix_prevision("Tomate", 4)
    vul = lire("v4_vulnerabilite.csv")
    tp = lire("v4_prevision_12_mois.csv")
    mk = tp[tp.destination == "Marrakech"]
    dp = lire("v5_prevision_8_semaines.csv")
    tr = json.loads((RES / "v5_tournees.json").read_text(encoding="utf-8"))
    ap = lire("v6_prevision_3_jours.csv")
    a1 = ap[(ap.h == 1) & (ap.polluant == "pm10")]
    ville = {
        "tourisme": {"marrakech_12m": mk.prevision.sum(), "plus_vulnerable": vul.destination.iloc[0],
                     "score": vul.score_vulnerabilite.iloc[0], "destinations": len(vul)},
        "dechets": {"tonnes_semaine": dp[dp.h == 1].prevision.sum(), "villes": dp.ville.nunique(),
                    "quartiers": dp.quartier.nunique(),
                    "camions_aid_marrakech": tr["aid"]["Marrakech"]["camions"],
                    "camions_semaine_marrakech": tr["semaine"]["Marrakech"]["camions"],
                    "gain_km_pct": np.mean([tr["semaine"][v]["gain_km_pct"] for v in tr["semaine"]])},
        "air": {"date": a1.date.iloc[0], "stations": a1.station.nunique(),
                "stations_degradees": int(a1.classe.isin(["médiocre", "mauvais", "très mauvais"]).sum()),
                "pire_station": a1.sort_values("prevision").station.iloc[-1], "pire_pm10": a1.prevision.max()},
    }
    return propre({"ville": ville,
        "prix": {"produits": len(prix_xgb()), "releves": int(P.observe.values.sum()),
                 "debut": P.w.index[0], "fin": P.w.index[-1], "tomate": tom["dernier_prix"],
                 "tomate_4sem": tom["prevision"][-1]["prevision"]},
        "rendement": {"campagne": 2026, "production_Mqx": hyb["production_Mqx"],
                      "rendement_qx_ha": hyb["rendement_qx_ha"], "officiel_Mqx": OFFICIEL_2026["production_Mqx"]},
        "secheresse": {"mois": etat.mois.iloc[0], "zones_en_secheresse": int((etat.spi_3 <= -1).sum()),
                       "zones": len(etat), "alertes_mois_prochain": int((prev[prev.horizon_mois == 1]
                                                                          .alerte_secheresse == "oui").sum())},
    })


# ======================================================================== FRONTEND COMPILÉ
DIST = PROJET / "app" / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{chemin:path}")
    def spa(chemin: str):
        f = DIST / chemin
        return FileResponse(f if chemin and f.is_file() else DIST / "index.html")
