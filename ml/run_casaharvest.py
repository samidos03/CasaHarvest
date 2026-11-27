"""CasaHarvest — lance les modules 1 (rendement) et 2 (sécheresse) et enregistre résultats + figures
dans ml/resultats/ (fichiers m1_* et m2_*).

Usage : python run_casaharvest.py      (~2 minutes)
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
import rendement as R
import secheresse as S

OUT = Path(__file__).resolve().parent / "resultats"
OUT.mkdir(exist_ok=True)
VERT, OR, GRIS, ROUGE = "#0B7A43", "#E0A100", "#7A8A99", "#C1272D"
COUL = {"Ridge": GRIS, "XGBoost": OR, R.HYBRIDE: VERT}
# Prévision officielle 2026 (Direction régionale de l'agriculture, relayée par la presse, juin 2026) :
OFFICIEL_2026 = {"production_Mqx": 25.8, "surface_ha": 852555}

# ============================================================ MODULE 1 : RENDEMENT
print("Module 1 : rendement des céréales")
ml, clim = R.charger()
cv = R.validation_croisee(ml)
tab, par_culture, tab_reg, reg = R.metriques(cv)
cv.to_csv(OUT / "m1_validation_croisee.csv", index=False, encoding="utf-8-sig")
tab.to_csv(OUT / "m1_metriques.csv", encoding="utf-8-sig")
par_culture.to_csv(OUT / "m1_metriques_par_culture.csv", encoding="utf-8-sig")
tab_reg.to_csv(OUT / "m1_metriques_region.csv", encoding="utf-8-sig")
fut, fut_reg = R.prevoir_futur(ml, clim)
fut.to_csv(OUT / "m1_previsions_2024_2026.csv", index=False, encoding="utf-8-sig")
fut_reg.to_csv(OUT / "m1_previsions_region_2024_2026.csv", encoding="utf-8-sig")
futm, futm_reg = R.prevoir_futur(ml, clim, moment="mars")
futm_reg.to_csv(OUT / "m1_previsions_region_2024_2026_mars.csv", encoding="utf-8-sig")
print(tab)
print(fut_reg.T)

fig, ax = plt.subplots(1, 2, figsize=(13.5, 5.4))
# (a) le facteur clé : SPI-6 de mars -> rendement
for cult, mk in zip(R.CULTURES, ["o", "s", "^"]):
    d = ml[ml.culture == cult]
    ax[0].scatter(d.spi_6_mars, d.rendement_qx_ha, s=26, marker=mk, alpha=.75, label=cult)
xx = np.linspace(-1.6, 2.1, 50)
grille = pd.DataFrame({"spi_6_mars": xx, "humidite_sol_printemps": ml.humidite_sol_printemps.median(),
                       "jours_chauds_printemps": ml.jours_chauds_printemps.median(), "culture": "Blé tendre",
                       "zone": "Settat-Berrechid"})
for nom in ["Ridge", "XGBoost"]:
    m = R.modele(nom, "mai").fit(ml[R.VARS["mai"] + R.CATS], ml.rendement_qx_ha)
    ax[0].plot(xx, np.clip(m.predict(grille[R.VARS["mai"] + R.CATS]), 0, None), color=COUL[nom], lw=2.2,
               label=f"{nom} (blé tendre, Settat)")
ax[0].axvspan(ml.spi_6_mars.max(), 2.1, color=GRIS, alpha=.12)
ax[0].text(ml.spi_6_mars.max() + .03, 2, "hors des données\n2010-2023", fontsize=8, color=GRIS)
ax[0].set(title="Sécheresse de mars et rendement des céréales", xlabel="SPI-6 en mars (≤ −1 : sécheresse)",
          ylabel="rendement (q/ha)")
ax[0].legend(fontsize=7.5, loc="upper left")
ax[0].grid(alpha=.3)
# (b) région : réel vs prévu (validation croisée) + prévisions 2024-2026
r = reg[(reg.moment == "mai") & (reg.modele == R.HYBRIDE)]
rr = r.assign(pr=r.prevision * r.s, re=r.reel * r.s).groupby("campagne")[["pr", "re", "s"]].sum()
ax[1].plot(rr.index, rr.re / rr.s, color="black", marker="o", lw=2, label="rendement réel (HCP)")
ax[1].plot(rr.index, rr.pr / rr.s, color=VERT, marker="o", lw=2, ls="--",
           label="prévu par le modèle hybride (campagne laissée de côté)")
fy = fut_reg["rendement_moyen_qx_ha"]
for nom in [R.HYBRIDE, "XGBoost"]:
    ax[1].plot([2023, 2024, 2025, 2026], [rr.pr.iloc[-1] / rr.s.iloc[-1], *fy[nom].values], color=COUL[nom],
               marker="D", lw=1.5, ls=":" if nom == "XGBoost" else "-", label=f"prévision 2024-2026 — {nom}")
off = OFFICIEL_2026["production_Mqx"] * 1e6 / OFFICIEL_2026["surface_ha"]
ax[1].scatter([2026], [off], s=140, marker="*", color=ROUGE, zorder=5, label="prévision officielle 2026 (≈ 30 q/ha)")
ax[1].set(title="Région Casablanca-Settat — céréales (blé tendre, blé dur, orge)", xlabel="campagne (année de récolte)",
          ylabel="rendement moyen (q/ha)")
ax[1].legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False)
ax[1].grid(alpha=.3)
fig.tight_layout()
fig.savefig(OUT / "fig_m1_rendement.png", dpi=130)
plt.close(fig)

# ============================================================ MODULE 2 : SÉCHERESSE
print("\nModule 2 : risque de sécheresse")
s = S.charger()
v = S.validation(s)
mt = S.metriques(v)
v.to_csv(OUT / "m2_validation_temporelle.csv", index=False, encoding="utf-8-sig")
mt.to_csv(OUT / "m2_metriques.csv", encoding="utf-8-sig")
pv = S.prevoir(s, nom="Ridge")
pv.to_csv(OUT / "m2_prevision_3_mois.csv", index=False, encoding="utf-8-sig")
etat = s.dropna(subset=["spi_3"]).sort_values("date").groupby("zone").tail(1)[
    ["zone", "mois", "spi_1", "spi_3", "spi_6", "spi_12", "anomalie_humidite_sol", "classe_secheresse_spi3"]]
etat.to_csv(OUT / "m2_etat_actuel.csv", index=False, encoding="utf-8-sig")
print(mt)
print(pv)

fig, ax = plt.subplots(1, 2, figsize=(13.5, 4.4))
z = "Settat-Berrechid"
obs = s[(s.zone == z) & (s.date >= "2017-09-01")].set_index("date").spi_3
ax[0].plot(obs.index, obs.values, color="black", lw=1.6, label="SPI-3 observé")
for nom in ["Ridge", "XGBoost"]:
    d = v[(v.zone == z) & (v.horizon == 1) & (v.modele == nom)].set_index("date_cible").prevision
    ax[0].scatter(d.index, d.values, s=14, color=COUL[nom], label=f"prévu 1 mois avant — {nom}", zorder=3)
ax[0].axhline(-1, color=ROUGE, ls="--", lw=1)
ax[0].axhline(S.ALERTE, color=OR, ls=":", lw=1)
ax[0].text(obs.index[0], -1.15, "seuil de sécheresse (−1)", color=ROUGE, fontsize=8, va="top")
ax[0].text(obs.index[0], S.ALERTE + .08, "seuil d'alerte (−0,5)", color=OR, fontsize=8)
ax[0].set(title=f"Sécheresse à {z} : observé et prévu (saison des pluies)", ylabel="SPI-3")
ax[0].legend(fontsize=7.5, loc="upper right")
ax[0].grid(alpha=.3)
mm = mt.reset_index()
w = .35
for i, nom in enumerate(["Ridge", "XGBoost"]):
    d = mm[mm.modele == nom]
    ax[1].bar(d.horizon + (i - .5) * w, d.R2.clip(lower=-0.5), w, color=COUL[nom], label=f"R² — {nom}")
ax[1].axhline(0, color="black", lw=.8)
ax[1].set(title="Fiabilité selon l'horizon de prévision", xlabel="horizon (mois)", ylabel="R² (0 = pas mieux que la normale)",
          xticks=[1, 2, 3])
ax[1].legend(fontsize=8)
ax[1].grid(alpha=.3, axis="y")
fig.tight_layout()
fig.savefig(OUT / "fig_m2_secheresse.png", dpi=130)
plt.close(fig)
print("terminé")
