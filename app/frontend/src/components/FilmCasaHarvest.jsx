import { useEffect, useRef, useState } from "react";
import { nf } from "../api";
import AUDIO from "../film_audio.json";

/**
 * Petit dessin animé (SVG animé en JavaScript) : « De l'eau à la récolte, de la récolte au marché ».
 * 4 scènes : la pluie sur le champ de Haj Mustapha, la récolte, le camion vers le marché de gros de Casablanca,
 * Allaoui qui arrive en taxi. Voix off en darija enregistrée d'un seul tenant (public/audio/film_voix.mp3) :
 * le film est calé sur elle (app/caler_audio_film.py). Personnages et décors originaux.
 */
const SCENES = [
  { titre: "L'eau", icone: "💧" },
  { titre: "La récolte", icone: "🌾" },
  { titre: "Le marché", icone: "🧺" },
  { titre: "Allaoui", icone: "🚕" },
];
// chronologie : début et fin de chaque réplique dans la piste de voix off (calculés par app/caler_audio_film.py)
const PISTE = AUDIO.piste;
const DUREE_VOIX = AUDIO.duree;
const TOTAL = DUREE_VOIX + 2;  // 2 s de plus pour laisser l'écran final
const LIGNES = AUDIO.repliques.map((l, i, arr) => ({ ...l, fin: i === arr.length - 1 ? TOTAL : l.fin }));
const BORNES = SCENES.map((_, k) => {
  const ls = LIGNES.filter((l) => l.scene === k);
  return { debut: ls[0].debut, fin: ls[ls.length - 1].fin };
});
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const ease = (x) => { const c = clamp(x); return c < 0.5 ? 2 * c * c : 1 - (-2 * c + 2) ** 2 / 2; };
const seg = (p, a, b) => clamp((p - a) / (b - a));

/* ------------------------------------------------------------------ personnages */
function HajMustapha({ x, y, s = 1, bras = 0, tablette = false }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <ellipse cx="0" cy="118" rx="34" ry="6" fill="#000" opacity=".12" />
      <rect x="-14" y="92" width="10" height="24" rx="4" fill="#5b4636" />
      <rect x="4" y="92" width="10" height="24" rx="4" fill="#5b4636" />
      <path d="M-30 30 Q0 18 30 30 L36 100 Q0 108 -36 100 Z" fill="#d9c8a6" stroke="#b9a37c" strokeWidth="1.5" />
      <path d="M-6 30 L0 100 L6 30" fill="none" stroke="#b9a37c" strokeWidth="1.5" />
      <g transform={`rotate(${-bras} 26 38)`}>
        <rect x="22" y="34" width="11" height="40" rx="5" fill="#d9c8a6" stroke="#b9a37c" strokeWidth="1.2" />
        <circle cx="27.5" cy="76" r="6" fill="#c58b5f" />
        {tablette && <rect x="18" y="66" width="30" height="22" rx="3" fill="#1f2a24" stroke="#fff" strokeWidth="2" />}
        {tablette && <rect x="21" y="69" width="24" height="16" rx="1.5" fill="#7fd1a5" />}
      </g>
      <rect x="-33" y="34" width="11" height="38" rx="5" fill="#d9c8a6" stroke="#b9a37c" strokeWidth="1.2" />
      <circle cx="0" cy="8" r="20" fill="#c58b5f" />
      <path d="M-15 14 Q0 36 15 14 Q12 22 0 24 Q-12 22 -15 14" fill="#f1f1ef" />
      <circle cx="-7" cy="5" r="2.2" fill="#2b1d14" />
      <circle cx="7" cy="5" r="2.2" fill="#2b1d14" />
      <path d="M-6 14 Q0 18 6 14" stroke="#7a4b30" strokeWidth="1.6" fill="none" />
      <ellipse cx="0" cy="-10" rx="32" ry="7" fill="#e3c26a" />
      <path d="M-17 -10 Q0 -34 17 -10 Z" fill="#e8ca76" />
      <rect x="-17" y="-14" width="34" height="4" fill="#9b2c2c" />
    </g>
  );
}

function Taxi({ x, y, s = 1, roue = 0, allaoui = true }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <ellipse cx="80" cy="74" rx="92" ry="7" fill="#000" opacity=".15" />
      <path d="M0 52 L8 30 Q12 22 24 22 L58 22 L72 4 Q76 0 84 0 L128 0 Q136 0 140 6 L152 22 L166 24 Q176 26 176 36 L176 56 Q176 62 170 62 L6 62 Q0 62 0 56 Z" fill="#c8302e" stroke="#8f1f1d" strokeWidth="2" />
      <path d="M78 6 L86 4 L126 4 L138 22 L68 22 Z" fill="#cfe6f5" stroke="#8f1f1d" strokeWidth="1.5" />
      <line x1="104" y1="4" x2="104" y2="22" stroke="#8f1f1d" strokeWidth="2" />
      {allaoui && (
        <g>
          <circle cx="120" cy="13" r="8" fill="#b9825a" />
          <path d="M112 9 Q120 1 128 9" fill="#2b1d14" />
          <path d="M115 16 Q120 18 125 16" stroke="#2b1d14" strokeWidth="1.8" fill="none" />
          <rect x="114" y="18" width="12" height="4" fill="#3d5a80" />
        </g>
      )}
      <rect x="92" y="-14" width="30" height="13" rx="3" fill="#f2c94c" stroke="#8f1f1d" strokeWidth="1.5" />
      <text x="107" y="-4" textAnchor="middle" fontSize="9" fontWeight="700" fill="#5c1210">TAXI</text>
      <rect x="0" y="40" width="176" height="5" fill="#e9e9e9" opacity=".7" />
      <circle cx="168" cy="38" r="4" fill="#fff6c9" />
      {[38, 140].map((cx) => (
        <g key={cx} transform={`rotate(${roue} ${cx} 62)`}>
          <circle cx={cx} cy="62" r="13" fill="#222" />
          <circle cx={cx} cy="62" r="6" fill="#bbb" />
          <line x1={cx - 6} y1="62" x2={cx + 6} y2="62" stroke="#666" strokeWidth="2" />
        </g>
      ))}
    </g>
  );
}

function Camion({ x, y, roue = 0, caisses = 6 }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <ellipse cx="95" cy="78" rx="105" ry="7" fill="#000" opacity=".15" />
      <rect x="0" y="20" width="140" height="48" rx="4" fill="#2f7d4f" stroke="#1f5a37" strokeWidth="2" />
      {Array.from({ length: caisses }, (_, i) => (
        <g key={i} transform={`translate(${8 + (i % 4) * 32} ${i < 4 ? 4 : -16})`}>
          <rect width="28" height="18" rx="2" fill="#b88a4a" stroke="#7d5a2b" />
          <circle cx="8" cy="5" r="5" fill="#d63a2f" /><circle cx="19" cy="5" r="5" fill="#e04a3a" />
        </g>
      ))}
      <path d="M140 30 L172 30 Q180 30 184 38 L196 54 L196 68 L140 68 Z" fill="#e8e3d3" stroke="#9b947c" strokeWidth="2" />
      <path d="M150 36 L172 36 L182 52 L150 52 Z" fill="#cfe6f5" />
      {[30, 160].map((cx) => (
        <g key={cx} transform={`rotate(${roue} ${cx} 68)`}>
          <circle cx={cx} cy="68" r="13" fill="#222" /><circle cx={cx} cy="68" r="5" fill="#bbb" />
          <line x1={cx - 6} y1="68" x2={cx + 6} y2="68" stroke="#666" strokeWidth="2" />
        </g>
      ))}
    </g>
  );
}

/* ------------------------------------------------------------------ décors */
function Ciel({ couleur = "#bfe3f7", soleil = true, x = 820 }) {
  return (
    <g>
      <rect width="960" height="400" fill={couleur} />
      {soleil && <circle cx={x} cy="70" r="38" fill="#ffd45e" opacity=".95" />}
    </g>
  );
}
const Nuage = ({ x, y, s = 1, c = "#fff" }) => (
  <g transform={`translate(${x} ${y}) scale(${s})`} fill={c}>
    <ellipse cx="0" cy="0" rx="46" ry="22" /><ellipse cx="38" cy="-10" rx="34" ry="24" /><ellipse cx="74" cy="2" rx="38" ry="20" />
  </g>
);

function Ville({ x = 600 }) {
  const imm = [[0, 120], [44, 170], [96, 140], [150, 200], [214, 130], [262, 160], [318, 110]];
  return (
    <g transform={`translate(${x} 0)`}>
      {imm.map(([dx, h], i) => (
        <g key={i}>
          <rect x={dx} y={290 - h} width="48" height={h} fill={i % 2 ? "#e9edf1" : "#dfe5ea"} stroke="#c7cfd6" />
          {Array.from({ length: Math.floor(h / 30) }, (_, k) => (
            <rect key={k} x={dx + 10} y={300 - h + k * 28} width="28" height="10" fill="#b9d3e6" opacity=".8" />
          ))}
        </g>
      ))}
      <rect x="380" y="110" width="22" height="180" fill="#e6dccb" stroke="#c9bba2" />
      <rect x="376" y="100" width="30" height="14" fill="#2f7d4f" />
      <circle cx="391" cy="92" r="6" fill="#d4a017" />
    </g>
  );
}

function Marche({ x = 560, tableau = 0, prix }) {
  return (
    <g transform={`translate(${x} 0)`}>
      <rect x="0" y="150" width="340" height="140" fill="#f4ead6" stroke="#cdb98f" strokeWidth="2" />
      <path d="M-10 150 L170 96 L350 150 Z" fill="#c8302e" />
      <text x="170" y="138" textAnchor="middle" fontSize="15" fontWeight="700" fill="#5c1210">سوق الجملة · MARCHÉ DE GROS</text>
      {[20, 120, 220].map((dx) => (
        <g key={dx}>
          <path d={`M${dx} 200 L${dx + 100} 200 L${dx + 92} 182 L${dx + 8} 182 Z`} fill={dx === 120 ? "#2f7d4f" : "#e0a100"} />
          <rect x={dx + 6} y="200" width="88" height="44" fill="#b88a4a" stroke="#7d5a2b" />
          {Array.from({ length: 6 }, (_, i) => (
            <circle key={i} cx={dx + 18 + i * 13} cy="212" r="6"
              fill={dx === 120 ? "#c9a227" : dx === 20 ? "#d63a2f" : "#8a5a2b"} />
          ))}
        </g>
      ))}
      {tableau > 0 && (
        <g opacity={tableau} transform={`translate(70 ${20 + (1 - tableau) * 20})`}>
          <rect width="200" height="64" rx="8" fill="#1f2a24" stroke="#fff" strokeWidth="3" />
          <text x="100" y="24" textAnchor="middle" fontSize="15" fill="#fff">🍅 Tomate · prix de gros</text>
          <text x="100" y="50" textAnchor="middle" fontSize="18" fontWeight="700" fill="#7fd1a5">
            {prix ? `${nf(prix.avant)} → ${nf(prix.apres)} DH` : "…"}
          </text>
        </g>
      )}
    </g>
  );
}

/* ------------------------------------------------------------------ scènes */
function Scene1({ p }) {
  const pluie = seg(p, 0.1, 0.75);
  const pousse = ease(seg(p, 0.35, 1));
  return (
    <g>
      <Ciel couleur={pluie > 0 && p < 0.85 ? "#a9c4d6" : "#bfe3f7"} soleil={p > 0.82} />
      <Nuage x={180 + p * 60} y={70} s={1.1} c="#8fa3b3" />
      <Nuage x={480 + p * 40} y={55} s={1.3} c="#9eb0bf" />
      <Nuage x={720 - p * 30} y={85} c="#a8b9c6" />
      {pluie > 0 && p < 0.85 && Array.from({ length: 70 }, (_, i) => {
        const dx = (i * 137) % 960, y0 = (i * 53) % 220;
        const y = 100 + ((y0 + p * 900) % 220);
        return <line key={i} x1={dx} y1={y} x2={dx - 4} y2={y + 14} stroke="#4a90c2" strokeWidth="2" opacity=".7" />;
      })}
      <rect x="0" y="290" width="960" height="110" fill="#8a5a34" />
      {Array.from({ length: 6 }, (_, r) => (
        <rect key={r} x="0" y={300 + r * 16} width="960" height="5" fill="#74492a" />
      ))}
      {Array.from({ length: 22 }, (_, i) => {
        const x = 300 + i * 30, h = 8 + 26 * pousse;
        return (
          <g key={i} transform={`translate(${x} ${300 + (i % 3) * 16})`}>
            <path d={`M0 0 Q-4 ${-h / 2} 0 ${-h}`} stroke="#4c9a3f" strokeWidth="3" fill="none" />
            <ellipse cx={-5} cy={-h * 0.6} rx="6" ry="3" fill="#5fb14d" transform={`rotate(-30 -5 ${-h * 0.6})`} />
            <ellipse cx={5} cy={-h * 0.8} rx="6" ry="3" fill="#5fb14d" transform={`rotate(30 5 ${-h * 0.8})`} />
          </g>
        );
      })}
      <HajMustapha x={150} y={180} s={1.05} bras={10 + Math.sin(p * 12) * 6} tablette />
      <g opacity={seg(p, 0.55, 0.7)} transform="translate(30 30)">
        <rect width="230" height="56" rx="12" fill="#fff" stroke="#0b7a43" strokeWidth="2" />
        <text x="16" y="24" fontSize="14" fill="#33413a">💧 Indice de sécheresse</text>
        <text x="16" y="44" fontSize="15" fontWeight="700" fill="#0b7a43">SPI-6 mars 2026 : +1,9 (humide)</text>
      </g>
    </g>
  );
}

function Scene2({ p, rec }) {
  const or = ease(seg(p, 0, 0.5));
  const c = (a, b) => Math.round(a + (b - a) * or);
  const ble = `rgb(${c(95, 222)},${c(177, 184)},${c(77, 68)})`;
  return (
    <g>
      <Ciel couleur="#cfeaf8" x={760} />
      <Nuage x={120} y={70} /><Nuage x={430} y={50} s={0.8} />
      <rect x="0" y="250" width="960" height="150" fill="#c9a24a" />
      {Array.from({ length: 48 }, (_, i) => {
        const x = 10 + (i % 24) * 40, y = i < 24 ? 280 : 330;
        const ondule = Math.sin(p * 10 + i) * 4;
        return (
          <g key={i} transform={`translate(${x} ${y})`}>
            <path d={`M0 30 Q${ondule} 0 ${ondule * 1.5} -26`} stroke={ble} strokeWidth="3" fill="none" />
            <ellipse cx={ondule * 1.5} cy="-32" rx="5" ry="11" fill={ble} />
          </g>
        );
      })}
      <HajMustapha x={140} y={150} s={1.05} bras={60 * ease(seg(p, 0.45, 0.6))} />
      <Camion x={600 - 30 * ease(seg(p, 0, 0.3))} y={200} caisses={Math.round(6 * ease(seg(p, 0.3, 0.9)))} />
      <g opacity={seg(p, 0.5, 0.65)} transform="translate(560 40)">
        <rect width="360" height="70" rx="14" fill="#fff" stroke="#0b7a43" strokeWidth="2" />
        <text x="20" y="28" fontSize="15" fill="#33413a">🌾 Récolte de céréales prévue en 2026</text>
        <text x="20" y="54" fontSize="20" fontWeight="700" fill="#0b7a43">
          {rec ? `${nf(rec, 1)} millions de quintaux` : "…"}
        </text>
      </g>
    </g>
  );
}

function Scene3({ p, prix }) {
  const x = -220 + 640 * ease(seg(p, 0, 0.75));
  return (
    <g>
      <Ciel couleur="#d6eefb" x={150} />
      <Nuage x={300 - p * 40} y={60} s={0.9} />
      <Ville x={600} />
      <rect x="0" y="290" width="960" height="110" fill="#6b7570" />
      {Array.from({ length: 12 }, (_, i) => (
        <rect key={i} x={((i * 90 - p * 600) % 1080 + 1080) % 1080 - 60} y="338" width="50" height="6" fill="#f3f3f3" />
      ))}
      <rect x="0" y="282" width="960" height="10" fill="#9aa5ad" />
      <g transform="translate(40 215)">
        <rect x="0" y="0" width="150" height="48" rx="6" fill="#0b7a43" />
        <text x="75" y="20" textAnchor="middle" fontSize="13" fontWeight="700" fill="#fff">الدار البيضاء ←</text>
        <text x="75" y="38" textAnchor="middle" fontSize="12" fill="#fff">Casablanca 70 km</text>
        <rect x="70" y="48" width="8" height="30" fill="#666" />
      </g>
      <Camion x={x} y={250} roue={p * 1400} />
      <g opacity={seg(p, 0.6, 0.75)}>
        <Marche x={590} tableau={seg(p, 0.65, 0.85)} prix={prix} />
      </g>
    </g>
  );
}

function Scene4({ p, prix, f7 = 0.4, f8 = 0.72 }) {
  // f7 / f8 : début (en fraction de la scène) de la réplique d'Allaoui et de la phrase finale
  const xt = 960 - 520 * ease(seg(p, 0, Math.min(0.35, f7)));
  const fin = seg(p, f8, f8 + 0.12);
  return (
    <g>
      <Ciel couleur="#d6eefb" x={880} />
      <Nuage x={600} y={70} s={0.8} />
      <Marche x={40} tableau={1} prix={prix} />
      <rect x="0" y="290" width="960" height="110" fill="#8e979c" />
      <rect x="0" y="282" width="960" height="10" fill="#b4bcc1" />
      <Taxi x={xt} y={262} s={1.15} roue={-p * 1800} />
      {p > f7 - 0.02 && p < f8 && Array.from({ length: 3 }, (_, i) => {
        const q = seg(p, f7 + i * 0.07, f7 + 0.2 + i * 0.07);
        return q > 0 && q < 1 && <text key={i} x={500 - 240 * q} y={250 - 60 * Math.sin(q * Math.PI)} fontSize="26">🪙</text>;
      })}
      <g opacity={seg(p, f7, f7 + 0.1) * (1 - fin)} transform="translate(560 120)">
        <rect width="230" height="62" rx="14" fill="#fff" stroke="#b0721a" strokeWidth="2" />
        <text x="16" y="26" fontSize="14" fill="#33413a">📱 Allaoui consulte CasaHarvest</text>
        <text x="16" y="48" fontSize="15" fontWeight="700" fill="#b0721a">La tomate va baisser ✔</text>
      </g>
      {fin > 0 && (
        <g opacity={fin}>
          <rect width="960" height="400" fill="#0b7a43" opacity=".88" />
          <text x="480" y="170" textAnchor="middle" fontSize="44" fontWeight="800" fill="#fff">🌾 CasaHarvest</text>
          <text x="480" y="220" textAnchor="middle" fontSize="22" fill="#e7f3ec">من الماء إلى الحصاد، ومن الحصاد إلى السوق</text>
          <text x="480" y="256" textAnchor="middle" fontSize="20" fill="#e7f3ec">De l'eau à la récolte, de la récolte au marché</text>
        </g>
      )}
    </g>
  );
}

export default function FilmCasaHarvest({ resume }) {
  const reduit = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const [t, setT] = useState(0);
  const [lecture, setLecture] = useState(!reduit);
  const [son, setSon] = useState(false);
  const der = useRef(null);
  const audio = useRef(null);
  const tRef = useRef(0);
  tRef.current = t;

  // horloge : quand la voix joue, c'est elle qui donne l'heure ; sinon (son coupé, ou écran final) temps réel
  useEffect(() => {
    if (!lecture) return undefined;
    der.current = performance.now();
    const id = setInterval(() => {
      const ts = performance.now();
      const a = audio.current;
      if (son && a && !a.paused && !a.ended) {
        setT(a.currentTime);
      } else {
        setT((v) => {
          const nv = v + Math.min(ts - der.current, 1000) / 1000;
          if (nv < TOTAL) return nv;
          if (son && a) { a.currentTime = 0; a.play().catch(() => {}); }  // le film recommence
          return 0;
        });
      }
      der.current = ts;
    }, 40);
    return () => clearInterval(id);
  }, [lecture, son]);

  // la voix suit la lecture, la pause et le son
  useEffect(() => {
    const a = audio.current;
    if (!a) return;
    if (son && lecture && tRef.current < DUREE_VOIX - 0.1) {
      if (Math.abs(a.currentTime - tRef.current) > 0.3) a.currentTime = tRef.current;
      a.play().catch(() => setSon(false));
    } else {
      a.pause();
    }
  }, [son, lecture]);

  const aller = (nt) => {
    setT(nt);
    const a = audio.current;
    if (a && son && nt < DUREE_VOIX - 0.1) { a.currentTime = nt; if (lecture) a.play().catch(() => {}); }
  };
  const iLigne = Math.max(0, LIGNES.findIndex((l) => t >= l.debut && t < l.fin));
  const ligne = LIGNES[iLigne];
  const k = ligne.scene;
  const b = BORNES[k];
  const p = (t - b.debut) / (b.fin - b.debut);

  const prix = resume ? { avant: resume.prix.tomate, apres: resume.prix.tomate_4sem } : null;
  const rec = resume?.rendement.production_Mqx;
  const duree = b.fin - b.debut;
  const fondu = Math.min(1, p / (0.4 / duree), (1 - p) / (0.4 / duree));
  const l3 = LIGNES.filter((l) => l.scene === 3);
  const f7 = (l3[1].debut - b.debut) / duree, f8 = (l3[2].debut - b.debut) / duree;
  const Sc = [Scene1, Scene2, Scene3, Scene4][k];

  return (
    <div className="ch-card ch-film overflow-hidden">
      <audio ref={audio} src={PISTE} preload="auto" />
      <div className="ch-film-ecran">
        <svg viewBox="0 0 960 400" width="100%" role="img" aria-label="Dessin animé : de l'eau à la récolte, de la récolte au marché">
          <g opacity={k === 3 && p > f8 ? 1 : fondu}><Sc p={p} prix={prix} rec={rec} f7={f7} f8={f8} /></g>
        </svg>
        <div className="ch-film-sous-titre">
          <div className="fr">{ligne.personnage === "haj" ? "Haj Mustapha : " : ligne.personnage === "allaoui" ? "Allaoui : " : ""}{ligne.fr}</div>
        </div>
        {!lecture && (
          <button type="button" className="ch-film-gros-play" onClick={() => setLecture(true)} aria-label="Lire le film">
            <i className="bi bi-play-fill" />
          </button>
        )}
        {!son && (
          <button type="button" className="ch-film-son" onClick={() => { setSon(true); setLecture(true); aller(b.debut); }}>
            <i className="bi bi-volume-up-fill me-1" /> Activer le son (darija)
          </button>
        )}
      </div>
      <div className="ch-film-barre">
        <button type="button" className="btn btn-sm btn-primary" onClick={() => setLecture((v) => !v)} aria-label={lecture ? "Pause" : "Lecture"}>
          <i className={`bi ${lecture ? "bi-pause-fill" : "bi-play-fill"}`} />
        </button>
        <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => { aller(0); setLecture(true); }} aria-label="Recommencer">
          <i className="bi bi-arrow-counterclockwise" />
        </button>
        <button type="button" className={`btn btn-sm ${son ? "btn-primary" : "btn-outline-primary"}`} onClick={() => setSon((v) => !v)}
          aria-label={son ? "Couper le son" : "Activer le son"}>
          <i className={`bi ${son ? "bi-volume-up-fill" : "bi-volume-mute-fill"}`} />
        </button>
        <div className="ch-film-progression" onClick={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          aller(clamp((e.clientX - r.left) / r.width) * TOTAL * 0.999);
        }}>
          <div className="ch-film-rempli" style={{ width: `${(t / TOTAL) * 100}%` }} />
          {BORNES.slice(1).map((bo) => <span key={bo.debut} className="ch-film-cran" style={{ left: `${(bo.debut / TOTAL) * 100}%` }} />)}
        </div>
        <span className="small text-secondary text-nowrap">{Math.floor(t)} / {Math.round(TOTAL)} s</span>
      </div>
      <div className="ch-film-chapitres">
        {SCENES.map((s, i) => (
          <button type="button" key={s.titre} className={`btn btn-sm ${i === k ? "btn-primary" : "btn-light"}`}
            onClick={() => { aller(BORNES[i].debut + 0.01); setLecture(true); }}>
            {s.icone} {i + 1}. {s.titre}
          </button>
        ))}
        <span className="small text-secondary ms-auto align-self-center">Voix off en darija (ElevenLabs)</span>
      </div>
    </div>
  );
}
