"""CasaHarvest — lance les modules 4 (tourisme), 5 (déchets) et 6 (qualité de l'air) et enregistre les
résultats dans ml/resultats/ (fichiers v4_*, v5_*, v6_*).

Usage : python data/construire_ville.py && python ml/run_ville.py      (~3 minutes)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ville as V  # noqa: E402

OUT = Path(__file__).resolve().parent / "resultats"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 160)

# ============================================================ MODULE 4 : TOURISME
print("Module 4 : fréquentation touristique")
t = V.tourisme_charger()
bt = V.tourisme_backtest(t)
met, par_h = V.tourisme_metriques(bt)
print(met.round(1).to_string(index=False))
bt.to_csv(OUT / "v4_backtest.csv", index=False)
met.to_csv(OUT / "v4_metriques.csv", index=False)
par_h.to_csv(OUT / "v4_erreur_horizon.csv", index=False)
marge, couv_brute, couv_cal = V.tourisme_calibrer(bt)
print(f"Calibration conforme : marge {marge:.3f} (log) ; couverture 2025-26 {couv_brute:.0f} % -> {couv_cal:.0f} %")
pd.DataFrame([dict(marge_log=marge, couverture_brute_2025=couv_brute, couverture_calibree_2025=couv_cal,
                   marge_finale=V.tourisme_marge(bt))]).to_csv(OUT / "v4_calibration.csv", index=False)
prev = V.tourisme_prevoir(t, marge=V.tourisme_marge(bt))
prev.to_csv(OUT / "v4_prevision_12_mois.csv", index=False)
vul = V.tourisme_vulnerabilite(t, prev)
vul.to_csv(OUT / "v4_vulnerabilite.csv", index=False)
print(vul[["destination", "occupation_pic_prevue_pct", "touristes_pour_100_hab", "score_vulnerabilite", "niveau"]]
      .round(1).to_string(index=False))

# ============================================================ MODULE 5 : DÉCHETS
print("\nModule 5 : déchets ménagers")
q, d = V.dechets_charger()
prof, k, sil = V.dechets_profils(q, d)
prof.to_csv(OUT / "v5_profils_quartiers.csv", index=False)
print(f"K-means : {k} groupes (silhouette {sil:.2f})")
print(prof.groupby("typologie")[["kg_hab_j", "part_touristique", "effet_ete", "effet_aid"]].mean().round(1))
te, met5, met_exc, imp = V.dechets_backtest(q, d)
print(met5.round(1).to_string(index=False))
print("Semaines exceptionnelles (Ramadan, Aïd) :", {k: round(v, 1) for k, v in met_exc.items()})
met5.to_csv(OUT / "v5_metriques.csv", index=False)
imp.rename_axis("variable").rename("importance").to_csv(OUT / "v5_importance.csv")
err_h = te.assign(e=np.log(te.reel / te.prevision)).groupby("h").e.quantile([.1, .9]).unstack()
err_h.columns = ["q10", "q90"]
err_h.to_csv(OUT / "v5_erreur_horizon.csv")
pd.Series(met_exc).to_csv(OUT / "v5_metriques_semaines_exceptionnelles.csv", header=["valeur"])
# nuitées futures (module 4 -> module 5) : ratio prévision / même mois de l'an passé
fut = {}
tm = t.set_index(["destination", "mois"]).nuitees
for r in prev.itertuples():
    ref = (pd.Timestamp(r.mois) - pd.DateOffset(years=1)).strftime("%Y-%m")
    if (r.destination, ref) in tm.index:
        fut[(r.destination, pd.Timestamp(r.mois).strftime("%Y-%m"))] = r.prevision / tm[(r.destination, ref)]
for k_ in list(fut):  # Casablanca suit le profil de Marrakech dans les données
    if k_[0] == "Marrakech":
        fut[("Casablanca", k_[1])] = fut[k_]
p5, m5 = V.dechets_prevoir(q, d, fut)
p5 = p5.merge(err_h, left_on="h", right_index=True)
p5["bas"], p5["haut"] = p5.prevision * np.exp(p5.q10), p5.prevision * np.exp(p5.q90)
p5.drop(columns=["q10", "q90"]).to_csv(OUT / "v5_prevision_8_semaines.csv", index=False)
pts = V.points_collecte(q)
tournees = {}
for sc in ["semaine", "haute_saison", "aid"]:
    ton = V.dechets_scenario(q, d, m5, sc)
    tournees[sc] = {v: V.optimiser_tournees(v, pts, ton) for v in V.VILLES_D}
    for v, r in tournees[sc].items():
        print(f"  {sc:13s} {v:11s} {r['tonnes_jour']:7.0f} t/j  {r['camions']:3d} camions  "
              f"{r['km']:7.0f} km (sans optimisation {r['km_naif']:7.0f}, gain {r['gain_km_pct']:.1f} %)")
(OUT / "v5_tournees.json").write_text(json.dumps(tournees, ensure_ascii=False, default=float), encoding="utf-8")

# ============================================================ MODULE 6 : AIR
print("\nModule 6 : qualité de l'air")
a, st = V.air_charger()
evals, sc_, prevs = [], [], []
for pol in V.POLLUANTS:
    e, imp6 = V.air_evaluer(a, pol)
    evals.append(e)
    imp6.rename_axis("variable").rename("importance").to_csv(OUT / f"v6_importance_{pol}.csv")
    sc_.append(V.air_sans_capteur(a, pol))
    f, der = V.air_prevoir(a, pol)
    prevs.append(f)
ev = pd.concat(evals).merge(pd.concat(sc_), on=["polluant", "station"], how="left")
ev.to_csv(OUT / "v6_evaluation_stations.csv", index=False)
print(ev[["polluant", "station", "disponibilite_pct", "mae_modele", "mae_persistance", "couverture_brute",
          "couverture_calibree", "largeur_relative_pct", "mae_modele_j1", "mae_sans_capteur"]].round(1).to_string(index=False))
pd.concat(prevs).to_csv(OUT / "v6_prevision_3_jours.csv", index=False)
print("Dernière mesure :", der.date())
