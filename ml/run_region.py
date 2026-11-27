"""CasaHarvest Région — lance les 4 thèmes et écrit ml/resultats/r_*.csv / r_*.json.

Usage : python data/construire_provinces.py && python ml/run_region.py     (~1 minute)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import region as R  # noqa: E402

OUT = Path(__file__).resolve().parent / "resultats"
OUT.mkdir(exist_ok=True)
pd.set_option("display.width", 180)
prov, clim, rend = R.charger()

# ---------------------------------------------------------------- A. Pluie
print("A. Pluie CHIRPS")
saison, norm = R.pluie_saison(clim)
saison.to_csv(OUT / "r_pluie_saisons.csv", index=False)
R.pluie_climatologie(clim).to_csv(OUT / "r_pluie_climatologie.csv", index=False)
s3 = R.spi(clim)
s3.to_csv(OUT / "r_spi3.csv", index=False)
terc = R.pluie_terciles(clim)
pd.DataFrame([terc]).to_csv(OUT / "r_pluie_terciles.csv", index=False)
print("  normales (mm/saison) :", norm["mean"].round(0).to_dict())
print("  saison 2026 (% normale) :", saison[saison.saison == 2026].set_index("province").pct_normale.round(0).to_dict())
print("  prévision du mois suivant (terciles) :", {k: round(v, 3) for k, v in terc.items()})

# ---------------------------------------------------------------- B. Humidité du sol
print("B. Humidité du sol ERA5-Land")
etat = R.sol_etat(clim)
etat.to_csv(OUT / "r_sol_etat.csv", index=False)
met_sol, best_sol, err_sol, tsol = R.sol_evaluer(clim)
met_sol.to_csv(OUT / "r_sol_metriques.csv", index=False)
prev_sol = R.sol_prevoir(clim, best_sol, err_sol)
src2prov = clim.drop_duplicates("province").set_index("province").source_era5
prev_sol = prev_sol.merge(src2prov.rename("source").reset_index(), on="source")
prev_sol.to_csv(OUT / "r_sol_prevision.csv", index=False)
print(met_sol.round(4).to_string(index=False))
print("  meilleur :", best_sol, "| état :", etat.set_index("province").classe.to_dict())

# ---------------------------------------------------------------- C. Récoltes
print("C. Récoltes par province")
met_r, best_r, t, reg, cols = R.recolte_evaluer(rend, clim)
print(met_r.round(2).to_string(index=False))
print("  variables :", cols)
met_r.to_csv(OUT / "r_recolte_metriques.csv", index=False)
t[["province", "culture", "campagne", "superficie_ha", "production_t", "rendement_qx_ha", "prevision_cv"]] \
    .to_csv(OUT / "r_recolte_validation.csv", index=False)
reg.to_csv(OUT / "r_recolte_validation_region.csv", index=False)
m, imp = R.recolte_modele_final(t, best_r, cols)
if imp is not None:
    imp.rename_axis("variable").rename("importance_pct").to_csv(OUT / "r_recolte_importance.csv")
prev = R.recolte_prevoir(m, t, rend, clim, cols)
prev.to_csv(OUT / "r_recolte_previsions.csv", index=False)
tot = prev.groupby("campagne").production_prevue_t.sum() / 1e5
print("  production régionale prévue (Mqx) :", tot.round(1).to_dict(), "| officiel 2026 : 25,8 Mqx")
sc = R.recolte_scenarios(m, t, clim, cols)
sc.to_csv(OUT / "r_recolte_scenarios_2027.csv", index=False)
json.dump({"meilleur_modele": best_r, "officiel_2026_Mqx": 25.8, "surface_officielle_2026_ha": 852555,
           "source_officiel": "Direction régionale de l'agriculture Casablanca-Settat (presse, juin 2026)"},
          open(OUT / "r_recolte_info.json", "w", encoding="utf-8"), ensure_ascii=False)

# ---------------------------------------------------------------- D. Barrage
print("D. Barrage Al Massira")
b = R.barrage_charger()
coef, tb, met_b, pj, et0j = R.barrage_calibrer(b, clim)
print("  coefficients :", {k: round(v, 4) for k, v in coef.items()}, "| validation :", {k: round(v, 2) for k, v in met_b.items()})
tb.to_csv(OUT / "r_barrage_intervalles.csv", index=False)
prev_b, traj = R.barrage_prevoir(b, coef, pj, et0j)
print(prev_b.round(2).to_string(index=False))
prev_b.to_csv(OUT / "r_barrage_prevision.csv", index=False)
traj.to_csv(OUT / "r_barrage_trajectoire.csv", index=False)
der = b.iloc[-1]
risque = R.risque_penurie(der.taux_pct, prev_b[prev_b.horizon_jours == 90].bas_pct.iloc[0])
json.dump({"coefficients": coef, "validation": met_b, "dernier": {"date": der.date.strftime("%Y-%m-%d"),
           "taux_pct": der.taux_pct, "volume_Mm3": der.volume_Mm3}, "capacite_Mm3": R.CAP, "risque": risque,
           "conso_casablanca_Mm3_an": 225,
           "source_conso": "https://medias24.com/2025/03/12/atten-deux-jours-les-barrages-au-maroc-gagnent-lequivalent-dune-annee-de-consommation-de-casablanca/"},
          open(OUT / "r_barrage_info.json", "w", encoding="utf-8"), ensure_ascii=False, default=float)
print("  risque de pénurie :", risque)
