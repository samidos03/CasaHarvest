"""CasaHarvest — module 2 : prévision du risque de sécheresse (SPI-3) par zone de Casablanca-Settat.

Cible : SPI-3 du mois t+h (h = 1, 2, 3 mois), indice de précipitations standardisé sur 3 mois
        (≤ -1 : sécheresse modérée, ≤ -1,5 : sévère, ≤ -2 : extrême).
Variables connues au mois t : SPI-1, SPI-3, SPI-6, SPI-12, anomalie d'humidité du sol, mois visé, zone.
Saison : mois visés d'octobre à mai seulement (en été il ne pleut presque pas : le SPI n'a pas de sens).
Évaluation : validation temporelle à fenêtre croissante — pour chaque année de test (2018 à 2026), les modèles
sont entraînés sur les années précédentes uniquement.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA = Path(__file__).resolve().parent.parent / "data" / "casaharvest"
NUM = ["spi_1", "spi_3", "spi_6", "spi_12", "anomalie_humidite_sol", "sin_mois", "cos_mois"]
SAISON = [10, 11, 12, 1, 2, 3, 4, 5]
SEUIL = -1.0    # sécheresse observée (définition standard du SPI)
# seuil d'alerte sur la prévision : la régression ramène les prévisions vers la normale, un seuil de -1 ne détecte
# que ~20 % des sécheresses ; à -0,5 (choisi sur la validation) : ~76 % détectées à 1 mois, ~41 % de fausses alertes
ALERTE = -0.5


def charger():
    s = pd.read_csv(DATA / "secheresse_mensuelle_zones.csv")
    s["date"] = pd.to_datetime(s.mois)
    return s.sort_values(["zone", "date"]).reset_index(drop=True)


def panneau(s, h):
    """Une ligne par (zone, mois t) : variables en t, cible = SPI-3 en t+h."""
    blocs = []
    for z, g in s.groupby("zone"):
        g = g.set_index("date")
        d = g[["spi_1", "spi_3", "spi_6", "spi_12", "anomalie_humidite_sol"]].copy()
        d["zone"] = z
        d["date_cible"] = d.index + pd.DateOffset(months=h)
        d["cible"] = g.spi_3.reindex(d.date_cible).values
        blocs.append(d.reset_index())
    p = pd.concat(blocs, ignore_index=True)
    m = p.date_cible.dt.month
    p["sin_mois"], p["cos_mois"] = np.sin(2 * np.pi * m / 12), np.cos(2 * np.pi * m / 12)
    return p[m.isin(SAISON)]


def modele(nom):
    if nom == "Ridge":
        pre = ColumnTransformer([("num", StandardScaler(), NUM), ("cat", OneHotEncoder(), ["zone"])])
        return make_pipeline(pre, RidgeCV(alphas=np.logspace(-2, 3, 30)))
    pre = ColumnTransformer([("num", "passthrough", NUM), ("cat", OneHotEncoder(), ["zone"])])
    return make_pipeline(pre, xgb.XGBRegressor(n_estimators=300, learning_rate=0.03, max_depth=3,
                                               min_child_weight=5, subsample=0.8, colsample_bytree=0.8,
                                               reg_lambda=5.0, random_state=0, n_jobs=4))


def validation(s, annees=range(2018, 2027)):
    rows = []
    for h in (1, 2, 3):
        p = panneau(s, h).dropna(subset=NUM + ["cible"])
        for nom in ["Ridge", "XGBoost"]:
            for an in annees:
                tr = p.date_cible < f"{an}-01-01"
                te = p.date_cible.dt.year == an
                if te.sum() == 0:
                    continue
                m = modele(nom).fit(p.loc[tr, NUM + ["zone"]], p.cible[tr])
                pr = m.predict(p.loc[te, NUM + ["zone"]])
                rows.append(p.loc[te, ["zone", "date", "date_cible", "cible"]].assign(
                    horizon=h, modele=nom, prevision=pr))
    return pd.concat(rows, ignore_index=True)


def metriques(v):
    def m(g):
        sec = g.cible <= SEUIL
        alerte = g.prevision <= ALERTE
        return pd.Series({
            "RMSE": np.sqrt(np.mean((g.cible - g.prevision) ** 2)),
            "R2": r2_score(g.cible, g.prevision), "correlation": g.cible.corr(g.prevision),
            "AUC_secheresse": roc_auc_score(sec, -g.prevision) if 0 < sec.sum() < len(g) else np.nan,
            "secheresses_detectees_pct": 100 * (alerte & sec).sum() / max(sec.sum(), 1),
            "fausses_alertes_pct": 100 * (alerte & ~sec).sum() / max(alerte.sum(), 1),
            "n": len(g), "mois_en_secheresse": int(sec.sum())})
    return v.groupby(["horizon", "modele"]).apply(m, include_groups=False).round(3)


def classe(v):
    return ("sécheresse extrême" if v <= -2 else "sécheresse sévère" if v <= -1.5 else
            "sécheresse modérée" if v <= -1 else "normal" if v < 1 else "humide")


def prevoir(s, nom="XGBoost"):
    """Prévision des 3 prochains mois à partir du dernier mois où le SPI est connu."""
    rows = []
    for h in (1, 2, 3):
        p = panneau(s, h)
        tr = p.dropna(subset=NUM + ["cible"])
        m = modele(nom).fit(tr[NUM + ["zone"]], tr.cible)
        der = s.dropna(subset=["spi_3"]).date.max()
        x = panneau(s, h)
        x = x[(x.date == der)].dropna(subset=NUM)
        if x.empty:  # mois visé hors saison des pluies
            continue
        for z, v, dc in zip(x.zone, m.predict(x[NUM + ["zone"]]), x.date_cible):
            rows.append({"zone": z, "dernier_mois_connu": der.strftime("%Y-%m"), "mois_prevu": dc.strftime("%Y-%m"),
                         "horizon_mois": h, "spi3_prevu": round(float(v), 2), "classe": classe(v),
                         "alerte_secheresse": "oui" if v <= ALERTE else "non",
                         "fiabilite": {1: "bonne", 2: "faible", 3: "très faible (indicatif)"}[h]})
    return pd.DataFrame(rows)
