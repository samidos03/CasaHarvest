"""Extrait les prix de gros hebdomadaires (Casablanca, bulletins Casa Prestations)
depuis les articles de presse (H24info, Challenge) collectés via l'API WordPress.

Usage : python -I extract_prix_presse.py <articles.json> <dossier_sortie>

Règles d'extraction (phrase par phrase, valeur rattachée au dernier produit cité) :
  - "produit (a–b DH/kg)" ou "produit : a à b DH"   -> min = a, max = b
  - "entre a et b DH"                               -> min = a, max = b
  - "plancher ... de a à b" / "plancher ... à b"    -> min = b (nouvelle valeur)
  - "plafond ... de c à d"  / "plafond ... à d"     -> max = d
  - "plancher/plafond stable à x"                   -> min/max = x
La date retenue est le mercredi (jour du bulletin) de la semaine de publication,
sauf si l'article cite explicitement une date "du/au <jour> <mois>".
"""
import json
import re
import sys
from datetime import date, timedelta

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

PRODUITS = {
    "Tomate": r"tomates?",
    "Pomme de terre": r"pommes? de terre",
    "Oignon frais": r"oignons? frais|oignons? vert",
    "Oignon sec": r"oignons? secs?",
    "Carotte": r"carottes?",
    "Courgette": r"courgettes?",
    "Aubergine": r"aubergines?",
    "Concombre": r"concombres?",
    "Chou-fleur": r"choux?[- ]fleurs?",
    "Chou blanc": r"choux? blancs?",
    "Courge": r"courges?",
    "Haricot vert": r"haricots? verts?",
    "Poivron": r"poivrons?",
    "Petit pois": r"petits? pois",
    "Fève": r"fèves?",
    "Orange": r"oranges?",
    "Clémentine": r"clémentines?|mandarines?",
    "Banane locale": r"bananes? locales?",
    "Banane importée": r"bananes? importées?",
    "Pomme locale": r"pommes? locales?",
    "Pomme importée": r"pommes? importées?",
    "Poire": r"poires?",
    "Raisin": r"raisins?",
    "Pastèque": r"pastèques?",
    "Melon": r"melons?",
    "Avocat": r"avocats?",
    "Grenade": r"grenades?",
    "Fraise": r"fraises?",
    "Datte": r"dattes?",
    "Viande bovine": r"viandes? bovines?|bovins?",
    "Viande ovine": r"viandes? ovines?|ovins?",
}
PROD_RE = re.compile("|".join(f"(?P<p{i}>\\b(?:{rx})\\b)" for i, rx in enumerate(PRODUITS.values())), re.I)
NAMES = list(PRODUITS)
NUM = r"(\d{1,3}(?:[.,]\d{1,2})?)"
MOIS = {m: i for i, m in enumerate(["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                                     "août", "septembre", "octobre", "novembre", "décembre"], 1)}


def f(x):
    return float(x.replace(",", "."))


def bulletin_date(pub, text):
    d = date.fromisoformat(pub[:10])
    m = re.search(r"(?:du|au|ce mercredi|mercredi|en date du)\s+(\d{1,2})(?:er)?\s+(" + "|".join(MOIS) + r")(?:\s+(20\d\d))?",
                  text, re.I)
    if m:
        y = int(m.group(3)) if m.group(3) else d.year
        try:
            cand = date(y, MOIS[m.group(2).lower()], int(m.group(1)))
            if timedelta(0) <= d - cand <= timedelta(10):
                return cand
        except ValueError:
            pass
    return d - timedelta(days=(d.weekday() - 2) % 7)  # mercredi de la semaine


def extract(text):
    # tirets insécables / typographiques -> tiret simple (ex. "chou‑fleur")
    text = re.sub("[‐‑‒­]", "-", text).replace(" ", " ").replace("\xa0", " ")
    out = {}
    cur = None  # le produit courant se prolonge à la phrase suivante ("Le plancher passe de ...")
    for sent in re.split(r"(?<=[.;!?])\s+(?=[A-ZÀ-Ý])", text):
        events = []  # (position, kind, values)
        for m in PROD_RE.finditer(sent):
            idx = int(next(k for k, v in m.groupdict().items() if v)[1:])
            events.append((m.start(), "prod", NAMES[idx]))
        # ellipse : "les pommes locales ... , les importées entre 12 et 22 DH"
        for m in re.finditer(r"\bles importées\b", sent, re.I):
            events.append((m.start(), "importees", None))
        UNIT = r"\s*(?:DH|dirhams?|MAD)"
        pats = [
            # "2,00–5,50 DH/kg", "(2,00-5,50 dirhams)", ": 2 à 5,50 DH"
            (NUM + r"\s*(?:–|—|-)\s*" + NUM + UNIT, "range"),
            (r"[(:]\s*" + NUM + r"\s*à\s*" + NUM + UNIT, "range"),
            (r"entre\s+" + NUM + r"\s*(?:DH(?:/kg)?|dirhams?)?\s+et\s+" + NUM + UNIT, "range"),
            (r"plancher[^.;]{0,80}?(?:de\s+" + NUM + r"\s*(?:DH(?:/kg)?)?\s*)?(?:à|a)\s+" + NUM, "min"),
            (r"plafond[^.;]{0,80}?(?:de\s+" + NUM + r"\s*(?:DH(?:/kg)?)?\s*)?(?:à|a)\s+" + NUM, "max"),
            (r"minimum[^.;]{0,60}?(?:à|a)\s+" + NUM + r"()", "min1"),
            (r"maximum[^.;]{0,60}?(?:à|a)\s+" + NUM + r"()", "max1"),
        ]
        for rx, kind in pats:
            for m in re.finditer(rx, sent, re.I):
                g = [x for x in m.groups() if x]
                events.append((m.start(), kind, g))
        events.sort(key=lambda e: e[0])
        for _, kind, val in events:
            if kind == "prod":
                cur = val
                continue
            if kind == "importees":
                if cur and cur.endswith("locale"):
                    cur = cur.replace("locale", "importée")
                continue
            if cur is None:
                continue
            rec = out.setdefault(cur, {})
            try:
                if kind == "range" and len(val) >= 2:
                    # "passe de a–b à c–d" : la dernière fourchette citée est la nouvelle
                    rec["min"], rec["max"] = f(val[0]), f(val[1])
                    rec["range"] = True
                elif kind in ("min", "min1") and not rec.get("range"):
                    rec.setdefault("min", f(val[-1]))
                elif kind in ("max", "max1") and not rec.get("range"):
                    rec.setdefault("max", f(val[-1]))
            except ValueError:
                pass
    # cohérence
    clean = {}
    for p, r in out.items():
        lo, hi = r.get("min"), r.get("max")
        lim = 200 if p.startswith("Viande") else 60
        if lo is not None and not (0.2 <= lo <= lim):
            lo = None
        if hi is not None and not (0.2 <= hi <= lim):
            hi = None
        if lo is not None and hi is not None and lo > hi:
            lo = hi = None
        if lo is not None or hi is not None:
            clean[p] = (lo, hi)
    return clean


def main():
    arts = json.load(open(sys.argv[1], encoding="utf-8"))
    rows = []
    for link, a in arts.items():
        t = a["text"]
        if not re.search(r"Casablanca", t):
            continue
        d = bulletin_date(a["date"], t)
        for p, (lo, hi) in extract(t).items():
            rows.append({"date_bulletin": d.isoformat(), "date_publication": a["date"][:10], "produit": p,
                         "prix_min_DH_kg": lo, "prix_max_DH_kg": hi, "source": a["site"], "url": link})
    df = pd.DataFrame(rows)
    # un article = un bulletin ; si plusieurs articles pour la même semaine, on garde le plus complet
    n_prod = df.groupby("url").produit.nunique()
    df["n"] = df.url.map(n_prod)
    df = df[df.n >= 3]  # articles qui listent vraiment la grille (≥ 3 produits)
    df = (df.sort_values("n", ascending=False)
            .drop_duplicates(["date_bulletin", "produit"])
            .drop(columns="n").sort_values(["produit", "date_bulletin"]))
    # moyenne seulement si min et max sont connus tous les deux
    df["prix_moyen_DH_kg"] = df[["prix_min_DH_kg", "prix_max_DH_kg"]].mean(axis=1, skipna=False).round(2)
    out = sys.argv[2]
    df.to_csv(f"{out}/prix_gros_casablanca_hebdo_long.csv", index=False, encoding="utf-8-sig")
    wide = df.pivot_table(index="date_bulletin", columns="produit", values="prix_moyen_DH_kg")
    wide.to_csv(f"{out}/prix_gros_casablanca_hebdo.csv", encoding="utf-8-sig")
    print("lignes", len(df), "semaines", df.date_bulletin.nunique(), df.date_bulletin.min(), "->", df.date_bulletin.max())
    print(df.groupby("produit").date_bulletin.count().sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()
