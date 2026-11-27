"""CasaHarvest Région Casablanca-Settat — modèles des 4 thèmes (9 préfectures et provinces).

A. Pluie (CHIRPS)          : cumul de la saison vs normale, SPI-3 (sécheresse), prévision du mois suivant en
                             « terciles » (sec / normal / pluvieux) évaluée contre la climatologie.
B. Humidité du sol (ERA5)  : état actuel (percentile), prévision 1 et 2 mois (Ridge, forêt aléatoire, XGBoost
                             comparés à la persistance), intervalle 80 %.
C. Récoltes (HCP)          : rendement blé tendre / blé dur / orge par province ; Ridge, forêt aléatoire, XGBoost
                             et référence « moyenne de la province » évalués campagne par campagne (validation
                             croisée « une campagne laissée de côté ») ; prévisions 2024-2026 ; zones à risque ;
                             scénarios 2027 (sec / normal / pluvieux).
D. Barrage Al Massira      : bilan hydrique calibré sur 39 relevés officiels ; prévision à 7, 30 et 90 jours par
                             ensemble de scénarios de pluie (années analogues) -> quantiles 10/50/90 % et risque
                             de pénurie.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

REG = Path(__file__).resolve().parent.parent / "data" / "region"
NORMALE = (2010, 2025)  # saisons complètes servant de « normale »


def charger():
    prov = pd.read_csv(REG / "provinces.csv")
    clim = pd.read_csv(REG / "climat_mensuel_provinces.csv")
    clim["date"] = pd.to_datetime(clim.mois)
    # saison agricole : septembre -> août, nommée par l'année de récolte (2026 = sept. 2025 -> août 2026)
    clim["saison"] = clim.date.dt.year + (clim.date.dt.month >= 9)
    rend = pd.read_csv(REG / "rendements_provinces_2010_2023.csv")
    return prov, clim, rend


# ================================================================================ A. PLUIE
def pluie_saison(clim):
    p = clim.dropna(subset=["pluie_mm"])
    s = p.groupby(["province", "saison"]).agg(pluie_mm=("pluie_mm", "sum"), mois=("pluie_mm", "size")).reset_index()
    comp = s[s.mois == 12]
    norm = comp[comp.saison.between(*NORMALE)].groupby("province").pluie_mm.agg(["mean", "std", "min", "max"])
    s = s.join(norm, on="province")
    s["pct_normale"] = s.pluie_mm / s["mean"] * 100
    return s.rename(columns={"mean": "normale_mm", "std": "ecart_type_mm", "min": "min_mm", "max": "max_mm"}), norm


def pluie_climatologie(clim):
    p = clim[clim.saison.between(*NORMALE)].dropna(subset=["pluie_mm"])
    p = p.assign(m=p.date.dt.month)
    return p.groupby(["province", "m"]).pluie_mm.agg(normale="mean", p10=lambda x: x.quantile(.1),
                                                     p90=lambda x: x.quantile(.9)).reset_index()


def spi(clim, k=3):
    """SPI-k : pluie cumulée sur k mois comparée à la même période des autres années (loi gamma)."""
    out = []
    for prov, g in clim.dropna(subset=["pluie_mm"]).sort_values("date").groupby("province"):
        g = g.set_index("date")
        cum = g.pluie_mm.rolling(k).sum()
        z = pd.Series(np.nan, index=cum.index)
        for m in range(1, 13):
            idx = cum.index[(cum.index.month == m) & cum.notna()]
            x = cum[idx].values
            q = (x == 0).mean()
            pos = x[x > 0]
            if len(pos) < 8:
                continue
            a, loc, sc = stats.gamma.fit(pos, floc=0)
            cdf = q + (1 - q) * stats.gamma.cdf(x, a, loc=0, scale=sc)
            z[idx] = stats.norm.ppf(np.clip(cdf, .001, .999))
        out.append(pd.DataFrame({"province": prov, "mois": z.index.strftime("%Y-%m"), "spi3": z.values}))
    s = pd.concat(out).dropna()
    s["classe"] = pd.cut(s.spi3, [-9, -2, -1.5, -1, 1, 1.5, 9],
                         labels=["sécheresse extrême", "sécheresse sévère", "sécheresse modérée", "normal",
                                 "humide", "très humide"]).astype(str)
    return s


def pluie_terciles(clim):
    """Peut-on prévoir si le mois prochain sera sec, normal ou pluvieux ? Régression logistique sur le SPI-3
    et l'anomalie du mois en cours ; validation « une saison laissée de côté » ; score RPSS (0 = pas mieux que
    la climatologie, 1 = parfait)."""
    s = spi(clim)
    p = clim.dropna(subset=["pluie_mm"]).merge(s[["province", "mois", "spi3"]], on=["province", "mois"])
    p["m"] = p.date.dt.month
    clim_m = p[p.saison.between(*NORMALE)].groupby(["province", "m"]).pluie_mm
    t1, t2 = clim_m.quantile(1 / 3).rename("t1"), clim_m.quantile(2 / 3).rename("t2")
    p = p.join(t1, on=["province", "m"]).join(t2, on=["province", "m"])
    p["tercile"] = np.where(p.pluie_mm <= p.t1, 0, np.where(p.pluie_mm <= p.t2, 1, 2))
    p["anom"] = p.pluie_mm / p.groupby(["province", "m"]).pluie_mm.transform("mean").replace(0, 1) - 1
    p = p.sort_values(["province", "date"])
    p["cible"] = p.groupby("province").tercile.shift(-1)
    p["m_cible"] = p.groupby("province").m.shift(-1)
    p = p.dropna(subset=["cible"])
    p = p[p.m_cible.isin([10, 11, 12, 1, 2, 3, 4, 5])]  # saison des pluies
    X = np.column_stack([p.spi3, p.anom.clip(-1, 3), np.sin(2 * np.pi * p.m_cible / 12), np.cos(2 * np.pi * p.m_cible / 12)])
    y = p.cible.astype(int).values
    proba = np.zeros((len(p), 3))
    for s_ in p.saison.unique():
        tr, te = p.saison.values != s_, p.saison.values == s_
        m = LogisticRegression(C=.5, max_iter=500).fit(X[tr], y[tr])
        proba[te] = m.predict_proba(X[te])
    O = np.eye(3)[y]
    rps = lambda P: np.mean(np.sum((np.cumsum(P, 1) - np.cumsum(O, 1)) ** 2, 1))  # noqa: E731
    rpss = 1 - rps(proba) / rps(np.full_like(proba, 1 / 3))
    acc = float((proba.argmax(1) == y).mean())
    return dict(rpss=float(rpss), precision=acc * 100, precision_hasard=100 / 3, n=int(len(p)))


# ================================================================================ B. HUMIDITÉ DU SOL
def sol_etat(clim):
    """Percentile de l'humidité du sol (7-28 cm) du dernier mois par rapport au même mois 2010-2025."""
    c = clim.dropna(subset=["humidite_sol_7_28cm"])
    der = c.mois.max()
    out = []
    for prov, g in c.groupby("province"):
        g = g.assign(m=g.date.dt.month)
        x = g[g.mois == der]
        if x.empty:
            continue
        ref = g[(g.m == x.m.iloc[0]) & g.saison.between(*NORMALE)].humidite_sol_7_28cm
        v = float(x.humidite_sol_7_28cm.iloc[0])
        pct = float(stats.percentileofscore(ref, v))
        out.append(dict(province=prov, mois=der, humidite_7_28=v, humidite_0_7=float(x.humidite_sol_0_7cm.iloc[0]),
                        normale=float(ref.mean()), percentile=pct,
                        classe="sec" if pct < 33 else ("humide" if pct > 67 else "normal")))
    return pd.DataFrame(out)


FEAT_SOL = ["sm_t", "sm_surf_t", "pluie_t", "et0_t", "sin", "cos", "h"]


def _sol_table(clim, H=2):
    z = clim.drop_duplicates(["source_era5", "mois"]).dropna(subset=["humidite_sol_7_28cm"]).sort_values(["source_era5", "date"])
    # pluie : moyenne des provinces de la zone (CHIRPS)
    pz = clim.groupby(["source_era5", "mois"]).pluie_mm.mean().rename("pluie_z")
    z = z.join(pz, on=["source_era5", "mois"])
    rows = []
    for src, g in z.groupby("source_era5"):
        g = g.reset_index(drop=True)
        for i in range(len(g)):
            for h in range(1, H + 1):
                j = i + h
                cible = g.humidite_sol_7_28cm[j] if j < len(g) else np.nan
                m = (g.date[i] + pd.DateOffset(months=h)).month
                rows.append(dict(source=src, mois=g.mois[i], saison=g.saison[i], h=h, sm_t=g.humidite_sol_7_28cm[i],
                                 sm_surf_t=g.humidite_sol_0_7cm[i], pluie_t=g.pluie_z[i], et0_t=g.et0_mm[i],
                                 sin=np.sin(2 * np.pi * m / 12), cos=np.cos(2 * np.pi * m / 12), y=cible, m_cible=m))
    return pd.DataFrame(rows)


def _modeles():
    return {"Ridge": make_pipeline(StandardScaler(), Ridge(1.0)),
            "Forêt aléatoire": RandomForestRegressor(300, min_samples_leaf=4, random_state=0, n_jobs=4),
            "XGBoost": xgb.XGBRegressor(n_estimators=300, learning_rate=.05, max_depth=3, subsample=.8,
                                        min_child_weight=3, random_state=0, n_jobs=4)}


def sol_evaluer(clim):
    t = _sol_table(clim).dropna(subset=["y"])
    t["pluie_t"] = t.pluie_t.fillna(t.groupby("m_cible").pluie_t.transform("mean"))
    res, preds = [], {}
    for s_ in sorted(t.saison.unique()):
        tr, te = t[t.saison != s_], t[t.saison == s_]
        for nom, m in _modeles().items():
            m.fit(tr[FEAT_SOL], tr.y)
            preds.setdefault(nom, []).append(pd.Series(m.predict(te[FEAT_SOL]), index=te.index))
    out = []
    clim_m = t.groupby("m_cible").y.transform("mean")
    for h in (1, 2):
        sel = t.h == h
        y = t.y[sel]
        ref = {"Persistance (même valeur)": t.sm_t[sel], "Climatologie (moyenne du mois)": clim_m[sel]}
        for nom in preds:
            ref[nom] = pd.concat(preds[nom])[sel[sel].index]
        for nom, p in ref.items():
            out.append(dict(horizon=h, modele=nom, mae=float(np.mean(np.abs(p - y))),
                            r2=float(1 - np.sum((p - y) ** 2) / np.sum((y - y.mean()) ** 2))))
    r = pd.DataFrame(out)
    # résidus du meilleur modèle -> intervalle 80 %
    best = r[r.horizon == 1].sort_values("mae").modele.iloc[0]
    if best in preds:
        e = (t.y - pd.concat(preds[best])).groupby(t.h).quantile([.1, .9]).unstack()
    else:
        e = (t.y - t.sm_t).groupby(t.h).quantile([.1, .9]).unstack()
    return r, best, e, t


def sol_prevoir(clim, best, err):
    t = _sol_table(clim)
    t["pluie_t"] = t.pluie_t.fillna(t.groupby("m_cible").pluie_t.transform("mean"))
    tr = t.dropna(subset=["y"])
    mods = _modeles()
    m = mods[best] if best in mods else mods["Ridge"]
    m.fit(tr[FEAT_SOL], tr.y)
    der = t.mois.max()
    f = t[t.mois == der].copy()
    f["prevision"] = m.predict(f[FEAT_SOL])
    f["bas"] = f.prevision + f.h.map(err[.1])
    f["haut"] = f.prevision + f.h.map(err[.9])
    f["mois_cible"] = [(pd.Timestamp(der) + pd.DateOffset(months=int(h))).strftime("%Y-%m") for h in f.h]
    # percentile de la prévision par rapport au même mois
    z = clim.drop_duplicates(["source_era5", "mois"]).dropna(subset=["humidite_sol_7_28cm"])
    z = z.assign(m=z.date.dt.month)
    f["percentile"] = [float(stats.percentileofscore(z[(z.source_era5 == s) & (z.m == mc)].humidite_sol_7_28cm, v))
                       for s, mc, v in zip(f.source, f.m_cible, f.prevision)]
    return f[["source", "mois", "mois_cible", "h", "bas", "prevision", "haut", "percentile"]]


# ================================================================================ C. RÉCOLTES
FENETRES = {  # variables de la saison retenues après comparaison (voir README) : l'humidité du sol en
    # février-mars est le meilleur indicateur (corrélation 0,7 avec le rendement relatif), puis la pluie
    # de novembre à janvier (semis, tallage) et la chaleur au printemps (remplissage du grain)
    "sol_fev_mar": ("humidite_sol_7_28cm", [2, 3], "mean"),
    "pluie_nov_jan": ("pluie_mm", [11, 12, 1], "sum"),
    "tmax_mar_mai": ("tmax_moy_C", [3, 4, 5], "mean"),
}
FEAT_R = list(FENETRES) + ["culture_bd", "culture_orge", "niveau_province"]
CULTURES = ["Blé tendre", "Blé dur", "Orge"]


def features_saison(clim):
    c = clim.assign(m=clim.date.dt.month)
    rows = []
    for (prov, s), g in c.groupby(["province", "saison"]):
        r = {"province": prov, "campagne": s}
        for nom, (col, ms, agg) in FENETRES.items():
            x = g[g.m.isin(ms)][col].dropna()
            r[nom] = (x.sum() if agg == "sum" else x.mean()) if len(x) == len(ms) else np.nan
        rows.append(r)
    f = pd.DataFrame(rows)
    ndvi = REG / "ndvi_provinces.csv"  # optionnel (collecte_provinces.py)
    if ndvi.exists():
        n = pd.read_csv(ndvi)
        n["date"] = pd.to_datetime(n.mois)
        n = n[n.date.dt.month.isin([2, 3])]
        n["campagne"] = n.date.dt.year
        f = f.merge(n.groupby(["province", "campagne"]).ndvi.mean().rename("ndvi_fev_mar").reset_index(), how="left")
    return f


def _table_rendement(rend, feats):
    t = rend[rend.culture.isin(CULTURES)].merge(feats, on=["province", "campagne"], how="left")
    t["culture_bd"] = (t.culture == "Blé dur").astype(int)
    t["culture_orge"] = (t.culture == "Orge").astype(int)
    return t


def _cols(t):
    return FEAT_R + (["ndvi_fev_mar"] if "ndvi_fev_mar" in t and t.ndvi_fev_mar.notna().mean() > .5 else [])


def _niveau(tr, te):
    """Niveau moyen de chaque province × culture appris sur les seules campagnes d'apprentissage."""
    niv = tr.groupby(["province", "culture"]).rendement_qx_ha.mean()
    glob = tr.groupby("culture").rendement_qx_ha.mean()
    return np.array([niv.get((p, c), glob[c]) for p, c in zip(te.province, te.culture)])


def recolte_evaluer(rend, clim):
    feats = features_saison(clim)
    t = _table_rendement(rend, feats).dropna(subset=list(FENETRES)).reset_index(drop=True)
    cols = _cols(t)
    P = {k: np.full(len(t), np.nan) for k in ["Moyenne de la province (référence)", *_modeles()]}
    for c in sorted(t.campagne.unique()):  # une campagne laissée de côté
        tr, te = t[t.campagne != c].copy(), t[t.campagne == c].copy()
        tr["niveau_province"] = _niveau(tr, tr)
        te["niveau_province"] = _niveau(tr, te)
        P["Moyenne de la province (référence)"][te.index] = te.niveau_province
        for nom, m in _modeles().items():
            m.fit(tr[cols], tr.rendement_qx_ha)
            P[nom][te.index] = np.clip(m.predict(te[cols]), 1, None)
    y = t.rendement_qx_ha.values
    met = []
    for nom, p in P.items():
        met.append(dict(modele=nom, mae_qx_ha=float(np.mean(np.abs(p - y))),
                        erreur_relative_mediane=float(np.median(np.abs(p / y - 1)) * 100),
                        r2=float(1 - np.sum((p - y) ** 2) / np.sum((y - y.mean()) ** 2))))
    met = pd.DataFrame(met).sort_values("mae_qx_ha")
    best = met[met.modele != "Moyenne de la province (référence)"].modele.iloc[0]
    t["prevision_cv"] = P[best]
    # régional : production totale observée vs prévue (campagne par campagne)
    t["prod_prev_t"] = t.prevision_cv * t.superficie_ha / 10
    reg = t.groupby("campagne").agg(reel_Mqx=("production_t", lambda s: s.sum() / 1e5),
                                    prevu_Mqx=("prod_prev_t", lambda s: s.sum() / 1e5)).reset_index()
    return met, best, t, reg, cols


def recolte_modele_final(t, best, cols):
    tr = t.copy()
    tr["niveau_province"] = _niveau(tr, tr)
    m = _modeles()[best].fit(tr[cols], tr.rendement_qx_ha)
    imp = None
    if hasattr(m, "feature_importances_"):
        imp = pd.Series(m.feature_importances_, cols)
    elif hasattr(m, "named_steps"):
        imp = pd.Series(np.abs(m.named_steps["ridge"].coef_), cols)
    return m, (imp / imp.sum() * 100).sort_values(ascending=False) if imp is not None else None


def recolte_prevoir(m, t, rend, clim, cols, campagnes=(2024, 2025, 2026), surface_2026=852555):
    """Rendement prévu par province et culture pour les campagnes sans statistiques publiées."""
    feats = features_saison(clim)
    base = t.copy()
    pc = rend[rend.culture.isin(CULTURES)]
    # surfaces : moyenne des 3 dernières campagnes publiées ; 2026 : recalées sur le total officiel régional
    surf = pc.sort_values("campagne").groupby(["province", "culture"]).tail(3).groupby(["province", "culture"]).superficie_ha.mean()
    rows = []
    for c in campagnes:
        f = feats[feats.campagne == c]
        for (p, cu), s in surf.items():
            x = f[f.province == p]
            if x.empty or x[list(FENETRES)].isna().any(axis=None):
                continue
            r = x.iloc[0].to_dict()
            r.update(province=p, culture=cu, campagne=c, culture_bd=int(cu == "Blé dur"), culture_orge=int(cu == "Orge"),
                     superficie_ha=s)
            rows.append(r)
    f = pd.DataFrame(rows)
    f["niveau_province"] = _niveau(base, f)
    f["rendement_prevu"] = np.clip(m.predict(f[cols]), 1, None)
    k = surface_2026 / f[f.campagne == 2026].superficie_ha.sum() if (f.campagne == 2026).any() else 1
    f.loc[f.campagne == 2026, "superficie_ha"] *= k
    f["production_prevue_t"] = f.rendement_prevu * f.superficie_ha / 10
    f["moyenne_qx_ha"] = f.niveau_province
    f["ratio_moyenne"] = f.rendement_prevu / f.moyenne_qx_ha * 100
    return f[["province", "culture", "campagne", "superficie_ha", "rendement_prevu", "production_prevue_t",
              "moyenne_qx_ha", "ratio_moyenne"]]


def recolte_scenarios(m, t, clim, cols, campagne=2027):
    """Début de saison : la pluie de l'hiver est inconnue. On rejoue chaque hiver passé (2010-2026) et on
    garde trois scénarios : année sèche (10 % les plus sèches), normale (médiane), pluvieuse (90 %)."""
    feats = features_saison(clim)
    feats = feats[feats.campagne.between(2010, 2026)].dropna(subset=list(FENETRES))
    out = []
    for p in t.province.unique():
        for cu in CULTURES:
            fp = feats[feats.province == p].copy()
            if fp.empty:
                continue
            fp["culture_bd"], fp["culture_orge"] = int(cu == "Blé dur"), int(cu == "Orge")
            fp["province"], fp["culture"] = p, cu
            fp["niveau_province"] = _niveau(t, fp)
            y = np.clip(m.predict(fp[cols]), 1, None)
            moy = fp.niveau_province.iloc[0]
            out.append(dict(province=p, culture=cu, campagne=campagne, annee_seche=float(np.quantile(y, .1)),
                            annee_normale=float(np.median(y)), annee_pluvieuse=float(np.quantile(y, .9)),
                            moyenne_qx_ha=float(moy), proba_mauvaise_pct=float((y < .7 * moy).mean() * 100)))
    return pd.DataFrame(out)


# ================================================================================ D. BARRAGE AL MASSIRA
CAP = 2649.54


def barrage_charger():
    b = pd.read_csv(REG / "barrage_al_massira_releves.csv", parse_dates=["date"])
    return b.sort_values("date").reset_index(drop=True)


def _pluie_jour(clim, prov="Settat"):
    """Pluie mensuelle CHIRPS de la province du barrage, répartie uniformément sur les jours du mois."""
    p = clim[clim.province == prov].dropna(subset=["pluie_mm"]).set_index("date").pluie_mm
    j = p.resample("D").ffill()
    j = j.reindex(pd.date_range(p.index.min(), p.index.max() + pd.offsets.MonthEnd(0)), method="ffill")
    return j / j.index.days_in_month


def _variables_intervalle(pj, et0j, d0, d1, v0):
    jours = pd.date_range(d0, d1 - pd.Timedelta(days=1))
    if len(jours) == 0 or jours[-1] > pj.index[-1] or jours[0] < pj.index[0]:
        return None
    pl = pj.reindex(jours)
    # pluie « efficace » : pluie des 60 derniers jours au-delà d'un seuil (sols saturés -> ruissellement)
    p60 = pj.rolling(60, min_periods=1).sum().reindex(jours)
    ruiss = (pl * np.clip((p60 - 60) / 100, 0, 3)).sum()
    surf = (max(v0, 1) / CAP) ** (2 / 3)  # surface du lac ~ volume^(2/3)
    evap = (et0j.reindex(jours).fillna(et0j.mean()) * surf).sum()
    ete = np.isin(jours.month, [5, 6, 7, 8, 9]).sum()
    return dict(pluie=float(pl.sum()), ruissellement=float(ruiss), evaporation=float(evap), jours_ete=int(ete),
                jours=len(jours), niveau=surf * len(jours))


def barrage_calibrer(b, clim):
    """Régression des variations de volume entre deux relevés successifs (Mm³) sur la pluie efficace,
    l'évaporation et les prélèvements d'été (moindres carrés positifs)."""
    from scipy.optimize import nnls
    pj = _pluie_jour(clim)
    e = clim[clim.province == "Settat"].dropna(subset=["et0_mm"]).set_index("date").et0_mm
    et0j = (e.resample("D").ffill() / e.resample("D").ffill().index.days_in_month).reindex(
        pd.date_range(e.index.min(), e.index.max() + pd.offsets.MonthEnd(0)), method="ffill")
    rows = []
    for i in range(len(b) - 1):
        v = _variables_intervalle(pj, et0j, b.date[i], b.date[i + 1], b.volume_Mm3[i])
        if v:
            v.update(d0=b.date[i], d1=b.date[i + 1], v0=b.volume_Mm3[i], dv=b.volume_Mm3[i + 1] - b.volume_Mm3[i])
            rows.append(v)
    t = pd.DataFrame(rows)
    X = np.column_stack([t.ruissellement, -t.evaporation, -t.jours_ete, -t.niveau])
    coef, _ = nnls(X, t.dv.values)
    t["dv_modele"] = X @ coef
    # validation : chaque intervalle prédit par un modèle calibré sans lui
    loo = []
    for i in range(len(t)):
        msk = np.arange(len(t)) != i
        c, _ = nnls(X[msk], t.dv.values[msk])
        loo.append(X[i] @ c)
    t["dv_loo"] = loo
    met = dict(n_intervalles=len(t), mae_modele_Mm3=float(np.mean(np.abs(t.dv_loo - t.dv))),
               mae_persistance_Mm3=float(np.mean(np.abs(t.dv))),
               r2=float(1 - np.sum((t.dv_loo - t.dv) ** 2) / np.sum((t.dv - t.dv.mean()) ** 2)))
    return dict(zip(["k_ruissellement", "k_evaporation", "k_ete", "k_niveau"], coef)), t, met, pj, et0j


def barrage_prevoir(b, coef, pj, et0j, horizons=(7, 30, 90)):
    """Ensemble : depuis le dernier relevé, on rejoue la pluie de chaque année passée (2009-2025) sur la même
    période de l'année, et on fait tourner le bilan hydrique jour par jour."""
    d0, v0 = b.date.iloc[-1], b.volume_Mm3.iloc[-1]
    et0_clim = et0j.groupby(et0j.index.dayofyear).mean()
    scen = []
    for an in range(2010, 2026):
        dec = pd.Timestamp(year=an, month=d0.month, day=d0.day) - d0
        v, traj = v0, []
        for k in range(1, max(horizons) + 1):
            d = d0 + pd.Timedelta(days=k)
            dh = d + dec
            p = float(pj.get(dh, 0.0))
            p60 = float(pj[(pj.index > dh - pd.Timedelta(days=60)) & (pj.index <= dh)].sum())
            surf = (max(v, 1) / CAP) ** (2 / 3)
            dv = (coef["k_ruissellement"] * p * np.clip((p60 - 60) / 100, 0, 3)
                  - coef["k_evaporation"] * float(et0_clim.get(d.dayofyear, 3)) * surf
                  - coef["k_ete"] * (d.month in (5, 6, 7, 8, 9)) - coef["k_niveau"] * surf)
            v = float(np.clip(v + dv, 0, CAP))
            traj.append(v)
        scen.append(traj)
    S = np.array(scen)
    jours = pd.date_range(d0 + pd.Timedelta(days=1), periods=S.shape[1])
    traj = pd.DataFrame({"date": jours, "p10": np.quantile(S, .1, 0), "p50": np.quantile(S, .5, 0), "p90": np.quantile(S, .9, 0)})
    for c in ["p10", "p50", "p90"]:
        traj[c + "_pct"] = traj[c] / CAP * 100
    res = []
    for h in horizons:
        r = traj.iloc[h - 1]
        res.append(dict(horizon_jours=h, date=r.date.strftime("%Y-%m-%d"), bas_pct=r.p10_pct, median_pct=r.p50_pct,
                        haut_pct=r.p90_pct, bas_Mm3=r.p10, median_Mm3=r.p50, haut_Mm3=r.p90,
                        proba_sous_10pct=float((S[:, h - 1] / CAP < .10).mean() * 100),
                        proba_baisse=float((S[:, h - 1] < v0).mean() * 100)))
    return pd.DataFrame(res), traj


def risque_penurie(taux_pct, p10_90j_pct):
    """Règle simple et lisible : on regarde le scénario le plus défavorable à 3 mois (10 % des cas)."""
    x = min(taux_pct, p10_90j_pct)
    if x < 10:
        return "élevé"
    if x < 25:
        return "moyen"
    return "faible"
