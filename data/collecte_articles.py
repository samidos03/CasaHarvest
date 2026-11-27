"""Collecte les articles de presse marocains qui reprennent le bulletin hebdomadaire
des prix du marché de gros de Casablanca (Casa Prestations), via l'API WordPress des sites.

Usage : python -I collecte_articles.py <articles.json>
(le fichier est complété s'il existe déjà)
"""
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")
OUT = sys.argv[1]

SITES = ["h24info.ma", "www.challenge.ma", "medias24.com", "leseco.ma", "lavieeco.com", "aujourdhui.ma",
         "www.maroc-diplomatique.net", "www.barlamane.com/fr", "fr.hibapress.com", "consonews.ma",
         "www.agrimaroc.ma", "www.infomediaire.net", "www.lnt.ma", "www.libe.ma"]
SITES = sys.argv[2:] or SITES  # sites passés en argument (optionnel)
QUERIES = ["marché de gros casablanca", "denrées alimentaires casablanca", "prix tomate casablanca",
           "casa prestations", "casablanca prestations", "prix de gros fruits légumes", "bulletin hebdomadaire prix",
           "prix des légumes casablanca", "viande rouge casablanca"]


def get(url):
    r = subprocess.run(["curl", "-sL", "-m", "60", "-A", "Mozilla/5.0", url], capture_output=True)
    try:
        return json.loads(r.stdout.decode("utf-8-sig"))
    except Exception:
        return []


posts = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
for site in SITES:
    before = len(posts)
    for q in QUERIES:
        for page in range(1, 11):
            res = get(f"https://{site}/wp-json/wp/v2/posts?search={urllib.parse.quote(q)}"
                      f"&per_page=100&page={page}&_fields=id,date,link,title,content")
            if not isinstance(res, list) or not res:
                break
            for p in res:
                if p["link"] in posts:
                    continue
                txt = html.unescape(re.sub("<[^>]+>", " ", p["content"]["rendered"]))
                txt = re.sub(r"\s+", " ", txt)
                if (re.search(r"Casablanca", txt) and re.search(r"tomate|pomme de terre|oignon", txt, re.I)
                        and re.search(r"\d\s*(DH|dirham)", txt, re.I) and re.search(r"gros", txt, re.I)):
                    posts[p["link"]] = {"site": site, "date": p["date"],
                                        "title": html.unescape(p["title"]["rendered"]), "text": txt}
            if len(res) < 100:
                break
    print(f"{site}: +{len(posts) - before}")
json.dump(posts, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("total articles", len(posts))
