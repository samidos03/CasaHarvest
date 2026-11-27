"""CasaHarvest — module 1 : prévision du rendement des céréales (blé tendre, blé dur, orge) par zone de
Casablanca-Settat, à partir du climat de la campagne.

Deux moments de prévision :
  - « mars »  : variables connues fin mars (pluie d'automne et d'hiver, humidité du sol en hiver, SPI-6 de mars)
                -> prévision précoce, utile pour anticiper la récolte et les prix
  - « mai »   : + pluie, humidité du sol et chaleur du printemps -> prévision de fin de campagne
Modèles : régression Ridge (linéaire régularisée) et XGBoost.
Évaluation : validation croisée « une campagne laissée de côté » (14 plis) — toutes les zones d'une même année
sont mises de côté ensemble, car elles partagent la même météo (sinon l'évaluation serait trop optimiste).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA = Path(__file__).resolve().parent.parent / "data" / "casaharvest"
CULTURES = ["Blé tendre", "Blé dur", "Orge"]
# Variables retenues : avec 14 campagnes, un jeu réduit est plus stable. Tests (validation croisée, XGBoost) :
#   8 variables climatiques R² 0,45 ; SPI-6 de mars seul R² 0,47 ; SPI-6 + humidité du sol + chaleur R² 0,47.
# Les variables de pluie sont redondantes avec le SPI-6 (qui résume la pluie des 6 derniers mois).
VARS = {
    "mars": ["spi_6_mars", "humidite_sol_hiver"],
    "mai": ["spi_6_mars", "humidite_sol_printemps", "jours_chauds_printemps"],
}
CATS = ["culture", "zone"]


def charger():
    ml = pd.read_csv(DATA / "table_ml_rendement_climat.csv")
    ml = ml[ml.culture.isin(CULTURES) & (ml.zone != "Région Casablanca-Settat")].dropna(subset=VARS["mai"] + VARS["mars"])
    clim = pd.read_csv(DATA / "climat_par_campagne_zones.csv")
    clim = clim[clim.zone != "Région Casablanca-Settat"]
    return ml.reset_index(drop=True), clim


def modele(nom, moment):
    num = VARS[moment]
    if nom == "Ridge":
        pre = ColumnTransformer([("num", StandardScaler(), num),
                                 ("cat", OneHotEncoder(handle_unknown="ignore"), CATS)])
        return make_pipeline(pre, RidgeCV(alphas=np.logspace(-2, 3, 30)))
    pre = ColumnTransformer([("num", "passthrough", num),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), CATS)])
    return make_pipeline(pre, xgb.XGBRegressor(n_estimators=300, learning_rate=0.03, max_depth=2,
                                               min_child_weight=5, subsample=0.8, colsample_bytree=0.8,
                                               reg_lambda=5.0, random_state=0, n_jobs=4))


HYBRIDE = "Hybride (XGBoost + garde-fou Ridge)"


def predire(Xtr, ytr, Xte, moment):
    """Prévisions des trois modèles. Hybride : XGBoost quand le climat ressemble au passé ; Ridge quand une
    variable sort de la plage observée à l'entraînement (les arbres de XGBoost ne savent pas extrapoler :
    au-delà de l'année la plus humide connue, ils répètent ce qu'ils ont vu pour cette année-là)."""
    pr = {nom: np.clip(modele(nom, moment).fit(Xtr, ytr).predict(Xte), 0, None) for nom in ["Ridge", "XGBoost"]}
    num = VARS[moment]
    hors = ((Xte[num] < Xtr[num].min()) | (Xte[num] > Xtr[num].max())).any(axis=1).values
    pr[HYBRIDE] = np.where(hors, pr["Ridge"], pr["XGBoost"])
    return pr, hors


def validation_croisee(ml):
    """Une campagne laissée de côté ; renvoie les prévisions hors échantillon de chaque modèle."""
    rows = []
    for moment in VARS:
        X = ml[VARS[moment] + CATS]
        for camp in sorted(ml.campagne.unique()):
            tr, te = ml.campagne != camp, ml.campagne == camp
            pr, hors = predire(X[tr], ml.rendement_qx_ha[tr], X[te], moment)
            for nom, p in pr.items():
                for (_, r), v, hd in zip(ml[te].iterrows(), p, hors):
                    rows.append({"moment": moment, "modele": nom, "campagne": camp, "zone": r.zone,
                                 "culture": r.culture, "surface_ha": r.surface_ha, "reel": r.rendement_qx_ha,
                                 "prevision": v, "extrapolation": bool(hd)})
    return pd.DataFrame(rows)


def metriques(cv):
    def m(g):
        return pd.Series({"MAE_qx_ha": mean_absolute_error(g.reel, g.prevision),
                          "RMSE_qx_ha": np.sqrt(np.mean((g.reel - g.prevision) ** 2)),
                          "R2": r2_score(g.reel, g.prevision), "n": len(g)})
    tab = cv.groupby(["moment", "modele"]).apply(m, include_groups=False).round(3)
    par_culture = cv.groupby(["moment", "modele", "culture"]).apply(m, include_groups=False).round(3)
    # niveau régional : rendement moyen pondéré par la surface, par campagne et par culture
    reg = (cv.assign(pr=cv.prevision * cv.surface_ha, re=cv.reel * cv.surface_ha)
           .groupby(["moment", "modele", "campagne", "culture"])
           .agg(pr=("pr", "sum"), re=("re", "sum"), s=("surface_ha", "sum")).reset_index())
    reg["prevision"], reg["reel"] = reg.pr / reg.s, reg.re / reg.s
    tab_reg = reg.groupby(["moment", "modele"]).apply(m, include_groups=False).round(3)
    return tab, par_culture, tab_reg, reg


def importance(ml, moment="mai"):
    """Coefficients standardisés de la Ridge (effet d'un écart-type de chaque variable, en qx/ha)."""
    m = modele("Ridge", moment).fit(ml[VARS[moment] + CATS], ml.rendement_qx_ha)
    noms = m[0].get_feature_names_out()
    coef = pd.Series(m[-1].coef_, index=[n.split("__", 1)[1] for n in noms])
    return coef[VARS[moment]].sort_values(key=abs, ascending=False)


def prevoir_futur(ml, clim, campagnes=(2024, 2025, 2026), moment="mai"):
    """Prévision des campagnes sans rendement publié (2024-2026), à partir du climat observé, avec les 3 modèles.
    Production = rendement prévu × surface moyenne des 3 dernières campagnes connues (approximation)."""
    Xtr = ml[VARS[moment] + CATS]
    surf = ml[ml.campagne >= ml.campagne.max() - 2].groupby(["zone", "culture"]).surface_ha.mean()
    rows = []
    for camp in campagnes:
        c = clim[clim.campagne == camp]
        for cult in CULTURES:
            X = c.assign(culture=cult)[VARS[moment] + CATS]
            pr, hors = predire(Xtr, ml.rendement_qx_ha, X, moment)
            for i, z in enumerate(X.zone):
                for nom, p in pr.items():
                    rows.append({"campagne": camp, "zone": z, "culture": cult, "modele": nom,
                                 "prevision_qx_ha": round(float(p[i]), 1), "extrapolation": bool(hors[i]),
                                 "surface_ref_ha": float(surf.get((z, cult), np.nan))})
    out = pd.DataFrame(rows)
    out["production_prevue_qx"] = out.prevision_qx_ha * out.surface_ref_ha
    reg = out.groupby(["campagne", "modele"]).agg(prod=("production_prevue_qx", "sum"), surf=("surface_ref_ha", "sum"))
    reg["rendement_moyen_qx_ha"] = (reg["prod"] / reg.surf).round(1)
    reg["production_Mqx"] = (reg["prod"] / 1e6).round(2)
    return out, reg[["rendement_moyen_qx_ha", "production_Mqx"]].unstack("modele")
