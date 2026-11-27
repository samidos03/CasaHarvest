# Script audio du film d'accueil CasaHarvest

Voix off : enregistrement ElevenLabs (voix « Roger »), d'un seul tenant : `frontend/public/audio/film_voix.mp3`.
Pour changer la voix : remplacer ce fichier (même texte, une courte pause entre les phrases), puis lancer
`python -I caler_audio_film.py` (repère les phrases dans l'audio) et recompiler l'interface (`npm run build` dans `frontend/`).
Pour changer le texte : modifier aussi la liste `REPLIQUES` dans `caler_audio_film.py`.

| N° | Scène | Qui parle | Sens (français) | Darija actuelle (à corriger) |
|---|---|---|---|---|
| 1 | 1 · L'eau | Haj Mustapha | La pluie est bien arrivée cette année, la terre a bu. | الشتا جات مزيانة هاد العام، والأرض شربات. |
| 2 | 1 · L'eau | Haj Mustapha | L'application me dit : pas de sécheresse ce mois-ci. | التطبيق كيقول ليا: ماكاينش الجفاف هاد الشهر. |
| 3 | 2 · La récolte | Haj Mustapha | Le blé devient doré, la récolte s'annonce bonne. | الزرع ولّى ذهبي، والمحصول غادي يكون مزيان. |
| 4 | 2 · La récolte | Narrateur | Prévision : plus de 26 millions de quintaux dans la région Casablanca-Settat. | التوقعات: أكثر من ستة وعشرين مليون قنطار فجهة الدار البيضاء سطات. |
| 5 | 3 · Le marché | Narrateur | Les légumes voyagent du champ jusqu'au marché de gros de Casablanca. | الخضرة كتمشي من الفلاح، حتى لسوق الجملة فالدار البيضاء. |
| 6 | 3 · Le marché | Narrateur | Au marché, l'intelligence artificielle prévoit le prix des semaines à venir. | وفي السوق، الذكاء الاصطناعي كيتوقع الثمن ديال الأسابيع الجاية. |
| 7 | 4 · Allaoui | Narrateur | Allaoui, chauffeur de taxi, passe au marché. | علاوي، مول الطاكسي، كيدوز للسوق. |
| 8 | 4 · Allaoui | Allaoui | Maintenant je comprends pourquoi les prix montent et descendent ! | دابا فهمت علاش الثمن كيطلع وكينزل! |
| 9 | 4 · Allaoui | Narrateur | L'un sème, l'autre achète, mais tous deux sont reliés par la même chaîne. | واحد كيزرع، وواحد كيشري، ولكن بجوج مرتبطين بنفس السلسلة. |
