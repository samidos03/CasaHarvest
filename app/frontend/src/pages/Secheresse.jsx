import { useState } from "react";
import { Badge, Col, Form, Row, Table } from "react-bootstrap";
import {
  Bar, CartesianGrid, ComposedChart, Legend, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip,
  XAxis, YAxis,
} from "recharts";
import { COULEURS, moisFr, nf, useApi } from "../api";
import { Etat, Hero, Section } from "../components/Ui";

const STYLE_CLASSE = {
  "sécheresse extrême": ["#7a1418", "#fbe3e4"], "sécheresse sévère": ["#c1272d", "#fbe3e4"],
  "sécheresse modérée": ["#b0721a", "#fff4d6"], normal: ["#0b7a43", "#e7f3ec"], humide: ["#1d6fa5", "#e3f0f9"],
};
const Classe = ({ c }) => {
  const [fg, bg] = STYLE_CLASSE[c] || ["#333", "#eee"];
  return <span className="ch-pill" style={{ color: fg, background: bg }}>{c}</span>;
};

function CarteZone({ e, prev, actif, onClick }) {
  const p1 = prev.find((p) => p.zone === e.zone && p.horizon_mois === 1);
  return (
    <div className={`ch-card p-3 h-100 ${actif ? "border-primary" : ""}`} style={{ cursor: "pointer", borderWidth: actif ? 2 : 1 }} onClick={onClick}>
      <div className="fw-bold mb-1"><i className="bi bi-geo-alt me-1 text-primary" />{e.zone}</div>
      <div className="small text-secondary mb-2">{moisFr(e.mois)} · SPI-3 = <b>{nf(e.spi_3, 2)}</b></div>
      <Classe c={e.classe_secheresse_spi3} />
      {p1 && (
        <div className="small mt-2">
          Mois suivant : <b>{nf(p1.spi3_prevu, 2)}</b>{" "}
          {p1.alerte_secheresse === "oui" ? <Badge bg="danger">alerte sécheresse</Badge> : <Badge bg="success">pas d'alerte</Badge>}
        </div>
      )}
    </div>
  );
}

function Serie({ zone }) {
  const { data, erreur, chargement } = useApi(`/secheresse/serie?zone=${encodeURIComponent(zone)}`);
  const [debut, setDebut] = useState("2018");
  if (!data) return <Etat chargement={chargement} erreur={erreur} hauteur={360} />;
  const d = data.filter((r) => r.mois >= `${debut}-01`);
  return (
    <Section titre={`${zone} — pluie mensuelle et indice de sécheresse SPI-3`} icone="bi-cloud-drizzle">
      <div className="d-flex justify-content-end mb-2">
        <Form.Select size="sm" style={{ width: 180 }} value={debut} onChange={(e) => setDebut(e.target.value)}>
          {["2010", "2014", "2018", "2022"].map((a) => <option key={a} value={a}>Depuis {a}</option>)}
        </Form.Select>
      </div>
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={d} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#eef1ed" vertical={false} />
          <XAxis dataKey="mois" minTickGap={40} tick={{ fontSize: 12 }} tickFormatter={(m) => m.slice(0, 4)} />
          <YAxis yAxisId="spi" domain={[-3, 3]} ticks={[-3, -2, -1, 0, 1, 2, 3]} tick={{ fontSize: 12 }} width={48}
            tickFormatter={(v) => (v > 0 ? `+${v}` : `${v}`.replace("-", "−"))}
            label={{ value: "SPI", angle: -90, position: "insideLeft", fontSize: 12 }} />
          <YAxis yAxisId="mm" orientation="right" tick={{ fontSize: 12 }} unit=" mm" width={60} />
          <ReferenceArea yAxisId="spi" y1={-3} y2={-1} fill="#fbe3e4" fillOpacity={0.5} />
          <ReferenceLine yAxisId="spi" y={-1} stroke={COULEURS.rouge} strokeDasharray="4 4" label={{ value: "sécheresse", position: "insideBottomLeft", fontSize: 11, fill: COULEURS.rouge }} />
          <ReferenceLine yAxisId="spi" y={0} stroke="#bbb" />
          <Tooltip labelFormatter={moisFr} formatter={(v, n) => [n === "Pluie" ? `${nf(v, 0)} mm` : nf(v, 2), n]} />
          <Legend wrapperStyle={{ fontSize: 13 }} />
          <Bar yAxisId="mm" dataKey="pluie_mm" name="Pluie" fill="#9cc9e6" isAnimationActive={false} />
          <Line yAxisId="spi" dataKey="spi_3" name="SPI-3 (3 mois)" stroke={COULEURS.rouge} strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line yAxisId="spi" dataKey="spi_6" name="SPI-6 (6 mois)" stroke="#55626b" strokeWidth={1.4} dot={false} strokeDasharray="5 3" isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="small text-secondary">SPI : pluie comparée à la normale du même mois (0 = normal ; ≤ −1 sécheresse modérée ; ≤ −1,5 sévère ; ≤ −2 extrême). Pluie : CHIRPS v2.0, moyenne sur la zone.</div>
    </Section>
  );
}

export default function Secheresse() {
  const etat = useApi("/secheresse/etat");
  const ev = useApi("/secheresse/evaluation");
  const [zone, setZone] = useState("Settat-Berrechid");
  return (
    <>
      <Hero titre="💧 Eau & sécheresse" texte="Suivre la sécheresse dans les 4 zones de Casablanca-Settat et prévoir le risque des prochains mois."
        badges={["🌧️ pluie CHIRPS 2009-2026", "🌱 humidité du sol ERA5-Land", "🤖 Ridge · alerte à 1 mois"]} />
      <Etat chargement={etat.chargement} erreur={etat.erreur}>
        {etat.data && (
          <>
            <Row className="g-3 mb-3">
              {etat.data.etat.map((e) => (
                <Col sm={6} xl={3} key={e.zone}><CarteZone e={e} prev={etat.data.prevision} actif={zone === e.zone} onClick={() => setZone(e.zone)} /></Col>
              ))}
            </Row>
            <Serie zone={zone} />
            <Row className="g-3 mt-1">
              <Col lg={7}>
                <Section titre="Prévision des 3 prochains mois" icone="bi-calendar3">
                  <Table size="sm" hover className="ch-table-compact mb-2">
                    <thead><tr><th>Zone</th><th>Mois prévu</th><th className="text-end">SPI-3 prévu</th><th>Classe</th><th>Alerte</th><th>Fiabilité</th></tr></thead>
                    <tbody>{etat.data.prevision.map((p) => (
                      <tr key={p.zone + p.mois_prevu}>
                        <td>{p.zone}</td><td>{moisFr(p.mois_prevu)}</td><td className="text-end">{nf(p.spi3_prevu, 2)}</td>
                        <td><Classe c={p.classe} /></td>
                        <td>{p.alerte_secheresse === "oui" ? <Badge bg="danger">oui</Badge> : <Badge bg="light" text="dark">non</Badge>}</td>
                        <td className={p.horizon_mois === 1 ? "text-success fw-semibold" : "text-secondary"}>{p.fiabilite}</td>
                      </tr>))}
                    </tbody>
                  </Table>
                  <div className="small text-secondary">Alerte déclenchée si le SPI-3 prévu est ≤ −0,5 (seuil choisi sur la validation pour repérer la majorité des sécheresses).</div>
                </Section>
              </Col>
              <Col lg={5}>
                <Section titre="Fiabilité du modèle (validation 2018-2026)" icone="bi-clipboard-data">
                  <Etat chargement={ev.chargement} erreur={ev.erreur}>
                    {ev.data && (
                      <Table size="sm" className="ch-table-compact mb-2">
                        <thead><tr><th>Horizon</th><th className="text-end">R²</th><th className="text-end">Détectées</th><th className="text-end">Fausses alertes</th></tr></thead>
                        <tbody>{ev.data.filter((m) => m.modele === "Ridge").map((m) => (
                          <tr key={m.horizon}><td>{m.horizon} mois</td><td className="text-end">{nf(m.R2, 2)}</td>
                            <td className="text-end">{nf(m.secheresses_detectees_pct, 0)} %</td><td className="text-end">{nf(m.fausses_alertes_pct, 0)} %</td></tr>))}
                        </tbody>
                      </Table>
                    )}
                  </Etat>
                  <div className="ch-note">À <b>1 mois</b>, le modèle repère environ <b>3 sécheresses sur 4</b> à l'avance. Au-delà de 2 mois, la pluie n'est pas prévisible avec ces seules données : la prévision n'est qu'indicative.</div>
                </Section>
              </Col>
            </Row>
          </>
        )}
      </Etat>
    </>
  );
}
