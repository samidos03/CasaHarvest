"""Collecte les articles de presse marocaine en arabe donnant des prix de gros de fruits et légumes
(marchés de gros de Casablanca, Inezgane et autres villes), via l'API WordPress des sites.

Usage : python -I collecte_arabe.py <articles_ar.json> [site1 site2 ...]   (le fichier est complété s'il existe)
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
SITES = sys.argv[2:] or ["www.hespress.com", "www.alyaoum24.com", "www.barlamane.com", "www.febrayer.com"]
QUERIES = [
    "الدار البيضاء للخدمات أسعار",
    "سوق الجملة للخضر والفواكه بالدار البيضاء",
    "سوق الجملة الدار البيضاء الطماطم",
    "سوق الجملة بإنزكان",
    "سوق الجملة إنزكان الطماطم",
    "أسعار الخضر سوق الجملة",
    "أسعار الخضر والفواكه بالجملة",
    "النشرة الأسبوعية أسعار الخضر",
    "أسعار الطماطم سوق الجملة",
    "أسعار البصل سوق الجملة",
    "أسعار البطاطس سوق الجملة",
    "سوق الجملة بمكناس", "سوق الجملة بفاس", "سوق الجملة بمراكش", "سوق الجملة بالرباط",
    "سوق الجملة بطنجة", "سوق الجملة بوجدة", "سوق الجملة بأكادير",
    "سوق الجملة للخضر والفواكه", "أثمنة الخضر بسوق الجملة", "ثمن الطماطم بالجملة", "أسعار الخضر بالجملة",
]
PROD = r"الطماطم|البطاطس|البطاطا|البصل|الجزر|الباذنجان|الخيار|الموز|البرتقال|التفاح"


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
                      f"&per_page=100&page={page}&_fields=date,link,title,content")
            if not isinstance(res, list) or not res:
                break
            for p in res:
                if not isinstance(p, dict) or p.get("link") in posts or "rendered" not in (p.get("content") or {}):
                    continue
                t = re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", p["content"]["rendered"])))
                if (re.search(r"سوق الجملة|أسواق الجملة|بالجملة", t) and re.search(PROD, t)
                        and re.search(r"(درهم|دراهم)", t)):
                    posts[p["link"]] = {"site": site, "date": p["date"],
                                        "title": html.unescape(p["title"]["rendered"]), "text": t}
            if len(res) < 100:
                break
        json.dump(posts, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{site}: +{len(posts) - before}", flush=True)
print("total", len(posts))
