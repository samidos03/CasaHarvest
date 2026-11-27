"""CasaHarvest — volet « ville » : construit les données des modules 4 (tourisme), 5 (déchets) et 6 (air).

IMPORTANT — nature des données
  Les séries mensuelles par destination, les tonnages par quartier et les mesures par station ne sont pas
  publiées en open data au Maroc sous une forme téléchargeable. Ce script produit donc des séries
  SIMULÉES mais CALIBRÉES sur des chiffres publics :
    * météo hebdomadaire RÉELLE des villes (ERA5-Land / Open-Meteo, fichier data/meteo_hebdo_villes.csv)
    * calendrier RÉEL des fêtes (data/calendrier_fetes.csv : Ramadan, Aïd al-Adha)
    * tourisme : nuitées annuelles et mensuelles de l'Observatoire du tourisme (presse 2024) —
      Marrakech ~10 M, Agadir ~6,5 M nuitées en 2024 ; janvier 2024 : Marrakech 692 525, Agadir 418 716,
      Essaouira 41 386 ; chute Covid 2020-2021 ; séisme d'Al Haouz (sept. 2023)
    * déchets : Casablanca ~2 600 t/j de déchets ménagers (2015), Marrakech ~900 t/j au CEV (2020),
      arrondissement Ménara 462 958 hab. pour 158 775 t/an ; moyenne nationale ~250 kg/hab/an
    * air : PM10 moyen ~60-75 µg/m³ à Casablanca (OMS 2016, études DMN), NO2 ~60 µg/m³ ; baisse du NO2
      pendant le confinement de 2020 ; épisodes de poussières sahariennes (chergui)
  Les données réelles peuvent remplacer ces fichiers sans changer le code ML (mêmes colonnes).

Sorties : data/ville/tourisme_mensuel.csv, dechets_quartiers.csv, dechets_hebdo.csv,
          air_stations.csv, air_journalier.csv
Usage : python data/construire_ville.py     (~10 s)
"""
from pathlib import Path

import numpy as np
import pandas as pd

ICI = Path(__file__).resolve().parent
OUT = ICI / "ville"
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(2026)

METEO = pd.read_csv(ICI / "meteo_hebdo_villes.csv", encoding="utf-8-sig", parse_dates=["semaine"])
FETES = pd.read_csv(ICI / "calendrier_fetes.csv", encoding="utf-8-sig", parse_dates=["semaine"])

# Début du Ramadan (dates observées au Maroc) — 30 jours
RAMADAN = ["2017-05-27", "2018-05-17", "2019-05-07", "2020-04-25", "2021-04-14", "2022-04-03", "2023-03-23",
           "2024-03-12", "2025-03-02", "2026-02-19", "2027-02-08"]
JOURS_RAMADAN = pd.DatetimeIndex(np.concatenate([pd.date_range(d, periods=30) for d in RAMADAN]))
AID_ADHA = pd.to_datetime(["2017-09-01", "2018-08-22", "2019-08-12", "2020-07-31", "2021-07-21", "2022-07-10",
                           "2023-06-29", "2024-06-17", "2025-06-07", "2026-05-27", "2027-05-17"])


def covid(m):
    """Facteur d'activité touristique (1 = normal) — fermeture des frontières 2020, reprise 2021-2022."""
    m = pd.Timestamp(m)
    if m < pd.Timestamp("2020-03-01"):
        return 1.0
    table = {"2020-03": .55, "2020-04": .03, "2020-05": .03, "2020-06": .06, "2020-07": .22, "2020-08": .30,
             "2020-09": .22, "2020-10": .20, "2020-11": .18, "2020-12": .17, "2021-01": .16, "2021-02": .18,
             "2021-03": .20, "2021-04": .22, "2021-05": .25, "2021-06": .40, "2021-07": .55, "2021-08": .55,
             "2021-09": .50, "2021-10": .55, "2021-11": .55, "2021-12": .25, "2022-01": .30, "2022-02": .55,
             "2022-03": .70, "2022-04": .72, "2022-05": .80, "2022-06": .85}
    k = m.strftime("%Y-%m")
    if k in table:
        return table[k]
    return 0.92 if m < pd.Timestamp("2023-01-01") else 1.0


# =============================================================================== MODULE 4 : TOURISME
# niveau annuel 2024 (nuitées en établissements classés), poids des marchés, capacité (lits), population
DEST = {
    "Marrakech": dict(n2024=10.0e6, meteo="Marrakech", lits=56000, pop=1.07e6, lat=31.63, lon=-8.01,
                      marches={"France": .30, "Royaume-Uni": .14, "Espagne": .07, "Allemagne": .05,
                               "Autres étrangers": .22, "Résidents (Maroc)": .22},
                      saison=[.78, .86, 1.02, 1.18, 1.05, .82, .78, .86, .98, 1.16, 1.05, 1.14]),
    "Agadir": dict(n2024=6.5e6, meteo="Agadir", lits=33000, pop=0.47e6, lat=30.42, lon=-9.60,
                   marches={"France": .24, "Royaume-Uni": .16, "Allemagne": .14, "Espagne": .03,
                            "Autres étrangers": .23, "Résidents (Maroc)": .20},
                   saison=[.80, .92, 1.00, 1.08, .92, .88, 1.10, 1.22, .98, 1.05, .98, 1.08]),
    "Fès": dict(n2024=1.15e6, meteo="Fès", lits=9000, pop=1.26e6, lat=34.03, lon=-5.00,
                marches={"France": .26, "Espagne": .14, "Royaume-Uni": .05, "Allemagne": .04,
                         "Autres étrangers": .26, "Résidents (Maroc)": .25},
                saison=[.62, .72, .98, 1.22, 1.18, .92, .98, 1.10, 1.12, 1.20, .98, .98]),
    "Essaouira": dict(n2024=0.55e6, meteo="Agadir", lits=3500, pop=0.08e6, lat=31.51, lon=-9.77,
                      marches={"France": .38, "Royaume-Uni": .06, "Allemagne": .07, "Espagne": .04,
                               "Autres étrangers": .17, "Résidents (Maroc)": .28},
                      saison=[.78, .82, .98, 1.12, 1.02, 1.12, 1.18, 1.28, .98, .98, .82, .94]),
    "Chefchaouen": dict(n2024=0.16e6, meteo="Tétouan", lits=1400, pop=0.045e6, lat=35.17, lon=-5.27,
                        marches={"Espagne": .30, "France": .10, "Royaume-Uni": .04, "Allemagne": .03,
                                 "Autres étrangers": .23, "Résidents (Maroc)": .30},
                        saison=[.52, .60, .92, 1.30, 1.20, .98, 1.15, 1.40, 1.15, 1.10, .80, .88]),
}
# croissance annuelle (indice 2024 = 1), avant Covid puis rattrapage
CROISSANCE = {2017: .80, 2018: .86, 2019: .90, 2020: .90, 2021: .90, 2022: .84, 2023: .93, 2024: 1.0, 2025: 1.10,
              2026: 1.16}
# vacances scolaires (part du mois) — France (zone C simplifiée), Royaume-Uni, Espagne, Maroc
VAC = {"France": [.35, .45, 0, .50, .15, 0, .9, 1, 0, .35, .1, .35],
       "Royaume-Uni": [.1, .25, .1, .5, .25, 0, .45, 1, .05, .25, 0, .35],
       "Espagne": [.2, 0, .1, .5, 0, .2, 1, 1, .1, 0, 0, .35],
       "Résidents (Maroc)": [.35, 0, .3, 0, .1, .2, 1, 1, .1, .1, .3, .2]}
# événements (destination, mois, effet multiplicatif, nom)
EVENEMENTS = [("Marrakech", 12, 1.08, "Festival international du film"),
              ("Marrakech", 4, 1.04, "Marathon / Marrakech du rire"),
              ("Essaouira", 6, 1.22, "Festival Gnaoua"),
              ("Fès", 5, 1.10, "Festival des musiques sacrées"),
              ("Fès", 6, 1.06, "Festival des musiques sacrées"),
              ("Agadir", 12, 1.05, "Fin d'année / Timitar"),
              ("Chefchaouen", 8, 1.06, "Été du Rif")]
# CAN 2025 (déc. 2025 - janv. 2026) dans les villes hôtes
CAN = {("Marrakech", "2025-12"): 1.10, ("Marrakech", "2026-01"): 1.08, ("Agadir", "2025-12"): 1.10,
       ("Agadir", "2026-01"): 1.07, ("Fès", "2025-12"): 1.12, ("Fès", "2026-01"): 1.08}


def construire_tourisme():
    mois = pd.date_range("2017-01-01", "2026-10-01", freq="MS")
    met = METEO.assign(m=METEO.semaine.dt.to_period("M").dt.to_timestamp())
    met = met.groupby(["ville", "m"]).agg(temp=("temp_moy_C", "mean"), pluie=("pluie_mm", "sum")).reset_index()
    jr = pd.Series(1, index=JOURS_RAMADAN).groupby(JOURS_RAMADAN.to_period("M")).sum()
    lignes = []
    for d, p in DEST.items():
        base = p["n2024"] / 12 / np.mean(p["saison"])
        bruit = rng.normal(0, .035, len(mois))
        ar = np.zeros(len(mois))
        for i in range(len(mois)):
            ar[i] = (.55 * ar[i - 1] if i else 0) + bruit[i]
        for i, m in enumerate(mois):
            k = m.strftime("%Y-%m")
            ram = int(jr.get(m.to_period("M"), 0))
            ev = [e for e in EVENEMENTS if e[0] == d and e[1] == m.month and m.year >= 2017]
            fev = np.prod([e[2] for e in ev]) if ev else 1.0
            if d == "Fès" and m.year in (2020, 2021):
                fev = 1.0
            fcan = CAN.get((d, k), 1.0)
            fseisme = {"2023-09": .80, "2023-10": .88, "2023-11": .95}.get(k, 1.0) if d in ("Marrakech",) else 1.0
            fcov = covid(m)
            t = met[(met.ville == p["meteo"]) & (met.m == m)]
            temp = float(t.temp.iloc[0]) if len(t) else np.nan
            # année de croissance interpolée au mois
            g0, g1 = CROISSANCE[m.year], CROISSANCE.get(m.year + 1, CROISSANCE[m.year] * 1.04)
            g = g0 + (g1 - g0) * (m.month - 1) / 12
            tot = 0
            par_marche = {}
            for mk, w in p["marches"].items():
                v = VAC.get(mk, [0] * 12)[m.month - 1]
                f_ram = (1 - .55 * ram / 30) if mk == "Résidents (Maroc)" else (1 - .10 * ram / 30)
                # les résidents reviennent fortement après Covid (tourisme interne 2020-21)
                f_cov = min(1, fcov * (2.2 if mk == "Résidents (Maroc)" else 1)) if fcov < 1 else 1
                if mk == "Royaume-Uni" and m.year < 2020:
                    w *= .85  # montée du marché britannique (vols low-cost) après 2022
                n = base * w * p["saison"][m.month - 1] * (1 + .18 * v) * f_ram * f_cov * fev * fcan * fseisme * g
                par_marche[mk] = n * np.exp(ar[i] + rng.normal(0, .03))
                tot += par_marche[mk]
            lignes.append(dict(mois=m.strftime("%Y-%m"), destination=d, nuitees=round(tot),
                               **{f"nuitees_{mk}": round(v) for mk, v in par_marche.items()},
                               jours_ramadan=ram, evenement="; ".join(sorted({e[3] for e in ev})) if fev > 1 else "",
                               can_2025=int(fcan > 1), facteur_covid=fcov,
                               vac_france=VAC["France"][m.month - 1], vac_royaume_uni=VAC["Royaume-Uni"][m.month - 1],
                               vac_espagne=VAC["Espagne"][m.month - 1], vac_maroc=VAC["Résidents (Maroc)"][m.month - 1],
                               temp_moy_C=round(temp, 1), pluie_mm=round(float(t.pluie.iloc[0]), 1) if len(t) else np.nan,
                               capacite_lits=p["lits"], population=int(p["pop"])))
    df = pd.DataFrame(lignes)
    # calage exact sur les repères publiés de janvier 2024
    for d, cible in {"Marrakech": 692525, "Agadir": 418716, "Essaouira": 41386}.items():
        m = (df.destination == d)
        r = cible / df.loc[m & (df.mois == "2024-01"), "nuitees"].iloc[0]
        r = 1 + (r - 1) * .8  # calage partiel pour garder le niveau annuel
        cols = [c for c in df.columns if c.startswith("nuitees")]
        df.loc[m, cols] = (df.loc[m, cols] * r).round()
    df.to_csv(OUT / "tourisme_mensuel.csv", index=False, encoding="utf-8")
    a = df[df.mois.str.startswith("2024")].groupby("destination").nuitees.sum() / 1e6
    print("Tourisme : nuitées 2024 (M) ->", a.round(2).to_dict())
    return df


# =============================================================================== MODULE 5 : DÉCHETS
KG_HAB_J = {"Médina dense": 0.78, "Habitat économique": 0.70, "Moyen standing": 0.88, "Villas / résidentiel": 1.15,
            "Zone touristique & hôtelière": 0.95}
QUARTIERS = {  # nom, lat, lon, population, habitat, part des lits touristiques de la ville
    "Marrakech": [("Médina", 31.628, -7.988, 125000, "Médina dense", .20),
                  ("Guéliz", 31.636, -8.012, 85000, "Moyen standing", .16),
                  ("Hivernage", 31.620, -8.020, 15000, "Zone touristique & hôtelière", .30),
                  ("Palmeraie", 31.670, -7.970, 25000, "Villas / résidentiel", .17),
                  ("Daoudiate", 31.650, -8.010, 95000, "Moyen standing", .02),
                  ("Sidi Youssef Ben Ali", 31.605, -7.975, 150000, "Habitat économique", .01),
                  ("M'Hamid", 31.585, -8.040, 210000, "Habitat économique", .02),
                  ("Massira", 31.615, -8.075, 190000, "Habitat économique", .01),
                  ("Agdal / route de l'Ourika", 31.590, -7.990, 45000, "Villas / résidentiel", .09),
                  ("Annakhil / Sidi Ghanem", 31.680, -8.040, 110000, "Moyen standing", .02)],
    "Casablanca": [("Anfa", 33.590, -7.660, 110000, "Villas / résidentiel", .18),
                   ("Maârif", 33.580, -7.635, 180000, "Moyen standing", .12),
                   ("Centre / Sidi Belyout", 33.596, -7.615, 90000, "Zone touristique & hôtelière", .40),
                   ("Ancienne médina", 33.604, -7.620, 60000, "Médina dense", .05),
                   ("Hay Mohammadi", 33.590, -7.560, 160000, "Habitat économique", .01),
                   ("Sidi Moumen", 33.585, -7.505, 450000, "Habitat économique", .01),
                   ("Aïn Chock", 33.540, -7.600, 300000, "Moyen standing", .04),
                   ("Sidi Bernoussi", 33.610, -7.500, 300000, "Habitat économique", .02),
                   ("Hay Hassani", 33.555, -7.680, 400000, "Habitat économique", .05),
                   ("Ben M'Sick / Moulay Rachid", 33.555, -7.560, 600000, "Habitat économique", .02),
                   ("Aïn Sebaâ", 33.605, -7.540, 220000, "Moyen standing", .02),
                   ("Ain Diab / Corniche", 33.590, -7.690, 40000, "Zone touristique & hôtelière", .28)],
    "Agadir": [("Secteur touristique (baie)", 30.410, -9.600, 20000, "Zone touristique & hôtelière", .62),
               ("Talborjt / centre", 30.425, -9.595, 45000, "Moyen standing", .10),
               ("Founty / Sonaba", 30.395, -9.595, 30000, "Villas / résidentiel", .20),
               ("Dakhla / Hay Mohammadi", 30.410, -9.565, 95000, "Habitat économique", .02),
               ("Tikiouine", 30.390, -9.530, 120000, "Habitat économique", .01),
               ("Bensergao", 30.385, -9.565, 85000, "Moyen standing", .02),
               ("Anza / Taddart", 30.445, -9.650, 75000, "Habitat économique", .03)],
}
DEPOTS = {"Marrakech": ("CEV de M'Nabha", 31.560, -8.110), "Casablanca": ("Décharge de Médiouna", 33.470, -7.520),
          "Agadir": ("CEV de Tamelast", 30.490, -9.520)}
# Casablanca : nuitées ~2,2 M / an
CASA_NUITEES = 2.2e6


def construire_dechets(tour):
    q = pd.DataFrame([dict(ville=v, quartier=n, lat=la, lon=lo, population=p, habitat=h, part_lits=pl)
                      for v, L in QUARTIERS.items() for (n, la, lo, p, h, pl) in L])
    q["kg_hab_j_ref"] = q.habitat.map(KG_HAB_J)
    q.to_csv(OUT / "dechets_quartiers.csv", index=False, encoding="utf-8")

    sem = pd.date_range("2019-01-02", "2026-11-18", freq="7D")
    fet = FETES.set_index("semaine").reindex(sem, method="nearest")
    met = METEO[METEO.ville.isin(["Marrakech", "Casablanca", "Agadir"])]
    # nuitées hebdo (interpolées depuis le mensuel)
    tm = tour.assign(m=pd.to_datetime(tour.mois)).pivot(index="m", columns="destination", values="nuitees")
    casa = tm["Marrakech"] / tm["Marrakech"].groupby(tm.index.year).transform("sum").replace(0, 1)
    tm["Casablanca"] = (CASA_NUITEES * tm["Marrakech"] / 10e6) * .9 + 0  # même profil, échelle de Casablanca
    jours_mois = tm.index.days_in_month.values[:, None]
    tj = (tm / jours_mois).reindex(pd.date_range(tm.index[0], "2026-11-30")).ffill()
    lignes = []
    for v in QUARTIERS:
        mv = met[met.ville == v].set_index("semaine").reindex(sem, method="nearest")
        for _, r in q[q.ville == v].iterrows():
            ar, base_bruit = 0.0, rng.normal(0, .025, len(sem))
            croiss = 1.0
            for i, s in enumerate(sem):
                croiss = (1 + .018) ** ((s - sem[0]).days / 365)
                nuitees_sem = float(tj[v].reindex(pd.date_range(s, periods=7)).sum()) * r.part_lits
                # population présente : été = retour des MRE et estivants (côte) ; Covid = confinement
                ete = 1 + (.10 if s.month in (7, 8) else 0) * (1.6 if v == "Agadir" else 1)
                rmd = fet.ramadan.iloc[i]
                aid = fet.aid_al_adha.iloc[i]
                avant_aid = fet.semaine_avant_aid.iloc[i]
                conf = .93 if pd.Timestamp("2020-03-20") <= s <= pd.Timestamp("2020-06-10") else 1.0
                pluie = float(mv.pluie_mm.iloc[i]) if not np.isnan(mv.pluie_mm.iloc[i]) else 0
                f_hab = 1 + (.16 * rmd) + (.55 * aid if r.habitat != "Zone touristique & hôtelière" else .1 * aid) \
                    + .08 * avant_aid
                # été : plus de déchets verts/emballages dans les quartiers aisés, moins (vacances) dans les autres
                if r.habitat in ("Villas / résidentiel",) and s.month in (7, 8):
                    f_hab *= 1.06
                menages_t = r.population * r.kg_hab_j_ref * 7 / 1000 * croiss * ete * f_hab * conf
                touristes_t = nuitees_sem * 1.6 / 1000  # ~1,6 kg par nuitée (hôtellerie + restauration)
                ar = .6 * ar + base_bruit[i]
                tonnes = (menages_t + touristes_t) * np.exp(ar) * (1 - .004 * min(pluie, 40) / 10)
                lignes.append(dict(semaine=s.strftime("%Y-%m-%d"), ville=v, quartier=r.quartier,
                                   tonnes=round(tonnes, 1), nuitees_quartier=round(nuitees_sem), ramadan=int(rmd),
                                   aid_al_adha=int(aid), semaine_avant_aid=int(avant_aid), ete=int(s.month in (7, 8)),
                                   confinement=int(conf < 1), pluie_mm=round(pluie, 1),
                                   temp_moy_C=round(float(mv.temp_moy_C.iloc[i]), 1)))
    d = pd.DataFrame(lignes)
    d.to_csv(OUT / "dechets_hebdo.csv", index=False, encoding="utf-8")
    j = d[d.semaine >= "2025-01-01"].groupby("ville").tonnes.sum() / (d[d.semaine >= "2025-01-01"].semaine.nunique() * 7)
    print("Déchets : t/jour 2025+ ->", j.round(0).to_dict())
    return d


# =============================================================================== MODULE 6 : AIR
STATIONS = [  # station, ville, type, lat, lon, niveau PM10, niveau NO2, taux de données manquantes
    ("Aïn Sebaâ (industrielle)", "Casablanca", "industrielle", 33.605, -7.535, 1.25, 1.05, .06),
    ("Derb Soltane (trafic)", "Casablanca", "trafic", 33.575, -7.610, 1.10, 1.40, .05),
    ("Sidi Othmane (fond urbain)", "Casablanca", "fond urbain", 33.565, -7.550, .95, .85, .08),
    ("Jahid / Maârif (fond urbain)", "Casablanca", "fond urbain", 33.585, -7.640, .85, .80, .10),
    ("Bab Doukkala (trafic)", "Marrakech", "trafic", 31.635, -8.000, 1.05, 1.15, .12),
    ("Daoudiate (fond urbain)", "Marrakech", "fond urbain", 31.650, -8.010, .90, .70, .30),
    ("Bensouda (industrielle)", "Fès", "industrielle", 34.050, -5.050, 1.00, .90, .25),
    ("Fès centre (trafic)", "Fès", "trafic", 34.035, -4.995, .95, 1.05, .45),
    ("Tanger ville (fond urbain)", "Tanger", "fond urbain", 35.770, -5.810, .80, .80, .55),
]
NIV_VILLE = {"Casablanca": (62, 48), "Marrakech": (58, 38), "Fès": (52, 34), "Tanger": (42, 32)}


def construire_air():
    st = pd.DataFrame(STATIONS, columns=["station", "ville", "type", "lat", "lon", "k_pm10", "k_no2", "manquant"])
    st[["station", "ville", "type", "lat", "lon"]].assign(
        taux_manquant=st.manquant).to_csv(OUT / "air_stations.csv", index=False, encoding="utf-8")
    jours = pd.date_range("2019-01-01", "2026-11-25")
    DERNIERE_MESURE = pd.Timestamp("2026-11-22")  # au-delà : seule la météo (prévue) est connue
    lignes = []
    for v in NIV_VILLE:
        mv = METEO[METEO.ville == v].set_index("semaine")[["temp_moy_C", "temp_max_C", "pluie_mm"]]
        mv = mv[~mv.index.duplicated()].sort_index()
        # météo journalière : interpolation de la météo hebdomadaire réelle + variabilité journalière
        t = mv.temp_moy_C.reindex(mv.index.union(jours)).interpolate("time").reindex(jours).bfill().ffill()
        tmax = mv.temp_max_C.reindex(mv.index.union(jours)).interpolate("time").reindex(jours).bfill().ffill()
        p_sem = mv.pluie_mm.reindex(jours, method="ffill").fillna(0) / 7
        n = len(jours)
        temp = t.values + rng.normal(0, 1.6, n)
        pluie = np.where(rng.random(n) < np.clip(p_sem.values / 4, 0, .8), rng.gamma(1.2, np.maximum(p_sem.values, .1) * 2.2), 0)
        vent = np.clip(rng.gamma(4, (4.2 if v in ("Casablanca", "Tanger") else 3.0) / 4, n) +
                       (1.2 if v == "Tanger" else 0), .3, None)
        # vent d'est chaud et sec (chergui / poussières sahariennes) : épisodes de 2-5 jours
        poussiere = np.zeros(n)
        i = 0
        while i < n:
            m = jours[i].month
            proba = (.012 if m in (3, 4, 5, 6, 7, 8, 9) else .004) * (1.4 if v in ("Marrakech", "Fès") else 1)
            if rng.random() < proba:
                L = rng.integers(2, 6)
                poussiere[i:i + L] = rng.uniform(.6, 1.0, min(L, n - i))
                i += L
            else:
                i += 1
        temp = temp + 4 * poussiere
        hum = np.clip(70 - 1.1 * (temp - 18) - 25 * poussiere + rng.normal(0, 6, n) + (8 if v != "Marrakech" else -10), 12, 98)
        dow = jours.dayofweek.values
        ram = jours.isin(JOURS_RAMADAN)
        trafic = np.where(dow == 6, .72, np.where(dow == 5, .88, 1.0)) * np.where(ram, .92, 1)
        conf = (jours >= "2020-03-20") & (jours <= "2020-06-10")
        trafic = trafic * np.where(conf, .45, 1) * np.where((jours >= "2020-06-11") & (jours <= "2020-12-31"), .85, 1)
        trafic = trafic * np.where(np.isin(jours.month, [7, 8]), .93 if v != "Tanger" else 1.12, 1)
        tendance = 1 + .012 * (jours.year - 2019 + jours.dayofyear / 365)  # parc automobile croissant
        ventil = 1 / (0.45 + .16 * vent)  # dispersion
        lessivage = np.exp(-.06 * np.minimum(pluie, 30))
        hiver = 1 + .18 * np.cos(2 * np.pi * (jours.dayofyear - 15) / 365)  # inversions de température
        pm_base, no2_base = NIV_VILLE[v]
        for _, s in st[st.ville == v].iterrows():
            ar1, ar2 = 0.0, 0.0
            pm10, no2 = np.zeros(n), np.zeros(n)
            e1, e2 = rng.normal(0, .17, n), rng.normal(0, .14, n)
            for k in range(n):
                ar1 = .55 * ar1 + e1[k]
                ar2 = .50 * ar2 + e2[k]
                pm10[k] = pm_base * s.k_pm10 * ventil[k] * lessivage[k] * hiver[k] * (.6 + .4 * trafic[k]) \
                    * tendance[k] ** .5 * np.exp(ar1) + 160 * poussiere[k] * rng.uniform(.5, 1.2)
                no2[k] = no2_base * s.k_no2 * ventil[k] ** 1.1 * hiver[k] ** 1.3 * trafic[k] ** (1.4 if s.type == "trafic" else 1.0) \
                    * tendance[k] * np.exp(ar2) * lessivage[k] ** .4
            # pannes de capteurs : blocs de jours manquants
            manque = np.zeros(n, bool)
            k = 0
            while k < n:
                if rng.random() < s.manquant / 18:
                    L = rng.integers(5, 40)
                    manque[k:k + L] = True
                    k += L
                else:
                    k += 1
            if s.station.startswith("Tanger") or s.station.startswith("Fès centre"):
                manque[: int(n * .35)] = True  # stations installées plus tard
            manque[jours > DERNIERE_MESURE] = True
            for k in range(n):
                lignes.append((jours[k].strftime("%Y-%m-%d"), v, s.station, s.type,
                               None if manque[k] else round(pm10[k], 1), None if manque[k] else round(no2[k], 1),
                               round(temp[k], 1), round(tmax.values[k] + 4 * poussiere[k], 1), round(pluie[k], 1),
                               round(vent[k], 1), round(hum[k]), int(poussiere[k] > 0), round(trafic[k], 3),
                               int(dow[k] >= 5), int(ram[k])))
    d = pd.DataFrame(lignes, columns=["date", "ville", "station", "type", "pm10", "no2", "temp_moy_C", "temp_max_C",
                                      "pluie_mm", "vent_m_s", "humidite_pct", "episode_poussiere", "indice_trafic",
                                      "week_end", "ramadan"])
    d.to_csv(OUT / "air_journalier.csv", index=False, encoding="utf-8")
    print("Air : PM10 / NO2 moyens ->", d.groupby("ville")[["pm10", "no2"]].mean().round(0).to_dict())
    print("Air : taux de mesures disponibles ->", d.groupby("station").pm10.apply(lambda s: s.notna().mean()).round(2).to_dict())


if __name__ == "__main__":
    t = construire_tourisme()
    construire_dechets(t)
    construire_air()
