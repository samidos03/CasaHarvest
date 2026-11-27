"""Modèle de prévision des prix de gros hebdomadaires (DH/kg) par produit — marché de gros de Casablanca.

Données : prix de gros hebdomadaires de Casablanca (prix_gros_hebdo_fusion.csv, 2024 -> 2026).

Modèle retenu, « naïf saisonnier amorti » :
    prix(t+h) = dernier prix connu × exp( ALPHA × [ S(semaine t+h) − S(semaine t) ] )
  où S est le profil saisonnier du produit (régression du log-prix sur une tendance linéaire
  + 2 harmoniques de la semaine de l'année), et ALPHA = 0,5 amortit la saisonnalité
  (estimée sur seulement ~2,5 ans).
Ce modèle a été comparé (backtest à origines glissantes) au modèle naïf (dernier prix)
et à un gradient boosting (HistGradientBoosting sur retards + saison) : voir evaluer().

Usage :
  python -I modele_prevision.py              -> évaluation des 3 méthodes
  python -I modele_prevision.py Tomate 8     -> prévision sur 8 semaines
"""
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

HERE = os.path.dirname(os.path.abspath(__file__))
F_DATA = "prix_gros_hebdo_fusion.csv"
MIN_SEMAINES = 30   # produits avec assez de relevés pour être modélisés
K_HARM = 2          # nombre d'harmoniques du profil saisonnier
ALPHA = 0.5         # amortissement de la saisonnalité
Z80 = 1.2816        # intervalle de prévision à 80 %


# ---------------------------------------------------------------- données
def charger_series():
    # relevés fusionnés presse française + arabe (construire_donnees_enrichies.py)
    d = pd.read_csv(os.path.join(HERE, F_DATA)).rename(columns={"semaine": "date_bulletin"})
    d = d[(d.marche == "Casablanca") & (d.date_bulletin >= "2024-01-01") & d.prix_moyen_DH_kg.notna()
          & (d.type_valeur != "valeur")]  # prix cités seuls : peu fiables (écart médian 31 % au bulletin)
    w = d.pivot_table(index="date_bulletin", columns="produit", values="prix_moyen_DH_kg")
    w.index = pd.to_datetime(w.index)
    start = w.index.min() - pd.Timedelta(days=(w.index.min().weekday() - 2) % 7)
    w = w.reindex(pd.date_range(start, w.index.max(), freq="W-WED"))
    w = w.loc[:, w.notna().sum() >= MIN_SEMAINES]
    observe = w.notna()
    # semaines manquantes : interpolation linéaire en log, uniquement entre deux relevés
    w = np.exp(np.log(w).interpolate(limit_area="inside"))
    return w, observe


def _semaine(dates):
    return np.asarray(pd.DatetimeIndex(dates).isocalendar().week, float)


def _harm(woy):
    a = 2 * np.pi * np.asarray(woy, float) / 52.18
    return np.column_stack([f(k * a) for k in range(1, K_HARM + 1) for f in (np.sin, np.cos)])


# ---------------------------------------------------------------- modèle retenu
def profil_saisonnier(w, observe, produit, fin=None):
    """Ajuste log p = a + b·t + harmoniques(semaine) sur les semaines observées ; renvoie S(semaine)."""
    s = np.log(w[produit])
    m = observe[produit] & s.notna()
    if fin is not None:
        m &= s.index <= fin
    s = s[m]
    if len(s) < 30:
        return lambda woy: np.zeros(len(np.atleast_1d(woy)))
    t = (s.index - w.index[0]).days / 365.25
    X = np.column_stack([np.ones(len(s)), t, _harm(_semaine(s.index))])
    beta = np.linalg.lstsq(X, s.values, rcond=None)[0]
    return lambda woy: _harm(woy) @ beta[2:]


def _releves(w, observe, produit, fin=None):
    """Prix réellement relevés jusqu'à `fin` (sans les semaines interpolées, qui utilisent des relevés
    postérieurs : les prendre comme point de départ serait une fuite de données dans le backtest)."""
    s = w[produit].where(observe[produit])
    return (s if fin is None else s.loc[:fin]).dropna()


def prevoir_saisonnier(w, observe, produit, h, fin=None, alpha=ALPHA):
    s = _releves(w, observe, produit, fin)
    last, d0 = s.iloc[-1], s.index[-1]
    S = profil_saisonnier(w, observe, produit, fin)
    dates = pd.date_range(d0 + pd.Timedelta(weeks=1), periods=h, freq="W-WED")
    ds = S(_semaine(dates)) - S(_semaine([d0]))[0]
    return pd.Series(last * np.exp(alpha * ds), index=dates), d0


# ---------------------------------------------------------------- méthodes de comparaison
def prevoir_naif(w, observe, produit, h, fin=None):
    s = _releves(w, observe, produit, fin)
    dates = pd.date_range(s.index[-1] + pd.Timedelta(weeks=1), periods=h, freq="W-WED")
    return pd.Series(s.iloc[-1], index=dates), s.index[-1]


def _gb_features(hist, woy, k):
    l1 = hist[-1]
    a = 2 * np.pi * woy / 52.18
    return [l1 - hist[-2], l1 - hist[-4], l1 - np.mean(hist[-8:]), l1, np.sin(a), np.cos(a), k]


def entrainer_gb(w, observe, fin=None):
    X, y = [], []
    for k, p in enumerate(w.columns):
        s = np.log(w[p])
        for i in range(8, len(s)):
            if fin is not None and w.index[i] > fin:
                break
            hist = s.iloc[i - 8:i].values
            if np.isnan(hist).any() or not observe[p].iloc[i]:
                continue
            X.append(_gb_features(hist, w.index[i].isocalendar().week, k))
            y.append(s.iloc[i] - hist[-1])
    m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_depth=3, min_samples_leaf=15,
                                      l2_regularization=1.0, categorical_features=[6], random_state=0)
    return m.fit(np.array(X, float), np.array(y))


def prevoir_gb(m, w, observe, produit, h, fin=None):
    k = list(w.columns).index(produit)
    r = _releves(w, observe, produit, fin)
    s = np.log(w[produit].loc[:r.index[-1]]).dropna()  # interpolation entre relevés <= dernier relevé
    hist = list(s.values[-8:])
    dates = pd.date_range(s.index[-1] + pd.Timedelta(weeks=1), periods=h, freq="W-WED")
    for dt in dates:
        hist.append(hist[-1] + m.predict(np.array([_gb_features(np.array(hist), dt.isocalendar().week, k)]))[0])
    return pd.Series(np.exp(hist[8:]), index=dates), s.index[-1]


# ---------------------------------------------------------------- évaluation
def evaluer(w, observe, n_test=40, h=8, avec_gb=True):
    """Backtest à origines glissantes (une origine toutes les 2 semaines sur les n_test dernières semaines).
    Erreur = |prévision − réel| / réel, uniquement sur des semaines réellement observées."""
    rows = []
    for o in w.index[-n_test - h:-h:2]:
        gb = entrainer_gb(w, observe, fin=o) if avec_gb else None
        for p in w.columns:
            if w[p].loc[:o].dropna().shape[0] < 8:
                continue
            prev = {"Naïf (dernier prix)": prevoir_naif(w, observe, p, h, o)[0],
                    "Saisonnier amorti (retenu)": prevoir_saisonnier(w, observe, p, h, o)[0]}
            if gb is not None:
                prev["Gradient boosting"] = prevoir_gb(gb, w, observe, p, h, o)[0]
            for j, dt in enumerate(prev["Naïf (dernier prix)"].index, 1):
                if dt not in w.index or not observe[p].get(dt, False):
                    continue
                vrai = w[p].loc[dt]
                for meth, f in prev.items():
                    rows.append({"produit": p, "horizon": j, "methode": meth,
                                 "erreur_pct": abs(f[dt] - vrai) / vrai * 100,
                                 "log_err": np.log(f[dt] / vrai)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- interface
class Prevision:
    """Chargé une fois (application Streamlit ou ligne de commande)."""

    def __init__(self, avec_gb=True):
        self.w, self.observe = charger_series()
        # l'évaluation (lente : gradient boosting ré-entraîné à chaque origine) est mise en cache
        # dans evaluation_modeles.csv, recalculée si les données sont plus récentes
        f_eval = os.path.join(HERE, "evaluation_modeles.csv")
        f_data = os.path.join(HERE, F_DATA)
        if os.path.exists(f_eval) and os.path.getmtime(f_eval) >= os.path.getmtime(f_data):
            self.eval = pd.read_csv(f_eval)
        else:
            self.eval = evaluer(self.w, self.observe, avec_gb=avec_gb)
            if avec_gb:
                self.eval.to_csv(f_eval, index=False, encoding="utf-8-sig")
        e = self.eval[self.eval.methode == "Saisonnier amorti (retenu)"]
        self.sigma = e.groupby("horizon").log_err.std()   # incertitude par horizon (backtest)

    @property
    def produits(self):
        return list(self.w.columns)

    def tableau_erreurs(self):
        return self.eval.pivot_table(index="horizon", columns="methode", values="erreur_pct").round(1)

    def prevoir(self, produit, h=8):
        f, last = prevoir_saisonnier(self.w, self.observe, produit, h)
        smax = self.sigma.iloc[-1] * np.sqrt(np.arange(1, h + 1) / len(self.sigma))
        sig = np.array([self.sigma.get(j, smax[j - 1]) for j in range(1, h + 1)])
        sig = np.maximum.accumulate(sig)  # l'incertitude ne diminue pas avec l'horizon
        prev = pd.DataFrame({
            "semaine": f.index.strftime("%Y-%m-%d"),
            "prevision_DH_kg": f.values.round(2),
            "bas_80pct": (f.values * np.exp(-Z80 * sig)).round(2),
            "haut_80pct": (f.values * np.exp(Z80 * sig)).round(2),
        })
        hist = self.w[produit].dropna().round(2)
        obs = self.observe[produit].reindex(hist.index)
        return prev, hist, obs, last


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) >= 2:
        P = Prevision(avec_gb=False)
        produit = sys.argv[1]
        h = int(sys.argv[2]) if len(sys.argv) > 2 else 8
        prev, hist, obs, last = P.prevoir(produit, h)
        print(f"{produit} (marché de gros de Casablanca) — dernier relevé {last.date()}")
        print(prev.to_string(index=False))
    else:
        P = Prevision()
        print("Produits modélisés :", ", ".join(P.produits))
        print("\nErreur absolue moyenne (%) par horizon (semaines) :")
        print(P.tableau_erreurs().to_string())
