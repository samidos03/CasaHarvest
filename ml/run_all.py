"""Lance l'expérience XGBoost hebdomadaire et enregistre les résultats dans ml/resultats/ (CSV + figure PNG).

Usage : python run_all.py            (~1 minute)
"""
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
import xgb_hebdo as XH

OUT = Path(__file__).resolve().parent / "resultats"
OUT.mkdir(exist_ok=True)
t0 = time.time()


def log(msg):
    print(f"[{time.time() - t0:6.0f}s] {msg}", flush=True)


log("XGBoost hebdomadaire : backtest")
res, imp = XH.backtest(verbose=False)
res.to_csv(OUT / "xgb_hebdo_backtest.csv", index=False, encoding="utf-8-sig")
imp.rename("importance").to_csv(OUT / "xgb_hebdo_importance.csv", encoding="utf-8-sig")

# métriques par horizon : MAPE, médiane, RMSE (log), part des prévisions à ±10 %, sens de variation correct
res["err_log"] = np.log(res.prevision / res.reel)
# sens de variation : seulement quand le prix réel a bougé d'au moins 2 % (sinon pas de « sens » à prévoir)
bouge = (res.reel / res.dernier_prix - 1).abs() >= 0.02
res["bon_sens"] = np.where(bouge, np.sign(res.prevision - res.dernier_prix) == np.sign(res.reel - res.dernier_prix),
                           np.nan)
res["a_10pct"] = res.erreur_pct <= 10
tab = res.groupby("horizon").agg(
    MAPE_pct=("erreur_pct", "mean"), erreur_mediane_pct=("erreur_pct", "median"),
    RMSE_log=("err_log", lambda e: np.sqrt(np.mean(e ** 2))),
    part_a_10pct=("a_10pct", lambda s: 100 * s.mean()),
    sens_correct_pct=("bon_sens", lambda s: 100 * s.dropna().astype(float).mean()),
    n=("erreur_pct", "size")).round(2)
tab.to_csv(OUT / "xgb_hebdo_erreur_horizon.csv", encoding="utf-8-sig")
res.groupby("produit").agg(MAPE_pct=("erreur_pct", "mean"), erreur_mediane_pct=("erreur_pct", "median"),
                           n=("erreur_pct", "size")).round(1).sort_values("MAPE_pct") \
    .to_csv(OUT / "xgb_hebdo_erreur_produit.csv", encoding="utf-8-sig")

fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
ax[0].plot(tab.index, tab.MAPE_pct, marker="o", color="#0B7A43", lw=2.5, label="erreur moyenne (MAPE)")
ax[0].plot(tab.index, tab.erreur_mediane_pct, marker="s", color="#E0A100", lw=1.8, ls="--", label="erreur médiane")
ax[0].set(title="XGBoost — erreur selon l'horizon", xlabel="horizon (semaines)", ylabel="erreur (%)")
ax[0].legend()
ax[0].grid(alpha=.3)
imp.head(12).iloc[::-1].plot.barh(ax=ax[1], color="#0B7A43")
ax[1].set(title="XGBoost — importance des variables (gain)", xlabel="part du gain")
fig.tight_layout()
fig.savefig(OUT / "fig1_xgb_hebdo.png", dpi=130)
plt.close(fig)

log("XGBoost hebdomadaire : prévision des 8 prochaines semaines")
prev = []
for p, (s, d0) in XH.prevoir_tous().items():
    for h, (semaine, val) in enumerate(s.items(), start=1):
        prev.append({"produit": p, "dernier_releve": d0.date(), "horizon_sem": h, "semaine": semaine.date(),
                     "prevision_XGBoost_DH_kg": round(val, 2)})
pd.DataFrame(prev).to_csv(OUT / "xgb_hebdo_prevision_8_semaines.csv", index=False, encoding="utf-8-sig")

log("terminé")
print(tab)
