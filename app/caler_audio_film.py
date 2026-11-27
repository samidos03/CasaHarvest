"""Cale le film d'accueil sur une voix off enregistrée d'un seul tenant (ex. ElevenLabs).

1. ffmpeg repère les silences de l'enregistrement -> des passages de parole ;
2. les passages sont regroupés en 9 répliques (programmation dynamique) : la durée de chaque groupe doit être
   proportionnelle à la longueur du texte de la réplique (une virgule peut créer une pause à l'intérieur d'une phrase) ;
3. écrit frontend/src/film_audio.json (début et fin de chaque réplique dans la piste).

Usage : python -I caler_audio_film.py [frontend/public/audio/film_voix.mp3]
Ensuite : cd frontend && npm run build
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ICI = Path(__file__).resolve().parent
PISTE = Path(sys.argv[1]) if len(sys.argv) > 1 else ICI / "frontend" / "public" / "audio" / "film_voix.mp3"

REPLIQUES = [  # (scène, personnage, darija, français)
    (0, "haj", "الشتا جات مزيانة هاد العام، والأرض شربات.", "La pluie est bien arrivée cette année, la terre a bu."),
    (0, "haj", "التطبيق كيقول ليا: ماكاينش الجفاف هاد الشهر.", "L'application me dit : pas de sécheresse ce mois-ci."),
    (1, "haj", "الزرع ولّى ذهبي، والمحصول غادي يكون مزيان.", "Le blé devient doré, la récolte s'annonce bonne."),
    (1, "narrateur", "التوقعات: أكثر من ستة وعشرين مليون قنطار فجهة الدار البيضاء سطات.",
     "Prévision : plus de 26 millions de quintaux dans la région Casablanca-Settat."),
    (2, "narrateur", "الخضرة كتمشي من الفلاح، حتى لسوق الجملة فالدار البيضاء.",
     "Les légumes voyagent du champ jusqu'au marché de gros de Casablanca."),
    (2, "narrateur", "وفي السوق، الذكاء الاصطناعي كيتوقع الثمن ديال الأسابيع الجاية.",
     "Au marché, l'intelligence artificielle prévoit le prix des semaines à venir."),
    (3, "narrateur", "علاوي، مول الطاكسي، كيدوز للسوق.", "Allaoui, chauffeur de taxi, passe au marché."),
    (3, "allaoui", "دابا فهمت علاش الثمن كيطلع وكينزل!", "Maintenant je comprends pourquoi les prix montent et descendent !"),
    (3, "narrateur", "واحد كيزرع، وواحد كيشري، ولكن بجوج مرتبطين بنفس السلسلة.",
     "L'un sème, l'autre achète, mais tous deux sont reliés par la même chaîne."),
]

duree = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(PISTE)],
                             capture_output=True, text=True).stdout)
log = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(PISTE), "-af", "silencedetect=noise=-35dB:d=0.25", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
debuts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
fins = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
# passages de parole entre les silences
bords = [0.0] + [v for pair in zip(debuts, fins) for v in pair] + [duree]
passages = [(bords[i], bords[i + 1]) for i in range(0, len(bords) - 1, 2) if bords[i + 1] - bords[i] > 0.15]
print(f"piste {duree:.1f} s, {len(passages)} passages de parole")

# regroupement optimal : groupe j de passages contigus <-> réplique j
n, m = len(REPLIQUES), len(passages)
if m < n:
    sys.exit(f"Seulement {m} passages pour {n} répliques : vérifier l'enregistrement (pauses entre les phrases).")
poids = [len(r[2]) for r in REPLIQUES]
parole = sum(b - a for a, b in passages)
cible = [parole * w / sum(poids) for w in poids]
INF = float("inf")
cout = [[INF] * (m + 1) for _ in range(n + 1)]
choix = [[0] * (m + 1) for _ in range(n + 1)]
cout[0][0] = 0
for j in range(1, n + 1):
    for k in range(j, m + 1):
        for i in range(j - 1, k):
            if cout[j - 1][i] == INF:
                continue
            d = sum(b - a for a, b in passages[i:k])
            c = cout[j - 1][i] + (d - cible[j - 1]) ** 2
            if c < cout[j][k]:
                cout[j][k], choix[j][k] = c, i
groupes, k = [], m
for j in range(n, 0, -1):
    i = choix[j][k]
    groupes.append((i, k))
    k = i
groupes.reverse()

sortie = []
for j, ((i, k), (scene, perso, ar, fr)) in enumerate(zip(groupes, REPLIQUES)):
    a, b = passages[i][0], passages[k - 1][1]
    # bascule des sous-titres au milieu du silence qui sépare deux répliques
    debut = 0.0 if j == 0 else round((sortie[-1]["fin_voix"] + a) / 2, 2)
    if sortie:
        sortie[-1]["fin"] = debut
    sortie.append({"scene": scene, "personnage": perso, "ar": ar, "fr": fr, "debut": debut, "fin": None,
                   "debut_voix": round(a, 2), "fin_voix": round(b, 2)})
    print(f"{j + 1}. {a:5.2f} -> {b:5.2f} s  ({k - i} passage(s))  {ar}")
sortie[-1]["fin"] = round(duree, 2)
json.dump({"piste": "/audio/" + PISTE.name, "duree": round(duree, 2), "repliques": sortie},
          open(ICI / "frontend" / "src" / "film_audio.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("écrit : frontend/src/film_audio.json")
