"""Météo hebdomadaire des villes marocaines (Open-Meteo, archive ERA5, gratuit, sans clé)
+ calendrier Ramadan / Aïd al-Adha.

Semaine = 7 jours se terminant le mercredi (jour du bulletin de Casablanca).
Usage : python -I collecte_meteo.py
"""
import json
import subprocess
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
DEBUT, FIN = "2017-01-01", "2026-11-11"
VILLES = {  # coordonnées approximatives du centre-ville
    "Casablanca": (33.57, -7.59), "Rabat": (34.02, -6.84), "Fès": (34.03, -5.00), "Marrakech": (31.63, -8.01),
    "Agadir": (30.42, -9.60), "Tanger": (35.76, -5.83), "Meknès": (33.89, -5.55), "Oujda": (34.68, -1.91),
    "Kénitra": (34.26, -6.58), "Tétouan": (35.57, -5.37), "Laâyoune": (27.15, -13.20), "Dakhla": (23.68, -15.96),
    "Guelmim": (28.99, -10.06), "Settat": (33.00, -7.62), "Safi": (32.30, -9.24), "Béni Mellal": (32.34, -6.36),
    "Al Hoceima": (35.25, -3.93), "Errachidia": (31.93, -4.42),
}
# dates approximatives (± 1 jour selon l'observation du croissant au Maroc)
RAMADAN = ["2017-05-27", "2018-05-17", "2019-05-07", "2020-04-25", "2021-04-14", "2022-04-03",
           "2023-03-23", "2024-03-12", "2025-03-02", "2026-02-19"]
AID_ADHA = ["2017-09-01", "2018-08-22", "2019-08-12", "2020-07-31", "2021-07-21", "2022-07-10",
            "2023-06-29", "2024-06-17", "2025-06-07", "2026-05-27"]

lat = ",".join(str(v[0]) for v in VILLES.values())
lon = ",".join(str(v[1]) for v in VILLES.values())
url = (f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={DEBUT}"
       f"&end_date={FIN}&daily=temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum"
       f"&timezone=Africa%2FCasablanca")
r = subprocess.run(["curl", "-sL", "-m", "300", url], capture_output=True)
data = json.loads(r.stdout)
if isinstance(data, dict):
    data = [data]
frames = []
for ville, d in zip(VILLES, data):
    df = pd.DataFrame(d["daily"])
    df["time"] = pd.to_datetime(df["time"])
    w = df.set_index("time").resample("W-WED").agg({"temperature_2m_mean": "mean", "temperature_2m_max": "max",
                                                     "temperature_2m_min": "min", "precipitation_sum": "sum"})
    w = w.rename(columns={"temperature_2m_mean": "temp_moy_C", "temperature_2m_max": "temp_max_C",
                          "temperature_2m_min": "temp_min_C", "precipitation_sum": "pluie_mm"}).round(1)
    w.insert(0, "ville", ville)
    frames.append(w)
met = pd.concat(frames).reset_index().rename(columns={"time": "semaine"})


def drapeau(semaines, debuts, duree):
    out = pd.Series(0, index=semaines)
    for d in pd.to_datetime(debuts):
        fin = d + pd.Timedelta(days=duree - 1)
        # la semaine (jeudi -> mercredi) chevauche la période
        out[(semaines - pd.Timedelta(days=6) <= fin) & (semaines >= d)] = 1
    return out.values


sem = pd.date_range(DEBUT, FIN, freq="W-WED")
cal = pd.DataFrame({"semaine": sem})
cal["ramadan"] = drapeau(sem, RAMADAN, 30)
cal["semaine_avant_ramadan"] = drapeau(sem, [str(pd.Timestamp(x) - pd.Timedelta(days=7))[:10] for x in RAMADAN], 7)
cal["aid_al_adha"] = drapeau(sem, AID_ADHA, 3)
cal["semaine_avant_aid"] = drapeau(sem, [str(pd.Timestamp(x) - pd.Timedelta(days=7))[:10] for x in AID_ADHA], 7)

met["semaine"] = met.semaine.dt.strftime("%Y-%m-%d")
cal["semaine"] = cal.semaine.dt.strftime("%Y-%m-%d")
met.to_csv("meteo_hebdo_villes.csv", index=False, encoding="utf-8-sig")
cal.to_csv("calendrier_fetes.csv", index=False, encoding="utf-8-sig")
print(met.shape, met.semaine.min(), "->", met.semaine.max(), met.ville.nunique(), "villes")
print(met[met.ville == "Agadir"].tail(3).to_string(index=False))
print(cal[cal.ramadan == 1].head(6).to_string(index=False))
