"""XGBoost sur les prix de gros hebdomadaires (Casablanca, DH/kg), stratégie directe multi-horizon.

Pour chaque horizon h (1..H semaines), un modèle XGBoost global (tous produits) prédit
    cible = log(prix[t+h]) - log(prix[t])
à partir de variables connues à la date t : dynamique récente du prix, saisonnalité, calendrier de la
semaine cible (Ramadan, Aïd), météo du Souss (bassin de production) et de Casablanca, produit et famille.

Évaluation sans fuite de données : à chaque origine o, la série est reconstruite avec les seuls relevés
connus à o (interpolation entre relevés passés uniquement), les modèles sont ré-entraînés sur les couples
(t, t+h) avec t+h <= o, et la prévision part du dernier relevé réel <= o.
"""
import numpy as np
import pandas as pd
import xgboost as xgb

from donnees import FAMILLE_PRODUIT, series_hebdo
from modele_prevision import profil_saisonnier

H = 8
# réglage retenu sur la 1re moitié des origines du backtest (validation) parmi 4 configurations :
# arbres peu profonds et apprentissage lent (peu de données -> forte régularisation)
PARAMS = dict(n_estimators=400, learning_rate=0.01, max_depth=2, min_child_weight=30, subsample=0.7,
              colsample_bytree=0.8, reg_lambda=30.0, objective="reg:pseudohubererror", huber_slope=0.15,
              tree_method="hist", enable_categorical=True, random_state=0, n_jobs=4)
VARIABLES = ["r1", "r4", "r13", "ecart_moy8", "volat8", "saison_diff", "an_passe", "sin_cible", "cos_cible",
             "mois_cible", "ramadan_cible", "avant_ramadan_cible", "aid_cible", "avant_aid_cible",
             "pluie_souss_4s", "tmax_souss_4s", "tmin_souss_4s", "pluie_casa_4s", "produit", "famille"]
NOMS = {"r1": "variation 1 semaine", "r4": "variation 4 semaines", "r13": "variation 13 semaines",
        "ecart_moy8": "écart à la moyenne 8 sem.", "volat8": "volatilité 8 sem.",
        "saison_diff": "effet saisonnier attendu", "an_passe": "évolution l'an passé (même période)",
        "sin_cible": "semaine de l'année (sin)", "cos_cible": "semaine de l'année (cos)", "mois_cible": "mois cible",
        "ramadan_cible": "Ramadan", "avant_ramadan_cible": "semaine avant Ramadan", "aid_cible": "Aïd al-Adha",
        "avant_aid_cible": "semaine avant l'Aïd", "pluie_souss_4s": "pluie Souss (4 sem.)",
        "tmax_souss_4s": "température max Souss", "tmin_souss_4s": "température min Souss",
        "pluie_casa_4s": "pluie Casablanca (4 sem.)", "produit": "produit", "famille": "famille de produit"}


def serie_a_origine(w, observe, o):
    """Log-prix reconstruits avec les seuls relevés <= o."""
    lw = np.log(w.where(observe)).loc[:o]
    return lw.interpolate(limit_area="inside"), observe.loc[:o]


def panneau(lw, obs, exo, h, profils):
    """Variables pour tous les couples (produit, t) et la cible log p(t+h) - log p(t) (si t+h est relevé)."""
    idx = lw.index
    futur = pd.date_range(idx[0], idx[-1] + pd.Timedelta(weeks=h), freq="W-WED")
    ex = exo.reindex(futur)
    woy_t = np.asarray(idx.isocalendar().week, float)
    cible_dt = idx + pd.Timedelta(weeks=h)
    woy_c = np.asarray(cible_dt.isocalendar().week, float)
    blocs = []
    for p in lw.columns:
        l = lw[p]
        b = pd.DataFrame({"t": idx, "cible_dt": cible_dt, "produit": p,
                          "r1": l - l.shift(1), "r4": l - l.shift(4), "r13": l - l.shift(13),
                          "ecart_moy8": l - l.rolling(8, min_periods=6).mean(),
                          "volat8": l.diff().rolling(8, min_periods=6).std(),
                          "an_passe": l.shift(52 - h) - l.shift(52),
                          "saison_diff": profils[p](woy_c) - profils[p](woy_t),
                          "sin_cible": np.sin(2 * np.pi * woy_c / 52.18), "cos_cible": np.cos(2 * np.pi * woy_c / 52.18),
                          "mois_cible": cible_dt.month,
                          "observe_t": obs[p].values, "l0": l.values}, index=idx)
        lc = l.reindex(cible_dt).values
        oc = obs[p].reindex(cible_dt).fillna(False).astype(bool).values
        b["cible"] = np.where(oc, lc - l.values, np.nan)
        blocs.append(b.reset_index(drop=True))
    df = pd.concat(blocs, ignore_index=True)
    ec = ex.reindex(df.cible_dt)
    et = ex.reindex(df.t)
    df["ramadan_cible"] = ec.ramadan.values
    df["avant_ramadan_cible"] = ec.semaine_avant_ramadan.values
    df["aid_cible"] = ec.aid_al_adha.values
    df["avant_aid_cible"] = ec.semaine_avant_aid.values
    for c in ["pluie_souss_4s", "tmax_souss_4s", "tmin_souss_4s", "pluie_casa_4s"]:
        df[c] = et[c].values
    df["produit"] = pd.Categorical(df.produit, categories=list(lw.columns))
    df["famille"] = pd.Categorical(df.produit.astype(str).map(FAMILLE_PRODUIT).fillna("autre"),
                                   categories=["légume", "fruit", "viande", "autre"])
    return df


def backtest(n_test=40, pas=2, verbose=True, params=None):
    w, observe, exo = series_hebdo()
    params = params or PARAMS
    res, imp = [], []
    origines = w.index[-n_test - H:-1:pas]
    for k, o in enumerate(origines):
        lw, obs = serie_a_origine(w, observe, o)
        profils = {p: profil_saisonnier(w, observe, p, fin=o) for p in w.columns}
        for h in range(1, H + 1):
            pan = panneau(lw, obs, exo, h, profils)
            tr = pan[pan.observe_t & pan.cible.notna() & pan.r4.notna()]
            m = xgb.XGBRegressor(**params).fit(tr[VARIABLES], tr.cible)
            if k == len(origines) - 1:
                imp.append(pd.Series(m.get_booster().get_score(importance_type="gain"), name=h))
            # point de départ : dernier relevé réel <= o, pour chaque produit
            for p in w.columns:
                po = obs[p][obs[p]]
                if po.empty:
                    continue
                d0 = po.index[-1]
                cible_dt = d0 + pd.Timedelta(weeks=h)
                if cible_dt not in w.index or not observe[p].get(cible_dt, False) or cible_dt <= o:
                    continue
                x = pan[(pan.produit == p) & (pan.t == d0)]
                if x.empty or pd.isna(x.r4.iloc[0]):
                    continue
                p0 = np.exp(x.l0.iloc[0])
                vrai = w[p][cible_dt]
                val = p0 * np.exp(m.predict(x[VARIABLES])[0])
                res.append({"origine": o, "produit": p, "horizon": int((cible_dt - d0).days / 7),
                            "methode": "XGBoost", "dernier_prix": p0, "prevision": val, "reel": vrai,
                            "erreur_pct": abs(val / vrai - 1) * 100})
        if verbose:
            print(f"origine {o.date()} ({k + 1}/{len(origines)})", flush=True)
    res = pd.DataFrame(res)
    importance = pd.concat(imp, axis=1).fillna(0)
    importance = (importance / importance.sum()).mean(axis=1).sort_values(ascending=False)
    importance.index = importance.index.map(lambda v: NOMS.get(v, v))
    return res, importance


def modele_final(h):
    """Entraîne le modèle XGBoost de l'horizon h sur toutes les données (pour la prévision réelle)."""
    w, observe, exo = series_hebdo()
    o = w.index[-1]
    lw, obs = serie_a_origine(w, observe, o)
    profils = {p: profil_saisonnier(w, observe, p) for p in w.columns}
    pan = panneau(lw, obs, exo, h, profils)
    tr = pan[pan.observe_t & pan.cible.notna() & pan.r4.notna()]
    return xgb.XGBRegressor(**PARAMS).fit(tr[VARIABLES], tr.cible), pan


def prevoir_tous(produits=None):
    """Prévision XGBoost des H prochaines semaines pour chaque produit, à partir du dernier relevé.
    Renvoie {produit: (Series des prévisions indexée par semaine, date du dernier relevé)}."""
    out = {}
    for h in range(1, H + 1):
        m, pan = modele_final(h)
        for p in produits or pan.produit.cat.categories:
            x = pan[(pan.produit == p) & pan.observe_t]
            if x.empty:
                continue
            x = x[x.t == x.t.max()]
            if pd.isna(x.r4.iloc[0]):
                continue
            d0 = x.t.iloc[0]
            val = float(np.exp(x.l0.iloc[0]) * np.exp(m.predict(x[VARIABLES])[0]))
            s, _ = out.get(p, (pd.Series(dtype=float), d0))
            s.loc[d0 + pd.Timedelta(weeks=h)] = val
            out[p] = (s, d0)
    return out


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    res, imp = backtest(verbose=False)
    print(res.pivot_table(index="horizon", columns="methode", values="erreur_pct").round(1))
    print(imp.round(3))
