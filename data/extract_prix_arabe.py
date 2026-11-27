"""Extrait les prix de gros (DH/kg) des articles en arabe, par marché (Casablanca, Inezgane, ...).

Usage : python -I extract_prix_arabe.py <articles_ar.json> <sortie.csv>

Règles :
  - le texte est découpé en propositions (. ، ؛ ! ?) ; le produit courant se prolonge d'une proposition à l'autre ;
  - le marché courant est le dernier marché de gros cité (« الدار البيضاء للخدمات », « سوق الجملة ... بإنزكان », ...) ;
  - une proposition qui parle du détail (التقسيط, المستهلك, الأسواق الشعبية...) est ignorée ;
  - « بين X و Y درهم » -> min/max ; « من X إلى Y » -> Y ; « سقف / الأقصى / لا يتجاوز ... X » -> max ;
    « X دراهم » seul -> prix moyen ; prix « par caisse » (لكل صندوق) ignorés.
"""
import json
import re
import sys
from datetime import date, timedelta

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

PRODUITS = [  # (nom, racine sans l'article) — les formes composées avant les formes simples
    ("Oignon frais", r"بصل الأخضر"), ("Oignon sec", r"بصل"),
    ("Banane locale", r"موز (?:المحلي|المغربي|الوطني)"), ("Banane importée", r"موز المستورد"),
    ("Pomme locale", r"تفاح (?:المحلي|المغربي|الوطني)"), ("Pomme importée", r"تفاح المستورد"),
    ("Courgette", r"قرع الأخضر|قرعة الخضراء|كورجيت|كوريجيت"), ("Courge", r"يقطين|قرع الأحمر|قرعة الحمراء"),
    ("Pastèque", r"بطيخ الأحمر|دلاح"), ("Melon", r"بطيخ الأصفر|سويهلة|شمام"),
    ("Haricot vert", r"لوبيا الخضراء|فاصوليا الخضراء|فاصولياء|فصولياء|فاصوليا|لوبيا"),
    ("Viande bovine", r"لحوم الأبقار|لحم البقر|لحوم البقر|لحوم العجل|لحم العجل"),
    ("Viande ovine", r"لحوم الأغنام|لحم الغنم|لحوم الغنم"),
    ("Tomate", r"طماطم"), ("Pomme de terre", r"بطاطس|بطاطا"), ("Carotte", r"جزر"),
    ("Aubergine", r"باذنجان|بادنجان"), ("Concombre", r"خيار"), ("Chou-fleur", r"شيفلور|قرنبيط"),
    ("Chou blanc", r"ملفوف|كرنب"), ("Poivron", r"فلفل"), ("Petit pois", r"جلبانة|بازلاء"), ("Fève", r"فول"),
    ("Orange", r"برتقال"), ("Clémentine", r"يوسفي|كليمونتين|ماندرين|مندرين"),
    ("Poire", r"إجاص|اجاص|بوعويد"), ("Raisin", r"عنب"), ("Avocat", r"أفوكادو|أفوكا|افوكا|أفوكاتو"),
    ("Grenade", r"رمان"), ("Fraise", r"فراولة|فريز"), ("Datte", r"تمور|تمر"),
    # produits non suivis ou ambigus : ils « absorbent » les prix qui les suivent (valeurs écartées)
    ("_autre", r"قرع|موز|تفاح|بطيخ|دجاج|دواجن|بيض|سمك|سردين|كراث|بورو|لفت|خوخ|مشمش|أناناس|كيوي|حامض|"
               r"سلاوي|نيورا|كرموس|تين|لحوم|محروقات|غازوال|صندوق"),
]
PREF = r"(?<!\w)(?:و|ف)?(?:ال|بال|كال|لل)"
PROD_RE = re.compile("|".join(f"(?P<p{i}>{PREF}(?:{rx})(?!\\w))" for i, (_, rx) in enumerate(PRODUITS)))
NAMES = [n for n, _ in PRODUITS]

MARCHES = [
    ("Casablanca", r"الدار البيضاء للخدمات|(?:سوق|أسواق) الجملة[^.،]{0,40}(?:ب|في )?الدار البيضاء|البيضاوي"),
    ("Inezgane (Agadir)", r"إنزكان|انزكان|إنزگان"),
    ("Agadir", r"(?:سوق|أسواق) الجملة[^.،]{0,40}(?:ب|في )?أكادير"),
    ("Meknès", r"(?:سوق|أسواق) الجملة[^.،]{0,40}(?:ب|في )?مكناس"),
    ("Fès", r"(?:سوق|أسواق) الجملة[^.،]{0,40}(?:ب|في )?فاس"),
    ("Marrakech", r"(?:سوق|أسواق) الجملة[^.،]{0,40}(?:ب|في )?مراكش"),
    ("Rabat", r"(?:سوق|أسواق) الجملة[^.،]{0,40}(?:ب|في )?الرباط"),
    ("Tanger", r"(?:سوق|أسواق) الجملة[^.،]{0,40}(?:ب|في )?طنجة"),
    ("Oujda", r"(?:سوق|أسواق) الجملة[^.،]{0,40}(?:ب|في )?وجدة"),
]
DETAIL = re.compile(r"التقسيط|بالتقسيط|المستهلك|الأسواق النهائية|السوق النهائية|الأسواق الشعبية|الأحياء|"
                    r"نقاط البيع|نقط البيع|الأسواق الأسبوعية|المحلات|الأسواق الأسبوعية|الدكاكين|الباعة|"
                    r"الأسواق الممتازة|المتاجر|المساحات التجارية|الأسواق المغربية")
NUM = r"(\d{1,3}(?:[.,]\d{1,2})?)"
UNIT = r"\s*(?:درهما|دراهم|درهم)"
KG = r"(?:\s*(?:لل|ل)?(?:كيلوغرام|كيلوغراما|كيلو|كلغ)(?: الواحد)?)?"
NOT_CAISSE = r"(?!\s*(?:لكل|لل|ل)\s*(?:صندوق|طن|قنطار))"
CHANGE = re.compile(r"زياد|ارتفاع|ارتفع|تراجع|انخفاض|انخفض|ناهز|بفارق|فارق|هامش")
PLAFOND = r"يصل إلى|تصل إلى|بما يصل|حدود|سقف|أقصى|الأقصى|يلامس|تلامس|لامس|لا يتجاوز|لم يتجاوز|لا تتجاوز|لم تتجاوز|لا يزيد|لم يكن"
MOTS = {"درهم واحد": "1 درهم", "درهمين": "2 دراهم", "درهمان": "2 دراهم", "ثلاثة دراهم": "3 دراهم",
        "أربعة دراهم": "4 دراهم", "خمسة دراهم": "5 دراهم", "ستة دراهم": "6 دراهم", "سبعة دراهم": "7 دراهم",
        "ثمانية دراهم": "8 دراهم", "تسعة دراهم": "9 دراهم", "عشرة دراهم": "10 دراهم"}


def norm(t):
    t = t.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789."))
    t = re.sub("[ً-ْـ]", "", t)  # diacritiques et tatweel
    for k, v in MOTS.items():
        t = t.replace(k, v)
    # « 4 دراهم ونصف (الدرهم) » -> 4.5 دراهم
    t = re.sub(NUM + UNIT + r" ونصف(?: الدرهم)?", lambda m: f"{float(m.group(1).replace(',', '.')) + 0.5:g} دراهم", t)
    return t


def f(x):
    return float(x.replace(",", "."))


def extract(text, defaut=None):
    """defaut : marché d'un site régional (ex. Kech24 -> Marrakech), utilisé quand l'article parle
    du « marché de gros » sans nommer la ville."""
    text = norm(text)
    out = {}   # (marché, produit) -> {min, max, moy}
    cur = None
    marche = None
    for cl in re.split(r"(?<!\d)[.](?!\d)|[،؛!?:]|\s-\s", text):
        for nom, rx in MARCHES:
            if re.search(rx, cl):
                marche = nom
        if marche is None and defaut and re.search(r"سوق الجملة|أسواق الجملة|بالجملة", cl):
            marche = defaut
        detail = bool(DETAIL.search(cl)) and not re.search(r"بالجملة|سوق الجملة|أسواق الجملة", cl)
        events = [(m.start(), "prod", NAMES[int(next(k for k, v in m.groupdict().items() if v)[1:])])
                  for m in PROD_RE.finditer(cl)]
        events += [(m.start(), "import", None) for m in re.finditer(r"(?<!موز )(?<!تفاح )(?:ال)?مستورد", cl)]
        U = UNIT + KG
        pats = [
            (r"بين\s*" + NUM + r"(?:" + U + r")?\s*و\s*" + NUM + U + NOT_CAISSE, "range"),
            (r"من\s*" + NUM + r"(?:" + U + r")?\s*إلى\s*" + NUM + U + NOT_CAISSE, "to"),
            (r"(?<![\d.,])" + NUM + U + NOT_CAISSE, "single"),
        ]
        spans = []
        for rx, kind in pats:
            for m in re.finditer(rx, cl):
                if any(a <= m.start() < b for a, b in spans):
                    continue  # nombre déjà pris par un motif plus spécifique
                if re.search(r"(?:لكل|لل|ل)\s*(?:صندوق|طن|قنطار)|للصندوق", cl[m.end():m.end() + 25]):
                    continue  # prix par caisse / tonne
                spans.append((m.start(), m.end()))
                avant = cl[max(0, m.start() - 35):m.start()]
                if kind == "single":
                    if CHANGE.search(cl) and (re.search(r"بنحو|بحوالي|بما يقارب|بما يناهز|بنسبة|بزيادة", avant) or
                                              not re.search(r"(?:إلى|ليصل|لتصل|ليبلغ|لتبلغ|عند|ليستقر|لتستقر)\s*$", avant)):
                        continue  # « a augmenté de 2 DH » : une variation, pas un prix
                    if re.search(r"متوسط", avant):
                        kind = "moyenne"
                    elif re.search(PLAFOND, avant):
                        kind = "max"
                events.append((m.start(), kind, [g for g in m.groups() if g]))
        events.sort(key=lambda e: e[0])
        for _, kind, val in events:
            if kind == "prod":
                cur = val
                continue
            if kind == "import":
                if cur and cur.endswith("locale"):
                    cur = cur.replace("locale", "importée")
                continue
            if cur is None or cur == "_autre" or marche is None or detail:
                continue
            rec = out.setdefault((marche, cur), {})
            if kind == "range":
                rec.update(min=f(val[0]), max=f(val[1]), moy=None, src="fourchette")
            elif kind == "to":
                rec.update(min=None, max=None, moy=f(val[1]), src="valeur")
            elif kind == "moyenne" and rec.get("src") != "fourchette":
                rec.update(min=None, max=None, moy=f(val[0]), src="moyenne")
            elif kind == "max" and "src" not in rec:
                rec.update(max=f(val[0]), src="plafond")
            elif kind == "single" and "src" not in rec:
                rec.update(moy=f(val[0]), src="valeur")
    clean = {}
    for (mk, p), r in out.items():
        lim = 200 if p.startswith("Viande") else 60
        lo, hi, mo = r.get("min"), r.get("max"), r.get("moy")
        ok = lambda v: v is not None and 0.2 <= v <= lim
        lo, hi, mo = (lo if ok(lo) else None), (hi if ok(hi) else None), (mo if ok(mo) else None)
        if lo is not None and hi is not None:
            if lo > hi or hi / lo > 8:
                continue  # fourchette incohérente
            mo = round((lo + hi) / 2, 2)
        if lo is None and hi is None and mo is None:
            continue
        clean[(mk, p)] = (lo, hi, mo, r["src"])
    return clean


SITE_VILLE = {"kech24.com": "Marrakech", "www.agadir24.info": "Inezgane (Agadir)",
              "www.sabahagadir.ma": "Inezgane (Agadir)", "www.tanja24.com": "Tanger", "oujdacity.net": "Oujda",
              "www.fesnews.media": "Fès"}


def semaine(pub):
    d = date.fromisoformat(pub[:10])
    return d - timedelta(days=(d.weekday() - 2) % 7)  # mercredi précédent (ou le jour même)


def main():
    arts = json.load(open(sys.argv[1], encoding="utf-8"))
    rows = []
    for link, a in arts.items():
        for (mk, p), (lo, hi, mo, typ) in extract(a["text"], SITE_VILLE.get(a["site"])).items():
            rows.append({"semaine": semaine(a["date"]).isoformat(), "date_publication": a["date"][:10],
                         "marche": mk, "produit": p, "prix_min_DH_kg": lo, "prix_max_DH_kg": hi,
                         "prix_moyen_DH_kg": mo, "type_valeur": typ, "source": a["site"], "url": link,
                         "langue": "ar"})
    df = pd.DataFrame(rows)
    # garder les articles qui donnent vraiment une grille de prix (≥ 2 produits pour un marché)
    n = df.groupby(["url", "marche"]).produit.transform("nunique")
    df = df[n >= 2].copy()
    df["n"] = df.groupby(["url", "marche"]).produit.transform("nunique")
    # même semaine / marché / produit : l'article le plus complet, de préférence avec une fourchette
    df["has_range"] = df.prix_min_DH_kg.notna()
    df = (df.sort_values(["has_range", "n"], ascending=False)
            .drop_duplicates(["semaine", "marche", "produit"]).drop(columns=["n", "has_range"])
            .sort_values(["marche", "produit", "semaine"]))
    df.to_csv(sys.argv[2], index=False, encoding="utf-8-sig")
    print("lignes", len(df), "| semaines par marché :")
    print(df.groupby("marche").semaine.nunique().sort_values(ascending=False).to_string())
    print(df.groupby(["marche", "produit"]).size().sort_values(ascending=False).head(25).to_string())


if __name__ == "__main__":
    main()
