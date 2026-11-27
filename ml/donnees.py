"""Chargement et préparation des données pour les modèles de machine learning.

series_hebdo() : prix de gros hebdomadaires de Casablanca (DH/kg) + variables exogènes
                 (météo du Souss et de Casablanca, calendrier Ramadan / Aïd al-Adha).
"""
import sys
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
sys.path.insert(0, str(DATA))


def series_hebdo():
    """Prix hebdomadaires (semaines × produits), masque des semaines relevées, et variables exogènes par semaine."""
    from modele_prevision import charger_series
    w, observe = charger_series()
    met = pd.read_csv(DATA / "meteo_hebdo_villes.csv", parse_dates=["semaine"])
    cal = pd.read_csv(DATA / "calendrier_fetes.csv", parse_dates=["semaine"]).set_index("semaine")
    souss = met[met.ville == "Agadir"].set_index("semaine")
    casa = met[met.ville == "Casablanca"].set_index("semaine")
    exo = pd.DataFrame({
        "pluie_souss_4s": souss.pluie_mm.rolling(4).sum(),
        "tmax_souss_4s": souss.temp_max_C.rolling(4).mean(),
        "tmin_souss_4s": souss.temp_min_C.rolling(4).mean(),
        "pluie_casa_4s": casa.pluie_mm.rolling(4).sum(),
    }).join(cal)
    return w, observe, exo


FAMILLE_PRODUIT = {"Tomate": "légume", "Pomme de terre": "légume", "Oignon frais": "légume", "Oignon sec": "légume",
                   "Carotte": "légume", "Courgette": "légume", "Aubergine": "légume", "Concombre": "légume",
                   "Chou-fleur": "légume", "Chou blanc": "légume", "Courge": "légume", "Orange": "fruit",
                   "Clémentine": "fruit", "Banane locale": "fruit", "Banane importée": "fruit",
                   "Pomme locale": "fruit", "Pomme importée": "fruit", "Avocat": "fruit",
                   "Viande bovine": "viande", "Viande ovine": "viande"}
