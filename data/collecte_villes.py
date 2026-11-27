"""Collecte les articles de presse donnant des prix de gros de fruits/légumes
pour les grandes villes marocaines autres que Casablanca.

Usage : python -I collecte_villes.py <articles_villes.json>
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
SITES = ["medias24.com", "leseco.ma", "h24info.ma", "www.barlamane.com/fr", "fr.hibapress.com", "www.challenge.ma",
         "lavieeco.com", "aujourdhui.ma", "consonews.ma", "www.agrimaroc.ma", "www.maroc-diplomatique.net",
         "www.infomediaire.net", "www.lnt.ma"]
VILLES = {"Rabat": r"Rabat", "Marrakech": r"Marrakech", "Fès": r"F[èe]s\b", "Agadir": r"Agadir|Inezgane",
          "Tanger": r"Tanger", "Meknès": r"Mekn[èe]s", "Oujda": r"Oujda", "Kénitra": r"K[ée]nitra",
          "Tétouan": r"T[ée]touan", "Salé": r"Sal[ée]\b"}


def get(url):
    r = subprocess.run(["curl", "-sL", "-m", "60", "-A", "Mozilla/5.0", url], capture_output=True)
    try:
        return json.loads(r.stdout.decode("utf-8-sig"))
    except Exception:
        return []


posts = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
for ville, rx in VILLES.items():
    before = len(posts)
    nom = ville.replace("è", "e").replace("é", "e")
    for site in SITES:
        for q in [f"marché de gros {nom}", f"prix tomate {nom}", f"prix légumes {nom}"]:
            for page in range(1, 4):
                res = get(f"https://{site}/wp-json/wp/v2/posts?search={urllib.parse.quote(q)}"
                          f"&per_page=100&page={page}&_fields=date,link,title,content")
                if not isinstance(res, list) or not res:
                    break
                for p in res:
                    if p["link"] in posts:
                        continue
                    t = re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", p["content"]["rendered"])))
                    # la ville doit apparaître à moins de 300 caractères d'un prix de légume en DH
                    ok = False
                    for m in re.finditer(rx, t):
                        win = t[max(0, m.start() - 300): m.end() + 300]
                        if re.search(r"tomate|pomme de terre|oignon|carotte", win, re.I) and re.search(r"\d\s*(DH|dirham)", win, re.I):
                            ok = True
                            break
                    if ok:
                        posts[p["link"]] = {"site": site, "date": p["date"], "ville_recherche": ville,
                                            "title": html.unescape(p["title"]["rendered"]), "text": t}
                if len(res) < 100:
                    break
    print(f"{ville}: +{len(posts) - before}", flush=True)
json.dump(posts, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("total", len(posts))
