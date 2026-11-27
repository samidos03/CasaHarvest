import { useMemo, useState } from "react";
import { Badge, Col, Row, Table } from "react-bootstrap";
import { Area, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { COULEURS, dateFr, nf, useApi } from "../api";
import { Choix, Etat, Hero, Section } from "../components/Ui";
import CarteSvg from "../components/CarteSvg";

const CLASSES = {
  "très bon": ["#1a9850", "#e3f4e8"], bon: ["#66bd63", "#eef8e8"], moyen: ["#c9a800", "#fff8d6"],
  "médiocre": ["#e07b00", "#fff0dc"], mauvais: ["#d7301f", "#fde2df"], "très mauvais": ["#7f0000", "#f6d6d6"],
};
const POL = { pm10: { nom: "PM10", seuil: 50, oms: 45, unite: "µg/m³" }, no2: { nom: "NO₂", seuil: 120, oms: 25, unite: "µg/m³" } };
const Classe = ({ c }) => {
  const [fg, bg] = CLASSES[c] || ["#333", "#eee"];
  return <span className="ch-pill" style={{ color: fg, background: bg }}>{c}</span>;
};
const VILLES = ["Casablanca", "Marrakech", "Fès", "Tanger"];
const CENTRE = { Casablanca: [33.58, -7.6], Marrakech: [31.64, -8.0], "Fès": [34.04, -5.0], Tanger: [35.77, -5.81] };

function CarteStation({ s, pol, actif, onClick }) {
  const p = s.prevision[pol];
  const j1 = p[0];
  const rare = s.disponibilite_pct < 60;
  return (
    <div className={`ch-card p-3 h-100 ch-carte-dest ${actif ? "actif" : ""}`} onClick={onClick}>
      <div className="d-flex justify-content-between gap-2">
        <div className="fw-semibold small">{s.station}</div>
        {rare && <Badge bg="warning" text="dark" title="Capteur souvent en panne ou installé récemment">capteur rare</Badge>}
      </div>
      <div className="d-flex align-items-baseline gap-2 mt-1">
        <span className="fs-3 fw-bold">{nf(j1.prevision, 0)}</span><span className="small text-secondary">{POL[pol].unite} demain</span>
      </div>
      <div className="small text-secondary mb-1">80 % de chances entre {nf(j1.bas, 0)} et {nf(j1.haut, 0)}</div>
      <Classe c={j1.classe} />
      {j1.episode_poussiere ? <span className="ch-pill ms-1" style={{ background: "#f6e7cf", color: "#8a5a12" }}>poussières</span> : null}
      <div className="d-flex gap-3 small mt-2 text-secondary">
        {p.slice(1).map((x) => <span key={x.date}>{dateFr(x.date, { weekday: "short" })} <b className="text-dark">{nf(x.prevision, 0)}</b></span>)}
      </div>
    </div>
  );
}

function Serie({ station, pol }) {
  const { data, erreur, chargement } = useApi(`/air/serie?station=${encodeURIComponent(station)}&polluant=${pol}&jours=120`);
  const d = useMemo(() => {
    if (!data) return [];
    const h = data.historique.map((r) => ({ date: r.date, mesure: r.valeur }));
    const last = h[h.length - 1];
    return [...h.slice(0, -1), { ...last, prevision: last.mesure, bande: [last.mesure, last.mesure] },
      ...data.prevision.map((r) => ({ date: r.date, prevision: r.prevision, bande: [r.bas, r.haut] }))];
  }, [data]);
  if (!data) return <Etat chargement={chargement} erreur={erreur} hauteur={320} />;
  return (
    <Section titre={`${station} — ${POL[pol].nom} journalier (4 derniers mois de mesures) et prévision J+1 à J+3`} icone="bi-activity">
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={d} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#eef1ed" vertical={false} />
          <XAxis dataKey="date" minTickGap={40} tick={{ fontSize: 12 }} tickFormatter={(s) => dateFr(s, { day: "numeric", month: "short" })} />
          <YAxis tick={{ fontSize: 12 }} width={44} />
          <Tooltip labelFormatter={(s) => dateFr(s, { weekday: "long", day: "numeric", month: "long" })} formatter={(v, n) => [Array.isArray(v) ? `${nf(v[0], 0)} – ${nf(v[1], 0)}` : `${nf(v, 0)} ${POL[pol].unite}`, n]} />
          <ReferenceLine y={POL[pol].seuil} stroke={COULEURS.rouge} strokeDasharray="4 4" label={{ value: `seuil « médiocre » (${POL[pol].seuil})`, position: "insideTopLeft", fontSize: 11, fill: COULEURS.rouge }} />
          <Area dataKey="bande" name="Intervalle 80 %" stroke="none" fill="#cfe3e8" fillOpacity={0.9} isAnimationActive={false} />
          <Line dataKey="mesure" name="Mesuré" stroke={COULEURS.encre} strokeWidth={1.5} dot={false} connectNulls={false} isAnimationActive={false} />
          <Line dataKey="prevision" name="Prévision" stroke="#3f7280" strokeWidth={2.4} strokeDasharray="5 3" dot={{ r: 3 }} isAnimationActive={false} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="small text-secondary">Les trous de la courbe sont des pannes de capteur. Pics brutaux au printemps et en été : épisodes de poussières sahariennes (chergui).</div>
    </Section>
  );
}

export default function Air() {
  const st = useApi("/air/stations");
  const ev = useApi("/air/evaluation");
  const [pol, setPol] = useState("pm10");
  const [choix, setChoix] = useState("Derb Soltane (trafic)");
  return (
    <>
      <Hero variante="air" titre="🌬️ Qualité de l'air dans les villes"
        texte="Prévoir les particules (PM10) et le dioxyde d'azote (NO₂) pour les 3 prochains jours, station par station, en disant honnêtement à quel point on est sûr — surtout là où les capteurs sont rares."
        badges={["📍 Casablanca · Marrakech · Fès · Tanger", "📡 9 stations, journalier 2019-2026", "🤖 XGBoost quantile", "🎯 calibration conforme par station"]} />
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <Choix options={[["pm10", "Particules PM10"], ["no2", "Dioxyde d'azote NO₂"]]} valeur={pol} onChange={setPol} />
        <div className="ch-legende">{Object.entries(CLASSES).map(([k, [c]]) => <span key={k}><i style={{ background: c }} />{k}</span>)}</div>
      </div>
      <Etat chargement={st.chargement} erreur={st.erreur} hauteur={300}>
        {st.data && (
          <>
            {VILLES.map((v) => (
              <div key={v} className="mb-3">
                <div className="fw-bold mb-2"><i className="bi bi-geo-alt-fill text-primary me-1" />{v}</div>
                <Row className="g-3">
                  {st.data.filter((s) => s.ville === v).map((s) => (
                    <Col sm={6} lg={3} key={s.station}><CarteStation s={s} pol={pol} actif={choix === s.station} onClick={() => setChoix(s.station)} /></Col>
                  ))}
                </Row>
              </div>
            ))}
            <Row className="g-3">
              <Col lg={8}><Serie station={choix} pol={pol} /></Col>
              <Col lg={4}>
                <Section titre="Carte des stations (demain)" icone="bi-map">
                  <CarteSvg fondMaroc largeur={420} hauteur={330} bornes={[[30.9, -9.4], [36.0, -4.2]]}
                    points={VILLES.map((v) => {
                      const ss = st.data.filter((s) => s.ville === v);
                      const pire = ss.reduce((a, s) => (s.prevision[pol][0].prevision > a.prevision[pol][0].prevision ? s : a));
                      const j1 = pire.prevision[pol][0];
                      return { lat: CENTRE[v][0], lon: CENTRE[v][1], r: 5 + ss.length * 1.5, taillePolice: 13, couleur: CLASSES[j1.classe]?.[0], label: `${v} ${nf(j1.prevision, 0)}`,
                        titre: `${v} : ${ss.length} station(s), maximum prévu ${nf(j1.prevision, 0)} ${POL[pol].unite}` };
                    })} />
                  <div className="small text-secondary mt-2">Couleur = station la plus polluée de la ville ; taille = nombre de stations. Tanger n'a qu'un capteur, souvent en panne.</div>
                </Section>
              </Col>
            </Row>
          </>
        )}
      </Etat>
      <Section titre="Fiabilité par station (test : novembre 2025 → novembre 2026)" icone="bi-clipboard-data" className="mt-3">
        <Etat chargement={ev.chargement} erreur={ev.erreur}>
          {ev.data && (
            <>
              <Table size="sm" hover responsive className="ch-table-compact">
                <thead><tr><th>Station</th><th className="text-end">Mesures disponibles</th><th className="text-end">Erreur modèle (J+1)</th><th className="text-end">Recopier la veille</th><th className="text-end">Couverture brute → calibrée</th><th className="text-end">Largeur intervalle</th><th className="text-end">Sans capteur (J+1)</th></tr></thead>
                <tbody>{ev.data.stations.filter((r) => r.polluant === pol).map((r) => (
                  <tr key={r.station} className={choix === r.station ? "table-active" : ""} style={{ cursor: "pointer" }} onClick={() => setChoix(r.station)}>
                    <td>{r.station}</td>
                    <td className="text-end">{nf(r.disponibilite_pct, 0)} %{r.disponibilite_pct < 60 && <i className="bi bi-exclamation-triangle-fill text-warning ms-1" />}</td>
                    <td className="text-end fw-semibold">{nf(r.mae_modele_j1, 1)}</td>
                    <td className="text-end">{nf(r.mae_persistance_j1, 1)}</td>
                    <td className="text-end">{nf(r.couverture_brute, 0)} % → <b>{nf(r.couverture_calibree, 0)} %</b></td>
                    <td className="text-end">± {nf(r.largeur_relative_pct / 2, 0)} %</td>
                    <td className="text-end">{r.mae_sans_capteur == null ? <span className="text-secondary">pas de voisine</span> : nf(r.mae_sans_capteur, 1)}</td>
                  </tr>))}
                </tbody>
              </Table>
              <div className="ch-note">
                Erreurs en {POL[pol].unite}. Le modèle divise nettement l'erreur par rapport à « recopier la veille », grâce à la météo prévue (vent, pluie, poussières).
                Les intervalles sont <b>recalibrés station par station</b> (méthode conforme) : une station avec peu de mesures reçoit un intervalle plus prudent.
                Colonne « sans capteur » : on retire la station et on la reconstitue à partir des stations voisines et de la météo — l'erreur augmente, surtout pour
                les sites atypiques (zone industrielle, grand axe) ; c'est l'argument chiffré pour installer des capteurs supplémentaires.
              </div>
            </>
          )}
        </Etat>
      </Section>
    </>
  );
}
