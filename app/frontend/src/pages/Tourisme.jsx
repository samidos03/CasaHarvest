import { useMemo, useState } from "react";
import { Col, Row, Table } from "react-bootstrap";
import {
  Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip,
  XAxis, YAxis,
} from "recharts";
import { COULEURS, moisFr, nf, useApi } from "../api";
import { Choix, Etat, Hero, Jauge, Section } from "../components/Ui";
import CarteSvg from "../components/CarteSvg";

const COORD = { Marrakech: [31.63, -8.01], Agadir: [30.42, -9.6], "Fès": [34.03, -5.0], Essaouira: [31.51, -9.77], Chefchaouen: [35.17, -5.27] };
const NIVEAU = { "élevé": ["ch-pill-bad", COULEURS.rouge], "modéré": ["ch-pill-mid", "#b0721a"], faible: ["ch-pill-ok", COULEURS.vert] };
const MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
const fmtM = (v) => (v >= 1e6 ? `${nf(v / 1e6, 2)} M` : `${nf(v / 1e3, 0)} k`);

function CarteDest({ d, actif, onClick }) {
  const [cls, coul] = NIVEAU[d.niveau] || NIVEAU["modéré"];
  return (
    <div className={`ch-card p-3 h-100 ch-carte-dest ${actif ? "actif" : ""}`} onClick={onClick}>
      <div className="d-flex justify-content-between align-items-start">
        <div className="fw-bold"><i className="bi bi-geo-alt-fill me-1" style={{ color: coul }} />{d.destination}</div>
        <span className={`ch-pill ${cls}`}>{d.niveau}</span>
      </div>
      <div className="fs-4 fw-bold mt-2">{fmtM(d.nuitees_prevues_12m)}</div>
      <div className="small text-secondary">nuitées prévues sur 12 mois <span className={d.croissance_prevue_pct >= 0 ? "ch-baisse" : "ch-hausse"}>{d.croissance_prevue_pct >= 0 ? "+" : ""}{nf(d.croissance_prevue_pct, 1)} %</span></div>
      <div className="small mt-2 d-flex justify-content-between"><span>Occupation au pic</span><b>{nf(d.occupation_pic_prevue_pct, 0)} %</b></div>
      <Jauge v={d.occupation_pic_prevue_pct} couleur={d.occupation_pic_prevue_pct >= 85 ? COULEURS.rouge : d.occupation_pic_prevue_pct >= 70 ? COULEURS.or : COULEURS.vert} />
      <div className="small mt-2 d-flex justify-content-between"><span>Vulnérabilité</span><b>{nf(d.score_vulnerabilite, 0)}/100</b></div>
    </div>
  );
}

function Serie({ dest }) {
  const { data, erreur, chargement } = useApi(`/tourisme/serie?destination=${encodeURIComponent(dest)}`);
  const [depuis, setDepuis] = useState("2022");
  const d = useMemo(() => {
    if (!data) return [];
    const h = data.historique.filter((r) => r.mois >= `${depuis}-01`).map((r) => ({ mois: r.mois, reel: r.nuitees, occ: r.occupation_pct }));
    const last = h[h.length - 1];
    const p = data.prevision.map((r) => ({ mois: r.mois, prevision: r.prevision, bande: [r.bas, r.haut], occp: r.occupation_pct, occh: r.occupation_haut_pct }));
    if (last) p.unshift({ mois: last.mois, prevision: last.reel, bande: [last.reel, last.reel] });
    return [...h.slice(0, -1), { ...last, ...p[0] }, ...p.slice(1)];
  }, [data, depuis]);
  if (!data) return <Etat chargement={chargement} erreur={erreur} hauteur={380} />;
  const p0 = data.prevision[0].mois;
  const debutOcc = `${Number(p0.slice(0, 4)) - 1}-${p0.slice(5)}`;
  const occ = d.map((r) => ({ mois: r.mois, observe: r.occ, prevu: r.occp, haut: r.occh })).filter((r) => r.mois >= debutOcc);
  return (
    <>
      <Section titre={`${dest} — nuitées mensuelles et prévision à 12 mois`} icone="bi-graph-up-arrow">
        <div className="d-flex justify-content-between flex-wrap gap-2 mb-2">
          <div className="ch-legende"><span><i style={{ background: COULEURS.encre }} />observé</span><span><i style={{ background: COULEURS.or }} />prévision (médiane)</span><span><i style={{ background: "#f3dca6" }} />intervalle à 80 %</span></div>
          <Choix options={[["2017", "Depuis 2017"], ["2022", "Depuis 2022"], ["2024", "Depuis 2024"]]} valeur={depuis} onChange={setDepuis} />
        </div>
        <ResponsiveContainer width="100%" height={340}>
          <ComposedChart data={d} margin={{ top: 10, right: 8, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="#eef1ed" vertical={false} />
            <XAxis dataKey="mois" minTickGap={30} tick={{ fontSize: 12 }} tickFormatter={(m) => `${MOIS[+m.slice(5) - 1]} ${m.slice(2, 4)}`} />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={fmtM} width={56} />
            <Tooltip labelFormatter={moisFr} formatter={(v, n) => [Array.isArray(v) ? `${fmtM(v[0])} – ${fmtM(v[1])}` : nf(v, 0), n]} />
            <Area dataKey="bande" name="Intervalle 80 %" stroke="none" fill="#f3dca6" fillOpacity={0.7} isAnimationActive={false} />
            <Line dataKey="reel" name="Nuitées observées" stroke={COULEURS.encre} strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line dataKey="prevision" name="Prévision" stroke={COULEURS.or} strokeWidth={2.4} strokeDasharray="6 3" dot={{ r: 2.5 }} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
        <div className="small text-secondary">Covid : effondrement en 2020-2021, exclu de l'apprentissage. La prévision tient compte du Ramadan (février-mars 2027), des festivals et de la dynamique récente.</div>
      </Section>
      <Row className="g-3 mt-1">
        <Col lg={7}>
          <Section titre="Taux d'occupation des lits : 12 derniers mois et 12 prochains" icone="bi-building">
            <ResponsiveContainer width="100%" height={260}>
              <ComposedChart data={occ} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#eef1ed" vertical={false} />
                <XAxis dataKey="mois" tick={{ fontSize: 11 }} tickFormatter={(m) => `${MOIS[+m.slice(5) - 1]}`} interval={1} />
                <YAxis tick={{ fontSize: 12 }} unit=" %" width={52} domain={[0, (m) => Math.max(100, Math.ceil(m / 10) * 10)]} />
                <Tooltip labelFormatter={moisFr} formatter={(v, n) => [`${nf(v, 0)} %`, n]} />
                <ReferenceLine y={85} stroke={COULEURS.rouge} strokeDasharray="4 4" label={{ value: "saturation (85 %)", position: "insideTopLeft", fontSize: 11, fill: COULEURS.rouge }} />
                <Bar dataKey="observe" name="Observé" fill="#9aa5ad" isAnimationActive={false} />
                <Bar dataKey="prevu" name="Prévu" fill="#e9c46a" isAnimationActive={false}>
                  {occ.map((r) => <Cell key={r.mois} fill={r.haut >= 85 ? "#e08a8d" : "#e9c46a"} />)}
                </Bar>
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </ComposedChart>
            </ResponsiveContainer>
            <div className="small text-secondary">Capacité : {nf(data.lits, 0)} lits classés. Barre rouge : la borne haute de la prévision dépasse 85 % d'occupation — risque de saturation.</div>
          </Section>
        </Col>
        <Col lg={5}>
          <Section titre="Marchés d'origine (12 derniers mois)" icone="bi-airplane">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.marches} layout="vertical" margin={{ top: 0, right: 16, left: 10, bottom: 0 }}>
                <XAxis type="number" tickFormatter={fmtM} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="marche" width={120} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v) => nf(v, 0)} />
                <Bar dataKey="nuitees" name="Nuitées" fill={COULEURS.vert} radius={[0, 4, 4, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </Section>
        </Col>
      </Row>
    </>
  );
}

export default function Tourisme() {
  const dest = useApi("/tourisme/destinations");
  const ev = useApi("/tourisme/evaluation");
  const [choix, setChoix] = useState("Marrakech");
  return (
    <>
      <Hero variante="terre" titre="🧳 Fréquentation touristique"
        texte="Prévoir les nuitées des 12 prochains mois par destination, avec un intervalle d'incertitude, et repérer les villes exposées à la surfréquentation."
        badges={["📍 Marrakech · Agadir · Fès · Essaouira · Chefchaouen", "🗓️ mensuel 2017-2026", "🤖 gradient boosting quantile", "📊 prévision probabiliste"]} />
      <Etat chargement={dest.chargement} erreur={dest.erreur}>
        {dest.data && (
          <>
            <Row className="g-3 mb-3">
              {["Marrakech", "Agadir", "Fès", "Essaouira", "Chefchaouen"].map((n) => {
                const d = dest.data.find((x) => x.destination === n);
                return d && <Col sm={6} lg key={n}><CarteDest d={d} actif={choix === n} onClick={() => setChoix(n)} /></Col>;
              })}
            </Row>
            <Serie dest={choix} />
            <Row className="g-3 mt-1">
              <Col lg={7}>
                <Section titre="Vulnérabilité à la surfréquentation" icone="bi-people">
                  <Table size="sm" hover responsive className="ch-table-compact mb-2">
                    <thead><tr><th>Destination</th><th className="text-end">Occup. pic prévue</th><th className="text-end">Mois saturés</th><th className="text-end">Touristes / 100 hab.</th><th className="text-end">Pic / creux</th><th>1er marché</th><th className="text-end">Score</th></tr></thead>
                    <tbody>{dest.data.map((d) => (
                      <tr key={d.destination} style={{ cursor: "pointer" }} onClick={() => setChoix(d.destination)}>
                        <td className="fw-semibold">{d.destination}</td>
                        <td className="text-end">{nf(d.occupation_pic_prevue_pct, 0)} %</td>
                        <td className="text-end">{d.mois_sature_prevus}</td>
                        <td className="text-end">{nf(d.touristes_pour_100_hab, 1)}</td>
                        <td className="text-end">× {nf(d.ratio_pic_creux, 1)}</td>
                        <td className="ch-nowrap">{d.premier_marche} ({nf(d.part_premier_marche, 0)} %)</td>
                        <td className="text-end"><span className={`ch-pill ${NIVEAU[d.niveau]?.[0]}`}>{nf(d.score_vulnerabilite, 0)}</span></td>
                      </tr>))}
                    </tbody>
                  </Table>
                  <div className="small text-secondary">Score 0-100 = occupation au pic prévue (35 %) + touristes présents pour 100 habitants (30 %) + écart pic/creux (20 %) + dépendance au premier marché (15 %), chaque composante ramenée entre 0 et 1.</div>
                </Section>
              </Col>
              <Col lg={5}>
                <Section titre="Carte des destinations" icone="bi-map">
                  <CarteSvg fondMaroc largeur={460} hauteur={300} bornes={[[29.6, -10.6], [36.0, -3.6]]}
                    points={dest.data.map((d) => ({ lat: COORD[d.destination][0], lon: COORD[d.destination][1], r: 4 + Math.sqrt(d.nuitees_prevues_12m) / 260, taillePolice: 13,
                      couleur: NIVEAU[d.niveau]?.[1], label: d.destination, actif: d.destination === choix, onClick: () => setChoix(d.destination),
                      titre: `${d.destination} : ${fmtM(d.nuitees_prevues_12m)} nuitées prévues` }))} />
                  <div className="ch-legende mt-2"><span><i style={{ background: COULEURS.rouge }} />vulnérabilité élevée</span><span><i style={{ background: "#b0721a" }} />modérée</span><span><i style={{ background: COULEURS.vert }} />faible</span><span>taille = nuitées prévues</span></div>
                </Section>
              </Col>
            </Row>
            <Section titre="Fiabilité : test sur 2 années passées (prévision faite en octobre 2024 et en octobre 2025)" icone="bi-clipboard-data" className="mt-3">
              <Etat chargement={ev.chargement} erreur={ev.erreur}>
                {ev.data && (
                  <Row className="g-3">
                    <Col lg={7}>
                      <Table size="sm" className="ch-table-compact mb-0">
                        <thead><tr><th>Destination</th><th className="text-end">Erreur modèle</th><th className="text-end">Même mois l'an passé</th><th className="text-end">+ tendance récente</th><th className="text-end">Couverture 80 %</th></tr></thead>
                        <tbody>{ev.data.metriques.map((m) => (
                          <tr key={m.destination} className={m.destination === "Toutes" ? "fw-bold" : ""}>
                            <td>{m.destination}</td><td className="text-end">{nf(m.mape_modele, 1)} %</td>
                            <td className="text-end">{nf(m.mape_naif_saisonnier, 1)} %</td><td className="text-end">{nf(m.mape_naif_tendance, 1)} %</td>
                            <td className="text-end">{nf(m.couverture_80, 0)} %</td></tr>))}
                        </tbody>
                      </Table>
                    </Col>
                    <Col lg={5}>
                      <div className="ch-note">
                        Erreur moyenne de <b>{nf(ev.data.metriques.at(-1).mape_modele, 1)} %</b> sur les 12 mois suivants, contre {nf(ev.data.metriques.at(-1).mape_naif_saisonnier, 1)} % en recopiant l'année passée.
                        Les intervalles bruts étaient trop étroits ; une <b>calibration conforme</b> les élargit (couverture testée sur 2025-26 :
                        {" "}{nf(ev.data.calibration.couverture_brute_2025, 0)} % → {nf(ev.data.calibration.couverture_calibree_2025, 0)} %).
                        Avec seulement deux années de test, ces chiffres restent indicatifs.
                      </div>
                    </Col>
                  </Row>
                )}
              </Etat>
            </Section>
          </>
        )}
      </Etat>
    </>
  );
}
