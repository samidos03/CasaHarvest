import { useMemo } from "react";
import { useApi } from "../api";

/** Carte des 9 préfectures et provinces de Casablanca-Settat (limites geoBoundaries).
 *  couleurs : { province: "#hex" } ; etiquettes : { province: "texte sous le nom" } */
const W = 600;
const NOMS_AR = {
  Casablanca: "الدار البيضاء", Mohammedia: "المحمدية", Settat: "سطات", Berrechid: "برشيد", "El Jadida": "الجديدة",
  "Sidi Bennour": "سيدي بنور", Benslimane: "بنسليمان", Nouaceur: "النواصر", "Médiouna": "مديونة",
};
// position des étiquettes (décalage manuel pour les petites préfectures autour de Casablanca)
const DECALAGE = { Casablanca: [-80, -34], Mohammedia: [10, -44], "Médiouna": [64, 34], Nouaceur: [-78, 34], Benslimane: [26, -14] };

export default function CarteRegion({ couleurs = {}, etiquettes = {}, choix, onChoix, hauteur = 380, arabe = false, legende }) {
  const { data } = useApi("/region/carte");
  const geo = useMemo(() => {
    if (!data) return null;
    const pts = data.flatMap((d) => d.anneau);
    const lo0 = Math.min(...pts.map((p) => p[0])), lo1 = Math.max(...pts.map((p) => p[0]));
    const la0 = Math.min(...pts.map((p) => p[1])), la1 = Math.max(...pts.map((p) => p[1]));
    const k = Math.cos((((la0 + la1) / 2) * Math.PI) / 180);
    const s = (W - 20) / ((lo1 - lo0) * k);
    const H = (la1 - la0) * s + 20;
    const proj = ([lo, la]) => [10 + (lo - lo0) * k * s, 10 + (la1 - la) * s];
    const chemins = {}, centres = {};
    data.forEach((d) => {
      const xy = d.anneau.map(proj);
      chemins[d.province] = (chemins[d.province] || "") + xy.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join("") + "Z";
      const c = centres[d.province] || { x: 0, y: 0, n: 0 };
      xy.forEach(([x, y]) => { c.x += x; c.y += y; c.n += 1; });
      centres[d.province] = c;
    });
    Object.values(centres).forEach((c) => { c.x /= c.n; c.y /= c.n; });
    return { chemins, centres, H };
  }, [data]);
  if (!geo) return <div style={{ height: hauteur }} className="ch-skel" />;
  const ordre = Object.keys(geo.chemins).sort((a, b) => (a === choix) - (b === choix)); // la province choisie au-dessus
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${geo.H}`} style={{ width: "100%", height: hauteur, display: "block" }} role="img" aria-label="Carte de la région Casablanca-Settat">
        <rect width={W} height={geo.H} fill="#eaf3f8" rx="12" />
        {ordre.map((p) => (
          <path key={p} d={geo.chemins[p]} fill={couleurs[p] || "#e9ede7"} stroke={p === choix ? "#14231b" : "#ffffff"}
            strokeWidth={p === choix ? 3 : 1.5} style={{ cursor: onChoix ? "pointer" : "default", transition: "fill .2s" }}
            onClick={() => onChoix && onChoix(p)}>
            <title>{p}{etiquettes[p] ? ` — ${etiquettes[p]}` : ""}</title>
          </path>
        ))}
        {Object.entries(geo.centres).map(([p, c]) => {
          const [dx, dy] = DECALAGE[p] || [0, 0];
          const x = c.x + dx, y = c.y + dy;
          return (
            <g key={p} style={{ pointerEvents: onChoix ? "auto" : "none", cursor: "pointer" }} onClick={() => onChoix && onChoix(p)}>
              {(dx || dy) ? <line x1={c.x} y1={c.y} x2={x} y2={y} stroke="#14231b" strokeWidth="0.8" opacity=".5" /> : null}
              <text x={x} y={y} textAnchor="middle" fontSize={p === choix ? 21 : 19} fontWeight={p === choix ? 800 : 650} fill="#14231b"
                paintOrder="stroke" stroke="#fff" strokeWidth="4.5">{arabe ? NOMS_AR[p] : p}</text>
              {etiquettes[p] && <text x={x} y={y + 20} textAnchor="middle" fontSize="17" fontWeight="600" fill="#33413a"
                paintOrder="stroke" stroke="#fff" strokeWidth="3">{etiquettes[p]}</text>}
            </g>
          );
        })}
      </svg>
      {legende && <div className="ch-legende mt-2">{legende.map(([c, l]) => <span key={l}><i style={{ background: c }} />{l}</span>)}</div>}
    </div>
  );
}

export { NOMS_AR };
