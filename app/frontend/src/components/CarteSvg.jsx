import { useEffect, useMemo, useState } from "react";

/** Petite carte vectorielle sans fond de tuiles (fonctionne hors ligne).
 *  points : [{ lat, lon, r, couleur, label, titre, onClick, actif }]
 *  traces : [{ coords: [[lat, lon], ...], couleur, epaisseur, tirets }]
 *  fondMaroc : dessine les provinces du Maroc (public/carte-maroc.json)
 *  bornes : [[latMin, lonMin], [latMax, lonMax]] (sinon calculées) */
let CACHE_MAROC = null;

export default function CarteSvg({ points = [], traces = [], fondMaroc = false, bornes, hauteur = 420, marge = 0.08, largeur = 1000 }) {
  const [maroc, setMaroc] = useState(CACHE_MAROC);
  useEffect(() => {
    if (!fondMaroc || CACHE_MAROC) return;
    fetch("/carte-maroc.json").then((r) => r.json()).then((d) => { CACHE_MAROC = d; setMaroc(d); }).catch(() => {});
  }, [fondMaroc]);

  const W = largeur;
  const { proj, H } = useMemo(() => {
    let la0, lo0, la1, lo1;
    if (bornes) [[la0, lo0], [la1, lo1]] = bornes;
    else {
      const all = [...points.map((p) => [p.lat, p.lon]), ...traces.flatMap((t) => t.coords)];
      la0 = Math.min(...all.map((c) => c[0])); la1 = Math.max(...all.map((c) => c[0]));
      lo0 = Math.min(...all.map((c) => c[1])); lo1 = Math.max(...all.map((c) => c[1]));
      const dl = (la1 - la0) * marge + 0.002, dn = (lo1 - lo0) * marge + 0.002;
      la0 -= dl; la1 += dl; lo0 -= dn; lo1 += dn;
    }
    const k = Math.cos((((la0 + la1) / 2) * Math.PI) / 180);
    const larg = (lo1 - lo0) * k, haut = la1 - la0;
    const H = Math.max(W * 0.26, Math.min(W * 0.9, (W * haut) / larg));
    const s = Math.min(W / larg, H / haut);
    const ox = (W - larg * s) / 2, oy = (H - haut * s) / 2;
    return { H, proj: (lat, lon) => [ox + (lon - lo0) * k * s, oy + (la1 - lat) * s] };
  }, [points, traces, bornes, marge, W]);

  const chemin = (coords) => coords.map(([la, lo], i) => `${i ? "L" : "M"}${proj(la, lo).map((v) => v.toFixed(1)).join(",")}`).join("");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: hauteur, display: "block" }} className="ch-carte" role="img">
      <rect width={W} height={H} fill={fondMaroc ? "#eaf3f8" : "#f7f9f6"} />
      {!fondMaroc && Array.from({ length: 11 }, (_, i) => (
        <g key={i} stroke="#e6ebe5" strokeWidth="1">
          <line x1={(i * W) / 10} x2={(i * W) / 10} y1="0" y2={H} />
          <line y1={(i * H) / 10} y2={(i * H) / 10} x1="0" x2={W} />
        </g>
      ))}
      {fondMaroc && maroc && maroc.map((r, i) => (
        <path key={i} d={chemin(r.map(([lo, la]) => [la, lo])) + "Z"} fill="#fbfaf5" stroke="#cfd8cf" strokeWidth="0.8" />
      ))}
      {traces.map((t, i) => (
        <path key={i} d={chemin(t.coords)} fill="none" stroke={t.couleur || "#0b7a43"} strokeWidth={t.epaisseur || 2}
          strokeDasharray={t.tirets || undefined} strokeLinejoin="round" strokeLinecap="round" opacity={t.opacite ?? 0.85} />
      ))}
      {points.map((p, i) => {
        const [x, y] = proj(p.lat, p.lon);
        return (
          <g key={i} onClick={p.onClick} style={{ cursor: p.onClick ? "pointer" : "default" }}>
            {p.titre && <title>{p.titre}</title>}
            <circle cx={x} cy={y} r={p.r || 6} fill={p.couleur || "#0b7a43"} fillOpacity={p.opacite ?? 0.85}
              stroke={p.actif ? "#1f2a24" : "#fff"} strokeWidth={p.actif ? 3 : 1.5} />
            {p.forme === "depot" && <rect x={x - 8} y={y - 8} width="16" height="16" fill="#1f2a24" rx="3" />}
            {p.label && (
              <text x={x + (p.r || 6) + 5} y={y + 4} fontSize={p.taillePolice || 15} fontWeight="600" fill="#1f2a24"
                paintOrder="stroke" stroke="#fff" strokeWidth="4">{p.label}</text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
