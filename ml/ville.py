"""CasaHarvest — volet « ville » : modules 4 (tourisme), 5 (déchets ménagers) et 6 (qualité de l'air).

Module 4 — Tourisme : nuitées mensuelles par destination (Marrakech, Agadir, Fès, Essaouira, Chefchaouen)
    Prévision directe à 1-12 mois (l'horizon est une variable du modèle), sur l'écart au même mois de l'an
    passé ; régression quantile (gradient boosting, quantiles 10 / 50 / 90 %) -> prévision probabiliste.
    + indicateurs de saisonnalité, de capacité d'accueil et de vulnérabilité à la surfréquentation.
Module 5 — Déchets : tonnage hebdomadaire par quartier (Marrakech, Casablanca, Agadir)
    Clustering K-means des profils de quartiers ; XGBoost 1-8 semaines (calendrier, Ramadan, Aïd, nuitées
    touristiques prévues par le module 4) ; optimisation des tournées de collecte (Clarke-Wright + 2-opt).
Module 6 — Qualité de l'air : PM10 et NO2 journaliers par station (Casablanca, Marrakech, Fès, Tanger)
    XGBoost quantile J+1 à J+3, puis calibration conforme PAR STATION : moins une station a de mesures,
    plus son intervalle est large. Test « station virtuelle » : erreur quand on retire le capteur.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.cluster import KMeans
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

VILLE = Path(__file__).resolve().parent.parent / "data" / "ville"
Q = (0.1, 0.5, 0.9)  # intervalle de prévision à 80 %


def _mape(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return float(np.mean(np.abs(p / y - 1)) * 100)


# ====================================================================================== MODULE 4
DESTINATIONS = ["Marrakech", "Agadir", "Fès", "Essaouira", "Chefchaouen"]
RAMADAN_2027 = {"2027-02": 21, "2027-03": 9}
EVENEMENTS_FUTURS = {("Marrakech", 12), ("Marrakech", 4), ("Essaouira", 6), ("Fès", 5), ("Fès", 6), ("Agadir", 12),
                     ("Chefchaouen", 8)}


def tourisme_charger():
    t = pd.read_csv(VILLE / "tourisme_mensuel.csv")
    t["m"] = pd.to_datetime(t.mois)
    return t


def _tourisme_etendre(t, fin):
    """Ajoute les mois futurs (calendrier connu à l'avance : Ramadan, événements) jusqu'à `fin`."""
    rows = []
    for d in DESTINATIONS:
        last = t[t.destination == d].m.max()
        for m in pd.date_range(last + pd.offsets.MonthBegin(1), fin, freq="MS"):
            k = m.strftime("%Y-%m")
            rows.append(dict(mois=k, m=m, destination=d, nuitees=np.nan,
                             jours_ramadan=RAMADAN_2027.get(k, 0),
                             evenement="oui" if (d, m.month) in EVENEMENTS_FUTURS else "", can_2025=0,
                             facteur_covid=1.0))
    return pd.concat([t, pd.DataFrame(rows)], ignore_index=True).sort_values(["destination", "m"])


def _tourisme_table(t, origines, H=12):
    """Table d'apprentissage directe : une ligne par (destination, origine, horizon)."""
    out = []
    for d in DESTINATIONS:
        s = t[t.destination == d].set_index("m").sort_index()
        y = np.log(s.nuitees)
        ycor = y - np.log(s.facteur_covid.clip(.05))  # série corrigée de la chute Covid
        ev = (s.evenement.fillna("") != "").astype(int)
        for o in origines:
            if o not in s.index:
                continue
            idx = [o - pd.DateOffset(months=k) for k in range(3)]
            idx12 = [i - pd.DateOffset(months=12) for i in idx]
            if any(i not in s.index for i in idx12):
                continue
            mom = float(np.mean([ycor[a] - ycor[b] for a, b in zip(idx, idx12)]))
            for h in range(1, H + 1):
                c = o + pd.DateOffset(months=h)
                b = c - pd.DateOffset(months=12)
                if c not in s.index or b not in s.index:
                    continue
                out.append(dict(destination=d, origine=o, cible=c, h=h, mois_cal=c.month, momentum=mom,
                                d_ramadan=s.jours_ramadan[c] - s.jours_ramadan[b], ramadan=s.jours_ramadan[c],
                                d_evenement=ev[c] - ev[b], d_can=s.can_2025[c] - s.can_2025[b],
                                covid_cible=float(s.facteur_covid[c]), covid_base=float(s.facteur_covid[b]),
                                base=float(y[b]), base_cor=float(ycor[b]), y=float(y[c]) if not np.isnan(y[c]) else np.nan))
    df = pd.DataFrame(out)
    df["cible_delta"] = df.y - df.base_cor
    return df


FEAT_T = ["h", "mois_cal", "momentum", "d_ramadan", "ramadan", "d_evenement", "d_can", "dest_code"]


def _tourisme_fit(tab):
    tab = tab[(tab.covid_cible >= 1) & tab.y.notna()].copy()
    tab["dest_code"] = tab.destination.map({d: i for i, d in enumerate(DESTINATIONS)})
    mods = {}
    for q in Q:
        m = HistGradientBoostingRegressor(loss="quantile", quantile=q, max_iter=350, learning_rate=.05,
                                          max_depth=3, min_samples_leaf=15, categorical_features=[7], random_state=0)
        m.fit(tab[FEAT_T], tab.cible_delta)
        mods[q] = m
    return mods


def _tourisme_pred(mods, tab):
    tab = tab.copy()
    tab["dest_code"] = tab.destination.map({d: i for i, d in enumerate(DESTINATIONS)})
    P = np.column_stack([mods[q].predict(tab[FEAT_T]) for q in Q])
    P.sort(axis=1)  # pas de croisement des quantiles
    base = tab.base_cor.values[:, None] + np.log(tab.covid_cible.values)[:, None]
    tab[["bas", "prevision", "haut"]] = np.exp(base + P)
    return tab


def tourisme_backtest(t):
    """Origines oct. 2024 et oct. 2025 : prévision des 12 mois suivants, comparée à la saisonnalité naïve."""
    res = []
    toutes = sorted(t.m.unique())
    tab_all = _tourisme_table(t, toutes)
    for o in [pd.Timestamp("2024-10-01"), pd.Timestamp("2025-10-01")]:
        mods = _tourisme_fit(tab_all[tab_all.cible <= o])
        te = _tourisme_pred(mods, tab_all[(tab_all.origine == o)])
        te["naif_saisonnier"] = np.exp(te.base)
        te["naif_tendance"] = np.exp(te.base_cor + te.momentum) * te.covid_cible
        res.append(te.assign(reel=np.exp(te.y)))
    return pd.concat(res)


def tourisme_marge(bt, alpha=.2):
    """Marge conforme (log) à ajouter aux quantiles 10/90 % pour atteindre ~80 % de couverture."""
    e = np.maximum(np.log(bt.bas / bt.reel), np.log(bt.reel / bt.haut)).values
    n = len(e)
    return float(np.quantile(e, min(1, np.ceil((n + 1) * (1 - alpha)) / n)))


def tourisme_calibrer(bt):
    """Calibration croisée : la marge apprise sur l'origine 2024 est testée sur l'origine 2025."""
    o1, o2 = sorted(bt.origine.unique())
    marge = tourisme_marge(bt[bt.origine == o1])
    b = bt.copy()
    b["bas_c"], b["haut_c"] = b.bas * np.exp(-marge), b.haut * np.exp(marge)
    t2 = b[b.origine == o2]
    return marge, float(((t2.reel >= t2.bas).values & (t2.reel <= t2.haut).values).mean() * 100), \
        float(((t2.reel >= t2.bas_c) & (t2.reel <= t2.haut_c)).mean() * 100)


def tourisme_metriques(bt):
    out = []
    for d, g in bt.groupby("destination"):
        out.append(dict(destination=d, mape_modele=_mape(g.reel, g.prevision),
                        mape_naif_saisonnier=_mape(g.reel, g.naif_saisonnier),
                        mape_naif_tendance=_mape(g.reel, g.naif_tendance),
                        couverture_80=float(((g.reel >= g.bas) & (g.reel <= g.haut)).mean() * 100)))
    g = bt
    out.append(dict(destination="Toutes", mape_modele=_mape(g.reel, g.prevision),
                    mape_naif_saisonnier=_mape(g.reel, g.naif_saisonnier),
                    mape_naif_tendance=_mape(g.reel, g.naif_tendance),
                    couverture_80=float(((g.reel >= g.bas) & (g.reel <= g.haut)).mean() * 100)))
    par_h = bt.groupby("h").apply(lambda g: pd.Series({"mape_modele": _mape(g.reel, g.prevision),
                                                       "mape_naif_saisonnier": _mape(g.reel, g.naif_saisonnier)}),
                                  include_groups=False).reset_index()
    return pd.DataFrame(out), par_h


def tourisme_prevoir(t, H=12, marge=0.0):
    origine = t.m.max()
    te = _tourisme_etendre(t, origine + pd.DateOffset(months=H))
    tab = _tourisme_table(te, sorted(te.m.unique()))
    mods = _tourisme_fit(tab[tab.cible <= origine])
    f = _tourisme_pred(mods, tab[tab.origine == origine])
    f["bas"], f["haut"] = f.bas * np.exp(-marge), f.haut * np.exp(marge)
    return f[["destination", "cible", "h", "bas", "prevision", "haut"]].rename(columns={"cible": "mois"})


def tourisme_vulnerabilite(t, prev):
    """Indicateurs de surfréquentation sur les 12 derniers mois observés + les 12 mois prévus."""
    out = []
    for d in DESTINATIONS:
        s = t[t.destination == d].sort_values("m").tail(12)
        lits, pop = s.capacite_lits.iloc[-1], s.population.iloc[-1]
        j = s.m.dt.days_in_month.values
        occ = s.nuitees.values / (lits * j) * 100
        p = prev[prev.destination == d].sort_values("mois")
        occ_p = p.prevision.values / (lits * p.mois.dt.days_in_month.values) * 100
        occ_h = p.haut.values / (lits * p.mois.dt.days_in_month.values) * 100
        marches = [c for c in s.columns if c.startswith("nuitees_")]
        parts = s[marches].sum() / s[marches].sum().sum()
        out.append(dict(destination=d, nuitees_12m=float(s.nuitees.sum()), nuitees_prevues_12m=float(p.prevision.sum()),
                        croissance_prevue_pct=float(p.prevision.sum() / s.nuitees.sum() * 100 - 100),
                        occupation_moy_pct=float(occ.mean()), occupation_pic_pct=float(occ.max()),
                        occupation_pic_prevue_pct=float(occ_p.max()),
                        mois_sature_prevus=int((occ_h >= 85).sum()),
                        ratio_pic_creux=float(s.nuitees.max() / s.nuitees.min()),
                        touristes_pour_100_hab=float((s.nuitees / j).max() / pop * 100),
                        nuitees_par_hab=float(s.nuitees.sum() / pop),
                        premier_marche=parts.idxmax().replace("nuitees_", ""), part_premier_marche=float(parts.max() * 100)))
    v = pd.DataFrame(out)
    # score 0-100 : moyenne de 4 composantes normalisées (min-max) — occupation au pic, intensité,
    # saisonnalité, dépendance au premier marché
    comp = {"occupation_pic_prevue_pct": .35, "touristes_pour_100_hab": .30, "ratio_pic_creux": .2,
            "part_premier_marche": .15}
    sc = sum(w * (v[c] - v[c].min()) / (v[c].max() - v[c].min() + 1e-9) for c, w in comp.items())
    v["score_vulnerabilite"] = (sc * 100).round(0)
    v["niveau"] = pd.cut(v.score_vulnerabilite, [-1, 33, 66, 101], labels=["faible", "modéré", "élevé"]).astype(str)
    return v.sort_values("score_vulnerabilite", ascending=False)


# ====================================================================================== MODULE 5
def dechets_charger():
    q = pd.read_csv(VILLE / "dechets_quartiers.csv")
    d = pd.read_csv(VILLE / "dechets_hebdo.csv", parse_dates=["semaine"])
    return q, d


def dechets_profils(q, d):
    """Profil de chaque quartier (2023-2026) puis K-means -> typologie."""
    d = d[d.semaine >= "2023-01-01"].merge(q, on=["ville", "quartier"])
    rows = []
    for (v, n), g in d.groupby(["ville", "quartier"]):
        norm = g[(g.ramadan == 0) & (g.aid_al_adha == 0) & (g.semaine_avant_aid == 0)]
        base = norm.tonnes.median()
        rows.append(dict(ville=v, quartier=n, kg_hab_j=g.tonnes.mean() * 1000 / 7 / g.population.iloc[0],
                         part_touristique=float((g.nuitees_quartier * 1.6 / 1000).sum() / g.tonnes.sum() * 100),
                         effet_ete=float(norm[norm.ete == 1].tonnes.mean() / norm[norm.ete == 0].tonnes.mean() * 100 - 100),
                         effet_ramadan=float(g[g.ramadan == 1].tonnes.mean() / base * 100 - 100),
                         effet_aid=float(g[g.aid_al_adha == 1].tonnes.mean() / base * 100 - 100),
                         variabilite=float(norm.tonnes.std() / norm.tonnes.mean() * 100),
                         tonnes_jour=float(g.tonnes.tail(52).mean() / 7)))
    p = pd.DataFrame(rows)
    X = StandardScaler().fit_transform(p[["kg_hab_j", "part_touristique", "effet_ete", "effet_aid", "variabilite"]])
    best = max(range(3, 6), key=lambda k: silhouette_score(X, KMeans(k, n_init=20, random_state=0).fit_predict(X)))
    km = KMeans(best, n_init=20, random_state=0).fit(X)
    p["cluster"] = km.labels_
    # nommer les groupes d'après leurs moyennes (attribution gloutonne, un nom par groupe)
    c = p.groupby("cluster")[["kg_hab_j", "part_touristique", "effet_aid", "effet_ete"]].mean()
    regles = [("part_touristique", "Pôles touristiques et hôteliers"),
              ("part_touristique", "Quartiers aisés et mixtes (part touristique notable)"),
              ("effet_ete", "Quartiers à forte saison estivale"),
              ("effet_aid", "Quartiers populaires denses (pic de l'Aïd)")]
    noms, reste = {}, list(c.index)
    for col, nom in regles:
        if not reste:
            break
        k = c.loc[reste, col].idxmax()
        noms[k] = nom
        reste.remove(k)
    for k in reste:
        noms[k] = "Quartiers résidentiels"
    p["typologie"] = p.cluster.map(noms)
    sil = silhouette_score(X, km.labels_)
    return p, best, float(sil)


FEAT_D = ["h", "y_o", "y_o4", "y_52", "ramadan", "aid_al_adha", "semaine_avant_aid", "ete", "confinement",
          "ram_o", "aid_o", "log_nuitees", "sin_s", "cos_s", "log_pop", "part_lits", "hab_code", "ville_code"]
HABITATS = ["Médina dense", "Habitat économique", "Moyen standing", "Villas / résidentiel", "Zone touristique & hôtelière"]
VILLES_D = ["Marrakech", "Casablanca", "Agadir"]


def _dechets_table(q, d, origines, H=8):
    d = d.merge(q, on=["ville", "quartier"]).sort_values(["ville", "quartier", "semaine"])
    out = []
    for (v, n), g in d.groupby(["ville", "quartier"]):
        g = g.reset_index(drop=True)
        y = np.log(g.tonnes.values)
        pos = {s: i for i, s in enumerate(g.semaine)}
        for o in origines:
            i = pos.get(o)
            if i is None or i < 56:
                continue
            for h in range(1, H + 1):
                j = i + h
                if j >= len(g):
                    break
                r = g.iloc[j]
                out.append(dict(ville=v, quartier=n, origine=o, semaine=r.semaine, h=h, y=y[j] if not np.isnan(y[j]) else np.nan,
                                y_o=y[i], y_o4=y[i - 3:i + 1].mean(), y_52=y[j - 52],
                                ramadan=r.ramadan, aid_al_adha=r.aid_al_adha, semaine_avant_aid=r.semaine_avant_aid,
                                ete=r.ete, confinement=r.confinement, ram_o=g.ramadan[i], aid_o=g.aid_al_adha[i],
                                log_nuitees=np.log1p(r.nuitees_quartier), sin_s=np.sin(2 * np.pi * r.semaine.dayofyear / 365),
                                cos_s=np.cos(2 * np.pi * r.semaine.dayofyear / 365), log_pop=np.log(r.population),
                                part_lits=r.part_lits, hab_code=HABITATS.index(r.habitat), ville_code=VILLES_D.index(v)))
    return pd.DataFrame(out)


def _dechets_modele():
    return xgb.XGBRegressor(n_estimators=500, learning_rate=.04, max_depth=4, subsample=.8, colsample_bytree=.8,
                            min_child_weight=5, reg_lambda=2, random_state=0, n_jobs=4)


def dechets_backtest(q, d):
    sem = sorted(d.semaine.unique())
    coupe = pd.Timestamp("2025-11-19")
    tr = _dechets_table(q, d, [s for s in sem if s <= coupe - pd.Timedelta(weeks=8)])
    te = _dechets_table(q, d, [s for s in sem if coupe <= s])
    m = _dechets_modele().fit(tr[FEAT_D], tr.y - tr.y_o)
    te["prevision"] = np.exp(te.y_o + m.predict(te[FEAT_D]))
    te["reel"] = np.exp(te.y)
    te["naif_persistance"] = np.exp(te.y_o)
    te["naif_annee_passee"] = np.exp(te.y_52)
    te = te.dropna(subset=["reel"])
    met = pd.DataFrame([dict(ville=v, mape_modele=_mape(g.reel, g.prevision),
                             mape_persistance=_mape(g.reel, g.naif_persistance),
                             mape_annee_passee=_mape(g.reel, g.naif_annee_passee))
                        for v, g in [*te.groupby("ville"), ("Toutes", te)]])
    # erreur pendant les semaines « exceptionnelles » (Ramadan, Aïd) — là où la prévision compte le plus
    exc = te[(te.ramadan == 1) | (te.aid_al_adha == 1) | (te.semaine_avant_aid == 1)]
    met_exc = dict(mape_modele=_mape(exc.reel, exc.prevision), mape_persistance=_mape(exc.reel, exc.naif_persistance),
                   n=len(exc))
    imp = pd.Series(m.feature_importances_, FEAT_D).sort_values(ascending=False)
    return te, met, met_exc, imp


def dechets_prevoir(q, d, nuitees_futures=None, H=8):
    """Prévision des 8 prochaines semaines ; les nuitées futures viennent du module 4 (tourisme)."""
    sem = sorted(d.semaine.unique())
    origine = sem[-1]
    futur = []
    for (v, n), g in d.groupby(["ville", "quartier"]):
        last = g.sort_values("semaine").iloc[-1]
        for h in range(1, H + 1):
            s = origine + pd.Timedelta(weeks=h)
            nq = last.nuitees_quartier
            if nuitees_futures is not None:
                ref = g[g.semaine == s - pd.Timedelta(weeks=52)]
                if len(ref):
                    nq = float(ref.nuitees_quartier.iloc[0]) * nuitees_futures.get((v, s.strftime("%Y-%m")), 1.0)
            futur.append(dict(semaine=s, ville=v, quartier=n, tonnes=np.nan, nuitees_quartier=nq, ramadan=0,
                              aid_al_adha=0, semaine_avant_aid=0, ete=int(s.month in (7, 8)), confinement=0))
    dd = pd.concat([d, pd.DataFrame(futur)], ignore_index=True)
    tr = _dechets_table(q, d, [s for s in sem if s <= origine - pd.Timedelta(weeks=8)])
    m = _dechets_modele().fit(tr[FEAT_D], tr.y - tr.y_o)
    te = _dechets_table(q, dd, [origine], H)
    te["prevision"] = np.exp(te.y_o + m.predict(te[FEAT_D]))
    # intervalle à 80 % : quantiles empiriques des erreurs du backtest (par horizon) — ajoutés par l'appelant
    return te[["ville", "quartier", "semaine", "h", "prevision"]], m


def dechets_scenario(q, d, m, scenario):
    """Tonnage journalier par quartier pour un scénario (semaine type, haute saison touristique, Aïd al-Adha)."""
    sem = sorted(d.semaine.unique())
    origine = sem[-1]
    base = _dechets_table(q, d, [origine - pd.Timedelta(weeks=1)], 1)
    base = base.copy()
    if scenario == "aid":
        base[["aid_al_adha"]] = 1
    elif scenario == "haute_saison":
        # nuitées du mois le plus chargé de l'année écoulée, été
        pic = d[d.semaine >= origine - pd.Timedelta(weeks=52)].groupby(["ville", "quartier"]).nuitees_quartier.max()
        base["log_nuitees"] = np.log1p(base.set_index(["ville", "quartier"]).index.map(pic).values.astype(float))
        base["ete"] = 1
        base["sin_s"], base["cos_s"] = np.sin(2 * np.pi * 210 / 365), np.cos(2 * np.pi * 210 / 365)
    base["tonnes_jour"] = np.exp(base.y_o + m.predict(base[FEAT_D])) / 7
    return base[["ville", "quartier", "tonnes_jour"]]


# --------------------------------------------------------------------------- tournées de collecte
DEPOTS = {"Marrakech": ("CEV de M'Nabha", 31.560, -8.110), "Casablanca": ("Décharge de Médiouna", 33.470, -7.520),
          "Agadir": ("CEV de Tamelast", 30.490, -9.520)}
CAPACITE_T = 10.0          # benne tasseuse ~10 t utiles
ROTATIONS_JOUR = 3         # tournées par camion et par jour
DETOUR = 1.35              # distance routière / distance à vol d'oiseau


def _km(a, b):
    la1, lo1, la2, lo2 = map(np.radians, (a[0], a[1], b[0], b[1]))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(h)) * DETOUR


def points_collecte(q):
    """Points de regroupement : ~1 point pour 12 000 habitants, répartis autour du centre du quartier."""
    r = np.random.default_rng(7)
    pts = []
    for _, x in q.iterrows():
        k = max(2, int(np.ceil(x.population / 12000)))
        rayon = .003 + .0016 * np.sqrt(k)
        for i in range(k):
            a = 2 * np.pi * i / k + r.uniform(0, .5)
            d = rayon * (0 if k == 1 else r.uniform(.5, 1))
            pts.append(dict(ville=x.ville, quartier=x.quartier, point=f"{x.quartier} #{i + 1}",
                            lat=x.lat + d * np.sin(a), lon=x.lon + d * np.cos(a) / np.cos(np.radians(x.lat)), part=1 / k))
    return pd.DataFrame(pts)


def _deux_opt(route, D):
    best = route[:]
    amelio = True
    while amelio:
        amelio = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                if D[best[i - 1], best[j]] + D[best[i], best[j + 1]] < D[best[i - 1], best[i]] + D[best[j], best[j + 1]] - 1e-9:
                    best[i:j + 1] = best[i:j + 1][::-1]
                    amelio = True
    return best


def optimiser_tournees(ville, pts, tonnes):
    """Tournées d'une journée. Charges pleines : allers-retours directs ; reliquats regroupés par la
    méthode des économies de Clarke-Wright (capacité du camion), puis chaque tournée améliorée par 2-opt.
    Référence « sans optimisation » : chaque point est vidé séparément (un aller-retour par chargement)."""
    p = pts[pts.ville == ville].merge(tonnes, on=["ville", "quartier"]).reset_index(drop=True)
    p["t"] = p.tonnes_jour * p.part
    dep = DEPOTS[ville]
    coords = [(dep[1], dep[2])] + list(zip(p.lat, p.lon))
    n = len(coords)
    D = np.array([[_km(coords[i], coords[j]) for j in range(n)] for i in range(n)])
    pleins = np.floor(p.t / CAPACITE_T).astype(int).values
    reste = p.t.values - pleins * CAPACITE_T
    km_directs = float(sum(2 * D[0, i + 1] * pleins[i] for i in range(len(p))))
    # Clarke-Wright sur les reliquats
    routes = {i: [i] for i in range(len(p)) if reste[i] > .05}
    charge = {i: reste[i] for i in routes}
    ou = {i: i for i in routes}
    eco = sorted(((D[0, i + 1] + D[0, j + 1] - D[i + 1, j + 1], i, j) for i in routes for j in routes if i < j), reverse=True)
    for s, i, j in eco:
        ri, rj = ou[i], ou[j]
        if ri == rj or charge[ri] + charge[rj] > CAPACITE_T:
            continue
        A, B = routes[ri], routes[rj]
        if A[-1] == i and B[0] == j:
            new = A + B
        elif A[0] == i and B[-1] == j:
            new = B + A
        elif A[-1] == i and B[-1] == j:
            new = A + B[::-1]
        elif A[0] == i and B[0] == j:
            new = A[::-1] + B
        else:
            continue
        routes[ri] = new
        charge[ri] += charge[rj]
        del routes[rj], charge[rj]
        for k in new:
            ou[k] = ri
    tournees, km_tournees = [], 0.0
    for r, seq in routes.items():
        idx = _deux_opt([0] + [k + 1 for k in seq] + [0], D)
        km = float(sum(D[idx[a], idx[a + 1]] for a in range(len(idx) - 1)))
        km_tournees += km
        tournees.append(dict(points=[p.point[k - 1] for k in idx[1:-1]], charge_t=float(charge[r]), km=km,
                             trace=[list(coords[k]) for k in idx]))
    km_naif = float(sum(2 * D[0, i + 1] * np.ceil(p.t[i] / CAPACITE_T) for i in range(len(p))))
    voyages = int(pleins.sum() + len(tournees))
    voyages_naif = int(np.ceil(p.t / CAPACITE_T).sum())
    return dict(ville=ville, depot=dict(nom=dep[0], lat=dep[1], lon=dep[2]), tonnes_jour=float(p.t.sum()),
                voyages=voyages, voyages_naif=voyages_naif, camions=int(np.ceil(voyages / ROTATIONS_JOUR)),
                camions_naif=int(np.ceil(voyages_naif / ROTATIONS_JOUR)), km=km_directs + km_tournees, km_naif=km_naif,
                gain_km_pct=(1 - (km_directs + km_tournees) / km_naif) * 100, tournees=tournees,
                points=[dict(point=r.point, quartier=r.quartier, lat=r.lat, lon=r.lon, tonnes=r.t) for r in p.itertuples()])


# ====================================================================================== MODULE 6
def air_charger():
    d = pd.read_csv(VILLE / "air_journalier.csv", parse_dates=["date"])
    st = pd.read_csv(VILLE / "air_stations.csv")
    return d, st


POLLUANTS = ["pm10", "no2"]
TYPES = ["trafic", "industrielle", "fond urbain"]
VILLES_A = ["Casablanca", "Marrakech", "Fès", "Tanger"]
SEUILS = {"pm10": [(20, "très bon"), (40, "bon"), (50, "moyen"), (100, "médiocre"), (150, "mauvais"), (1e9, "très mauvais")],
          "no2": [(40, "très bon"), (90, "bon"), (120, "moyen"), (230, "médiocre"), (340, "mauvais"), (1e9, "très mauvais")]}


def classe_air(pol, v):
    if v is None or np.isnan(v):
        return None
    return next(c for s, c in SEUILS[pol] if v < s)


def _air_table(d, pol, H=3, sans_capteur=False):
    """Une ligne par (station, jour d'origine, horizon). Variables : météo PRÉVUE du jour cible, calendrier,
    dernières mesures de la station (sauf en mode « sans capteur ») et moyenne des autres stations de la ville."""
    d = d.sort_values(["station", "date"]).copy()
    d["ly"] = np.log(d[pol])
    voisins = d.groupby(["ville", "date"]).ly.agg(["sum", "count"]).rename(columns={"sum": "s", "count": "c"})
    d = d.join(voisins, on=["ville", "date"])
    d["voisins"] = (d.s - d.ly.fillna(0)) / (d.c - d.ly.notna().astype(int)).replace(0, np.nan)
    tabs = []
    for st, g in d.groupby("station"):
        g = g.set_index("date")
        lag = pd.DataFrame({"y_o": g.ly, "y_o1": g.ly.shift(1), "y_7": g.ly.rolling(7, min_periods=3).mean(),
                            "vois_o": g.voisins, "poussiere_o": g.episode_poussiere})
        for h in range(1, H + 1):
            t = g[["ville", "type", "temp_moy_C", "temp_max_C", "pluie_mm", "vent_m_s", "humidite_pct",
                   "episode_poussiere", "indice_trafic", "week_end", "ramadan", "ly"]].copy()
            t = t.join(lag.shift(h))
            t["h"] = h
            t["station"] = st
            t["origine"] = t.index - pd.Timedelta(days=h)
            tabs.append(t.reset_index())
    tab = pd.concat(tabs, ignore_index=True)
    tab["mois_sin"] = np.sin(2 * np.pi * tab.date.dt.dayofyear / 365)
    tab["mois_cos"] = np.cos(2 * np.pi * tab.date.dt.dayofyear / 365)
    tab["type_code"] = tab.type.map({t: i for i, t in enumerate(TYPES)})
    tab["ville_code"] = tab.ville.map({v: i for i, v in enumerate(VILLES_A)})
    if sans_capteur:
        tab[["y_o", "y_o1", "y_7"]] = np.nan
    return tab


FEAT_A = ["h", "temp_moy_C", "temp_max_C", "pluie_mm", "vent_m_s", "humidite_pct", "episode_poussiere",
          "indice_trafic", "week_end", "ramadan", "y_o", "y_o1", "y_7", "vois_o", "poussiere_o", "mois_sin",
          "mois_cos", "type_code", "ville_code"]


def _air_modele():
    return xgb.XGBRegressor(objective="reg:quantileerror", quantile_alpha=np.array(Q), n_estimators=400,
                            learning_rate=.05, max_depth=5, subsample=.8, colsample_bytree=.8, min_child_weight=10,
                            random_state=0, n_jobs=4)


def _conforme(cal, alpha=.2):
    """Calibration conforme (CQR) par station : marge ajoutée à l'intervalle pour garantir ~80 % de
    couverture. Quantile d'ordre ceil((n+1)(1-a))/n : une station avec peu de mesures reçoit une marge plus
    large (moins de preuves -> plus de prudence). Stations à moins de 20 points : marge de la ville x 1,5."""
    out = {}
    for st, g in cal.groupby("station"):
        e = np.maximum(g.lo - g.ly, g.ly - g.hi).values
        n = len(e)
        if n < 20:
            out[st] = (None, n)
            continue
        k = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
        out[st] = (float(np.quantile(e, k)), n)
    return out


def air_evaluer(d, pol):
    tab = _air_table(d, pol).dropna(subset=["ly"])
    tr = tab[tab.date <= "2024-12-31"]
    ca = tab[(tab.date > "2024-12-31") & (tab.date <= "2025-10-31")].copy()
    te = tab[tab.date > "2025-10-31"].copy()
    m = _air_modele().fit(tr[FEAT_A], tr.ly)
    for df in (ca, te):
        P = np.sort(m.predict(df[FEAT_A]), axis=1)
        df["lo"], df["med"], df["hi"] = P[:, 0], P[:, 1], P[:, 2]
    marges = _conforme(ca)
    villes = ca.groupby("ville").apply(lambda g: float(np.quantile(np.maximum(g.lo - g.ly, g.ly - g.hi), .8)),
                                       include_groups=False)
    te["marge"] = [marges[s][0] if marges.get(s, (None,))[0] is not None else villes[v] * 1.5
                   for s, v in zip(te.station, te.ville)]
    te["lo_c"], te["hi_c"] = te.lo - te.marge, te.hi + te.marge
    res = []
    for st, g in te.groupby("station"):
        y = np.exp(g.ly)
        res.append(dict(polluant=pol, station=st, ville=g.ville.iloc[0], type=g.type.iloc[0],
                        n_test=len(g), n_calibration=marges.get(st, (None, 0))[1],
                        disponibilite_pct=float(d[d.station == st][pol].notna().mean() * 100),
                        mae_modele=float(np.mean(np.abs(np.exp(g.med) - y))),
                        mae_modele_j1=float(np.mean(np.abs(np.exp(g.med[g.h == 1]) - y[g.h == 1]))),
                        mae_persistance=float(np.nanmean(np.abs(np.exp(g.y_o) - y))),
                        mae_persistance_j1=float(np.nanmean(np.abs(np.exp(g.y_o[g.h == 1]) - y[g.h == 1]))),
                        couverture_brute=float(((g.ly >= g.lo) & (g.ly <= g.hi)).mean() * 100),
                        couverture_calibree=float(((g.ly >= g.lo_c) & (g.ly <= g.hi_c)).mean() * 100),
                        largeur_relative_pct=float(np.mean(np.exp(g.hi_c) - np.exp(g.lo_c)) / np.mean(y) * 100)))
    imp = pd.Series(m.feature_importances_, FEAT_A).sort_values(ascending=False)
    return pd.DataFrame(res), imp


def air_sans_capteur(d, pol):
    """Station virtuelle : on retire une station de l'apprentissage et ses propres mesures ; on la prédit
    à partir de la météo, du type de site et des autres stations de la ville."""
    tab = _air_table(d, pol, H=1, sans_capteur=True).dropna(subset=["ly"])
    out = []
    for st, g in tab.groupby("station"):
        if g.vois_o.notna().mean() < .3:
            continue
        tr = tab[(tab.station != st) & (tab.date <= "2025-10-31")]
        te = g[g.date > "2025-10-31"]
        if len(te) < 20:
            continue
        m = _air_modele().fit(tr[FEAT_A], tr.ly)
        P = np.sort(m.predict(te[FEAT_A]), axis=1)
        y = np.exp(te.ly)
        out.append(dict(polluant=pol, station=st, mae_sans_capteur=float(np.mean(np.abs(np.exp(P[:, 1]) - y))),
                        largeur_sans_capteur_pct=float(np.mean(np.exp(P[:, 2]) - np.exp(P[:, 0])) / np.mean(y) * 100),
                        couverture_sans_capteur=float(((te.ly >= P[:, 0]) & (te.ly <= P[:, 2])).mean() * 100)))
    return pd.DataFrame(out)


def air_prevoir(d, pol):
    """Prévision J+1 à J+3 depuis la dernière mesure, intervalles calibrés par station."""
    tab = _air_table(d, pol)
    der = d[d[pol].notna()].date.max()
    hist = tab.dropna(subset=["ly"])
    tr = hist[hist.date <= der - pd.Timedelta(days=300)]
    ca = hist[hist.date > der - pd.Timedelta(days=300)].copy()
    m = _air_modele().fit(tr[FEAT_A], tr.ly)
    P = np.sort(m.predict(ca[FEAT_A]), axis=1)
    ca["lo"], ca["hi"] = P[:, 0], P[:, 2]
    marges = _conforme(ca)
    villes = ca.groupby("ville").apply(lambda g: float(np.quantile(np.maximum(g.lo - g.ly, g.ly - g.hi), .8)),
                                       include_groups=False)
    m = _air_modele().fit(hist[FEAT_A], hist.ly)  # modèle final sur tout l'historique
    f = tab[(tab.origine == der)].copy()
    P = np.sort(m.predict(f[FEAT_A]), axis=1)
    f["marge"] = [marges[s][0] if marges.get(s, (None,))[0] is not None else villes[v] * 1.5
                  for s, v in zip(f.station, f.ville)]
    f["prevision"] = np.exp(P[:, 1])
    f["bas"], f["haut"] = np.exp(P[:, 0] - f.marge), np.exp(P[:, 2] + f.marge)
    f["sans_mesure_recente"] = f.y_o.isna()
    f["polluant"] = pol
    f["classe"] = [classe_air(pol, v) for v in f.prevision]
    f["n_calibration"] = [marges.get(s, (None, 0))[1] for s in f.station]
    return f[["polluant", "station", "ville", "type", "date", "h", "bas", "prevision", "haut", "classe",
              "sans_mesure_recente", "n_calibration", "episode_poussiere", "vent_m_s", "pluie_mm"]], der
