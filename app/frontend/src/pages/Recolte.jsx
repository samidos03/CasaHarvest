import { useEffect, useState } from "react";
import { Alert, Badge, Button, ButtonGroup, Col, Form, Row, Table } from "react-bootstrap";
import {
  CartesianGrid, Legend, Line, LineChart, ReferenceArea, ResponsiveContainer, Scatter, ScatterChart, Tooltip,
  XAxis, YAxis, ZAxis,
} from "recharts";
import { COULEURS, nf, useApi } from "../api";
import { Etat, Hero, Kpi, Section } from "../components/Ui";

const HYBRIDE = "Hybride (XGBoost + garde-fou Ridge)";
const COUL_CULTURE = { "Blé tendre": "#1f77b4", "Blé dur": "#ff7f0e", Orge: "#2ca02c" };
const libelleSpi = (v) => (v <= -2 ? "sécheresse extrême" : v <= -1.5 ? "sécheresse sévère" : v <= -1 ? "sécheresse modérée" : v < 1 ? "normal" : v < 1.5 ? "humide" : "très humide");

function Serie({ zone, culture }) {
  const { data, erreur, chargement } = useApi(`/rendement/serie?zone=${encodeURIComponent(zone)}&culture=${encodeURIComponent(culture)}`);
  if (!data) return <Etat chargement={chargement} erreur={erreur} hauteur={360} />;
  const lignes = data.historique.map((r) => ({ campagne: r.campagne, reel: r.rendement_qx_ha, cv: r.prevision_cv }));
  const der = lignes[lignes.length - 1];
  const hyb = data.previsions.filter((p) => p.modele === HYBRIDE);
  const xgb = data.previsions.filter((p) => p.modele === "XGBoost");
  const fut = hyb.map((p) => ({ campagne: p.campagne, hybride: p.prevision_qx_ha, xgboost: xgb.find((x) => x.campagne === p.campagne)?.prevision_qx_ha }));
  const tout = [...lignes, ...fut];
  const idx = tout.findIndex((r) => r.campagne === der.campagne);
  tout[idx] = { ...tout[idx], hybride: der.cv, xgboost: der.cv };
  const p26 = hyb.find((p) => p.campagne === 2026);
  const extrap = hyb.some((p) => p.extrapolation);
  return (
    <>
      <Row className="g-3 mb-3">
        <Col sm={6} xl={3}><Kpi label="Dernier rendement publié" valeur={`${nf(der.reel, 1)} q/ha`} sous={`campagne ${der.campagne} (HCP)`} icone="bi-clipboard-check" /></Col>
        <Col sm={6} xl={3}><Kpi label="Prévision 2026" valeur={`${nf(p26?.prevision_qx_ha, 1)} q/ha`} sous="modèle hybride, climat observé" icone="bi-stars" /></Col>
        <Col sm={6} xl={3}><Kpi label="Meilleure année 2010-2023" valeur={`${nf(Math.max(...lignes.map((l) => l.reel || 0)), 1)} q/ha`} sous={`en ${lignes.reduce((a, b) => (b.reel > a.reel ? b : a)).campagne}`} icone="bi-trophy" /></Col>
        <Col sm={6} xl={3}><Kpi label="Pire année 2010-2023" valeur={`${nf(Math.min(...lignes.map((l) => l.reel ?? 99)), 1)} q/ha`} sous={`en ${lignes.reduce((a, b) => (b.reel < a.reel ? b : a)).campagne} (sécheresse)`} icone="bi-cloud-sun" /></Col>
      </Row>
      <Section titre={`${culture} — ${zone} : rendement réel et prévu`} icone="bi-graph-up">
        <ResponsiveContainer width="100%" height={360}>
          <LineChart data={tout} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#eef1ed" vertical={false} />
            <XAxis dataKey="campagne" tick={{ fontSize: 12 }} />
            <YAxis unit=" q/ha" width={66} tick={{ fontSize: 12 }} />
            <ReferenceArea x1={der.campagne} x2={2026} fill="#f3f6f2" />
            <Tooltip formatter={(v, n) => [`${nf(v, 1)} q/ha`, n]} labelFormatter={(c) => `Campagne ${c - 1}/${c}`} />
            <Legend wrapperStyle={{ fontSize: 13 }} />
            <Line dataKey="reel" name="Rendement réel (HCP)" stroke="#1f2a24" strokeWidth={2.5} dot={{ r: 3.5 }} isAnimationActive={false} />
            <Line dataKey="cv" name="Prévu (campagne laissée de côté)" stroke={COULEURS.vert} strokeDasharray="6 4" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
            <Line dataKey="hybride" name="Prévision 2024-2026 — hybride" stroke={COULEURS.vert} strokeWidth={3} dot={{ r: 5, strokeWidth: 0, fill: COULEURS.vert }} isAnimationActive={false} />
            <Line dataKey="xgboost" name="XGBoost seul" stroke={COULEURS.or} strokeDasharray="3 3" strokeWidth={1.6} dot={{ r: 3 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
        {extrap && <div className="small text-secondary mt-1"><i className="bi bi-exclamation-diamond me-1 text-warning" />Une campagne future a un climat hors des valeurs 2010-2023 : le modèle hybride utilise alors la Ridge, car XGBoost ne sait pas extrapoler (voir l'écart avec la courbe orange).</div>}
      </Section>
    </>
  );
}

function Simulateur({ options, zone, culture }) {
  const p = options.plages;
  const [spi, setSpi] = useState(0);
  const [hs, setHs] = useState(Math.round(p.humidite_sol_printemps.mediane * 100) / 100);
  const [chaud, setChaud] = useState(Math.round(p.jours_chauds_printemps.mediane));
  const [res, setRes] = useState(null);
  useEffect(() => {
    const t = setTimeout(() => {
      fetch(`/api/rendement/simuler?spi6=${spi}&humidite_sol=${hs}&jours_chauds=${chaud}&culture=${encodeURIComponent(culture)}&zone=${encodeURIComponent(zone)}`)
        .then((r) => r.json()).then(setRes).catch(() => setRes(null));
    }, 180);
    return () => clearTimeout(t);
  }, [spi, hs, chaud, zone, culture]);
  const preset = (s, h, c) => { setSpi(s); setHs(h); setChaud(c); };
  return (
    <Section titre="Simulateur : et si la saison était… ?" icone="bi-sliders">
      <p className="small text-secondary">Choisissez le climat de la campagne : le modèle hybride estime le rendement de <b>{culture}</b> pour <b>{zone}</b>.</p>
      <div className="d-flex flex-wrap gap-2 mb-3">
        <Button size="sm" variant="outline-danger" onClick={() => preset(-1.4, 0.21, 12)}>☀️ Année sèche (type 2022)</Button>
        <Button size="sm" variant="outline-secondary" onClick={() => preset(0, 0.25, 9)}>⛅ Année normale</Button>
        <Button size="sm" variant="outline-primary" onClick={() => preset(1.2, 0.3, 4)}>🌧️ Année humide (type 2021)</Button>
      </div>
      <Row className="g-4 align-items-center">
        <Col lg={7}>
          <Form.Label className="small fw-semibold mb-0">Sécheresse de fin d'hiver — SPI-6 en mars : <b>{nf(spi, 1)}</b> <Badge bg="light" text="dark">{libelleSpi(spi)}</Badge></Form.Label>
          <Form.Range min={-2.5} max={2.5} step={0.1} value={spi} onChange={(e) => setSpi(Number(e.target.value))} />
          <Form.Label className="small fw-semibold mb-0">Humidité du sol au printemps (m³/m³) : <b>{nf(hs, 2)}</b></Form.Label>
          <Form.Range min={0.15} max={0.4} step={0.01} value={hs} onChange={(e) => setHs(Number(e.target.value))} />
          <Form.Label className="small fw-semibold mb-0">Jours ≥ 30 °C au printemps (mars-mai) : <b>{chaud}</b></Form.Label>
          <Form.Range min={0} max={25} step={1} value={chaud} onChange={(e) => setChaud(Number(e.target.value))} />
        </Col>
        <Col lg={5}>
          <div className="text-center p-3 rounded-4" style={{ background: "#e7f3ec" }}>
            <div className="small text-uppercase fw-semibold text-secondary">Rendement estimé</div>
            <div className="display-5 fw-bold text-primary">{res ? nf(res.rendement_qx_ha, 1) : "…"}</div>
            <div className="text-secondary">quintaux par hectare</div>
            {res && <div className="small mt-2">Ridge : {nf(res.ridge, 1)} · XGBoost : {nf(res.xgboost, 1)} q/ha</div>}
          </div>
          {res?.extrapolation && <Alert variant="warning" className="small mt-2 mb-0 py-2"><i className="bi bi-exclamation-triangle me-1" />Climat hors des valeurs observées 2010-2023 : estimation par la Ridge (extrapolation), à prendre avec prudence.</Alert>}
        </Col>
      </Row>
    </Section>
  );
}

function Region() {
  const { data, erreur, chargement } = useApi("/rendement/region");
  if (!data) return <Etat chargement={chargement} erreur={erreur} hauteur={120} />;
  const camp = [...new Set(data.previsions.map((p) => p.campagne))];
  const val = (c, m) => data.previsions.find((p) => p.campagne === c && p.modele === m);
  return (
    <Section titre="Région Casablanca-Settat — céréales (blé tendre, blé dur, orge)" icone="bi-geo-alt">
      <Table size="sm" className="ch-table-compact mb-2">
        <thead><tr><th>Campagne</th><th className="text-end">Hybride (retenu)</th><th className="text-end">XGBoost seul</th><th className="text-end">Ridge seule</th></tr></thead>
        <tbody>
          {camp.map((c) => (
            <tr key={c}>
              <td>{c - 1}/{c}</td>
              {[HYBRIDE, "XGBoost", "Ridge"].map((m) => <td key={m} className={`text-end ${m === HYBRIDE ? "fw-semibold" : ""}`}>{nf(val(c, m)?.production_Mqx, 1)} Mqx · {nf(val(c, m)?.rendement_qx_ha, 1)} q/ha</td>)}
            </tr>
          ))}
        </tbody>
      </Table>
      <div className="ch-note">
        <b>Contrôle externe 2026</b> : la Direction régionale de l'agriculture annonce <b>{nf(data.officiel_2026.production_Mqx, 1)} millions de quintaux</b> (≈ {nf(data.officiel_2026.rendement_qx_ha, 1)} q/ha). Le modèle hybride prévoit <b>{nf(val(2026, HYBRIDE)?.production_Mqx, 1)} Mqx</b>, XGBoost seul {nf(val(2026, "XGBoost")?.production_Mqx, 1)} Mqx.
        <span className="text-secondary"> 2024 et 2025 : pas de bilan régional officiel trouvé pour vérifier.</span>
      </div>
    </Section>
  );
}

function Evaluation() {
  const { data, erreur, chargement } = useApi("/rendement/evaluation");
  if (!data) return <Etat chargement={chargement} erreur={erreur} hauteur={200} />;
  return (
    <Row className="g-3">
      <Col lg={6}>
        <Section titre="La sécheresse de mars décide de la récolte" icone="bi-cloud-sun">
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
              <CartesianGrid stroke="#eef1ed" />
              <XAxis type="number" dataKey="spi_6_mars" name="SPI-6 mars" domain={[-2, 2]} tick={{ fontSize: 12 }} label={{ value: "SPI-6 en mars (≤ −1 : sécheresse)", position: "insideBottom", offset: -5, fontSize: 12 }} />
              <YAxis type="number" dataKey="rendement_qx_ha" name="Rendement" unit=" q/ha" width={66} tick={{ fontSize: 12 }} />
              <ZAxis range={[36, 36]} />
              <Tooltip formatter={(v, n) => [nf(v, 2), n]} />
              <Legend verticalAlign="top" wrapperStyle={{ fontSize: 12 }} />
              {Object.keys(COUL_CULTURE).map((c) => <Scatter key={c} name={c} data={data.nuage_spi.filter((d) => d.culture === c)} fill={COUL_CULTURE[c]} fillOpacity={0.75} isAnimationActive={false} />)}
            </ScatterChart>
          </ResponsiveContainer>
        </Section>
      </Col>
      <Col lg={6}>
        <Section titre="Précision (validation croisée, une campagne laissée de côté)" icone="bi-clipboard-data">
          <Table size="sm" className="ch-table-compact">
            <thead><tr><th>Moment</th><th>Modèle</th><th className="text-end">Erreur moy.</th><th className="text-end">R²</th></tr></thead>
            <tbody>{data.metriques.map((m) => (
              <tr key={m.moment + m.modele} className={m.modele === HYBRIDE ? "fw-semibold" : ""}>
                <td>{m.moment === "mars" ? "fin mars" : "fin mai"}</td><td>{m.modele.replace(" (XGBoost + garde-fou Ridge)", "")}</td>
                <td className="text-end">±{nf(m.MAE_qx_ha, 1)} q/ha</td><td className="text-end">{nf(m.R2, 2)}</td>
              </tr>))}
            </tbody>
          </Table>
          <div className="small text-secondary">XGBoost est le plus précis sur les années « habituelles » ; le modèle hybride sacrifie un peu de précision pour rester fiable les années exceptionnelles (2026 : écart de 2 % avec la prévision officielle, contre −40 % pour XGBoost seul).</div>
        </Section>
      </Col>
    </Row>
  );
}

export default function Recolte() {
  const options = useApi("/rendement/options");
  const [zone, setZone] = useState("Région Casablanca-Settat");
  const [culture, setCulture] = useState("Blé tendre");
  return (
    <>
      <Hero titre="🌾 Récolte de céréales" texte="Prévoir le rendement du blé tendre, du blé dur et de l'orge à partir du climat de la campagne — dès la fin mars, trois mois avant la moisson."
        badges={["📊 rendements HCP 2010-2023", "🌧️ pluie CHIRPS · humidité du sol ERA5-Land", "🤖 hybride XGBoost + Ridge"]} />
      <Etat chargement={options.chargement} erreur={options.erreur}>
        {options.data && (
          <>
            <Section className="mb-3">
              <Row className="g-3 align-items-end">
                <Col md={5}>
                  <Form.Label className="small fw-semibold">Zone</Form.Label>
                  <Form.Select value={zone} onChange={(e) => setZone(e.target.value)}>{options.data.zones.map((z) => <option key={z}>{z}</option>)}</Form.Select>
                </Col>
                <Col md="auto">
                  <Form.Label className="small fw-semibold">Culture</Form.Label><br />
                  <ButtonGroup>{options.data.cultures.map((c) => <Button key={c} size="sm" variant={culture === c ? "primary" : "outline-primary"} onClick={() => setCulture(c)}>{c}</Button>)}</ButtonGroup>
                </Col>
              </Row>
            </Section>
            <Serie zone={zone} culture={culture} />
            <Row className="g-3 mt-1">
              <Col xl={7}><Simulateur options={options.data} zone={zone} culture={culture} /></Col>
              <Col xl={5}><Region /></Col>
            </Row>
            <div className="mt-3"><Evaluation /></div>
          </>
        )}
      </Etat>
    </>
  );
}
