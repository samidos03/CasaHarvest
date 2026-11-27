import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Col, Nav, Row, Table } from "react-bootstrap";
import {
  Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Scatter,
  ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from "recharts";
import { COULEURS, moisFr, nf, useApi } from "../api";
import { Choix, Etat, Hero, Kpi, Section } from "../components/Ui";
import CarteRegion from "../components/CarteRegion";

const PROVINCES = ["Casablanca", "Mohammedia", "Settat", "Berrechid", "El Jadida", "Sidi Bennour", "Benslimane", "Nouaceur", "Médiouna"];
const MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
const CULT = { "Blé tendre": "#b0721a", "Blé dur": "#0b7a43", Orge: "#1d6fa5" };
const BLEU = "#1d6fa5";
const fmtM = (m) => `${MOIS[+m.slice(5) - 1]} ${m.slice(2, 4)}`;
const echellePct = (p) => (p == null ? "#e9ede7" : p >= 130 ? "#2166ac" : p >= 110 ? "#67a9cf" : p >= 90 ? "#a6d96a" : p >= 70 ? "#fdae61" : "#d7301f");
const echelleRatio = (p) => (p == null ? "#e9ede7" : p >= 110 ? "#1a9850" : p >= 90 ? "#a6d96a" : p >= 70 ? "#fdae61" : "#d7301f");

function ChoixProvince({ province, setProvince }) {
  return (
    <select className="form-select form-select-sm" style={{ maxWidth: 220 }} value={province} onChange={(e) => setProvince(e.target.value)}>
      {PROVINCES.map((p) => <option key={p}>{p}</option>)}
    </select>
  );
}

// ================================================================= PLUIE
function Pluie({ province, setProvince, provs }) {
  const { data, erreur, chargement } = useApi(`/region/pluie?province=${encodeURIComponent(province)}`);
  const ev = useApi("/region/evaluation-pluie");
  const [depuis, setDepuis] = useState("2020");
  const [saisonCarte, setSaisonCarte] = useState(2026);
  const serie = useMemo(() => {
    if (!data) return [];
    const cl = Object.fromEntries(data.climatologie.map((c) => [c.m, c]));
    return data.mensuel.filter((r) => r.mois >= `${depuis}-01`).map((r) => {
      const c = cl[+r.mois.slice(5)];
      return { mois: r.mois, pluie: r.pluie_mm, normale: c?.normale, bande: c ? [c.p10, c.p90] : null };
    });
  }, [data, depuis]);
  if (!data) return <Etat chargement={chargement} erreur={erreur} hauteur={400} />;
  const saisons = data.saisons.filter((s) => s.province === province);
  const carteVals = Object.fromEntries(data.saisons.filter((s) => s.saison === saisonCarte).map((s) => [s.province, s.pct_normale]));
  const s26 = saisons.find((s) => s.saison === 2026);
  const spiDer = data.spi3.at(-1);
  return (
    <>
      <Row className="g-3 mb-3">
        <Col sm={6} lg={3}><Kpi label="Normale annuelle (2010-2025)" valeur={`${nf(s26?.normale_mm, 0)} mm`} sous="cumul septembre → août" /></Col>
        <Col sm={6} lg={3}><Kpi label="Saison 2025-2026" valeur={`${nf(s26?.pluie_mm, 0)} mm`} sous={<>{nf(s26?.pct_normale, 0)} % de la normale</>} /></Col>
        <Col sm={6} lg={3}><Kpi label={`SPI-3 (${moisFr(spiDer?.mois)})`} valeur={nf(spiDer?.spi3, 2)} sous={spiDer?.classe} /></Col>
        <Col sm={6} lg={3}><Kpi label="Saison la plus sèche" valeur={`${saisons.reduce((a, s) => (s.pct_normale < a.pct_normale ? s : a), saisons[0])?.saison - 1}-${String(saisons.reduce((a, s) => (s.pct_normale < a.pct_normale ? s : a), saisons[0])?.saison).slice(2)}`}
          sous={`${nf(Math.min(...saisons.map((s) => s.pct_normale)), 0)} % de la normale`} /></Col>
      </Row>
      <Row className="g-3">
        <Col lg={5}>
          <Section titre="Carte : pluie de la saison en % de la normale" icone="bi-map">
            <select className="form-select form-select-sm mb-2" value={saisonCarte} onChange={(e) => setSaisonCarte(+e.target.value)}>
              {[...new Set(data.saisons.map((s) => s.saison))].sort((a, b) => b - a).map((s) => <option key={s} value={s}>Saison {s - 1}-{s}</option>)}
            </select>
            <CarteRegion choix={province} onChoix={setProvince} hauteur={300}
              couleurs={Object.fromEntries(PROVINCES.map((p) => [p, echellePct(carteVals[p])]))}
              etiquettes={Object.fromEntries(PROVINCES.map((p) => [p, carteVals[p] ? `${Math.round(carteVals[p])} %` : ""]))}
              legende={[["#d7301f", "< 70 %"], ["#fdae61", "70-90"], ["#a6d96a", "90-110"], ["#67a9cf", "110-130"], ["#2166ac", "> 130 %"]]} />
          </Section>
        </Col>
        <Col lg={7}>
          <Section titre={`${province} — pluie de chaque saison (CHIRPS)`} icone="bi-bar-chart">
            <ResponsiveContainer width="100%" height={330}>
              <BarChart data={saisons.map((s) => ({ ...s, nom: `${String(s.saison - 1).slice(2)}-${String(s.saison).slice(2)}` }))} margin={{ top: 10, right: 8, left: -6, bottom: 0 }}>
                <CartesianGrid stroke="#eef1ed" vertical={false} />
                <XAxis dataKey="nom" tick={{ fontSize: 11 }} interval={0} angle={-40} textAnchor="end" height={40} />
                <YAxis tick={{ fontSize: 12 }} unit=" mm" width={74} />
                <Tooltip formatter={(v, n, p) => [`${nf(v, 0)} mm (${nf(p.payload.pct_normale, 0)} % de la normale)`, "Pluie"]} />
                <ReferenceLine y={s26?.normale_mm} stroke="#14231b" strokeDasharray="5 4" label={{ value: "normale", position: "right", fontSize: 11 }} />
                <Bar dataKey="pluie_mm" isAnimationActive={false} radius={[3, 3, 0, 0]}>
                  {saisons.map((s) => <Cell key={s.saison} fill={echellePct(s.pct_normale)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Section>
        </Col>
      </Row>
      <Section titre={`${province} — pluie mensuelle et plage habituelle (10 % – 90 % des années)`} icone="bi-cloud-rain" className="mt-3">
        <div className="d-flex justify-content-between flex-wrap gap-2 mb-2">
          <ChoixProvince province={province} setProvince={setProvince} />
          <Choix options={[["2010", "Depuis 2010"], ["2020", "Depuis 2020"], ["2024", "Depuis 2024"]]} valeur={depuis} onChange={setDepuis} />
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={serie} margin={{ top: 10, right: 8, left: -6, bottom: 0 }}>
            <CartesianGrid stroke="#eef1ed" vertical={false} />
            <XAxis dataKey="mois" tickFormatter={fmtM} minTickGap={30} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 12 }} unit=" mm" width={62} />
            <Tooltip labelFormatter={moisFr} formatter={(v, n) => [Array.isArray(v) ? `${nf(v[0], 0)} – ${nf(v[1], 0)} mm` : `${nf(v, 0)} mm`, n]} />
            <Area dataKey="bande" name="Plage habituelle" fill="#d9e9f5" stroke="none" isAnimationActive={false} />
            <Bar dataKey="pluie" name="Pluie observée" fill={BLEU} isAnimationActive={false} />
            <Line dataKey="normale" name="Normale du mois" stroke="#14231b" strokeDasharray="4 3" dot={false} isAnimationActive={false} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </Section>
      <Row className="g-3 mt-1">
        <Col lg={7}>
          <Section titre="Indice de sécheresse SPI-3" icone="bi-thermometer-sun">
            <ResponsiveContainer width="100%" height={240}>
              <ComposedChart data={data.spi3.filter((r) => r.mois >= `${depuis}-01`)} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="#eef1ed" vertical={false} />
                <XAxis dataKey="mois" tickFormatter={fmtM} minTickGap={30} tick={{ fontSize: 11 }} />
                <YAxis domain={[-3, 3]} tick={{ fontSize: 12 }} />
                <Tooltip labelFormatter={moisFr} formatter={(v, n, p) => [`${nf(v, 2)} (${p.payload.classe})`, "SPI-3"]} />
                <ReferenceLine y={-1} stroke="#e07b00" strokeDasharray="4 3" label={{ value: "sécheresse", position: "insideBottomLeft", fontSize: 11, fill: "#e07b00" }} />
                <ReferenceLine y={0} stroke="#9aa5ad" />
                <Bar dataKey="spi3" isAnimationActive={false}>
                  {data.spi3.filter((r) => r.mois >= `${depuis}-01`).map((r) => <Cell key={r.mois} fill={r.spi3 < -1 ? "#d7301f" : r.spi3 < 0 ? "#fdae61" : "#67a9cf"} />)}
                </Bar>
              </ComposedChart>
            </ResponsiveContainer>
            <div className="small text-secondary">SPI-3 : pluie des 3 derniers mois comparée aux mêmes mois des autres années (loi gamma ajustée par mois). En dessous de −1 : sécheresse.</div>
          </Section>
        </Col>
        <Col lg={5}>
          <Section titre="Peut-on prévoir la pluie du mois prochain ?" icone="bi-question-circle">
            {ev.data && (
              <>
                <div className="d-flex gap-3 mb-2">
                  <Kpi label="Bonnes réponses" valeur={`${nf(ev.data.precision, 0)} %`} sous={`hasard : ${nf(ev.data.precision_hasard, 0)} %`} />
                  <Kpi label="Score RPSS" valeur={nf(ev.data.rpss, 2)} sous="0 = pas mieux que l'habitude" />
                </div>
                <div className="ch-note small">
                  Régression logistique (sec / normal / pluvieux) à partir du SPI-3 et de l'anomalie du mois en cours, testée saison par saison
                  sur {nf(ev.data.n, 0)} cas. Résultat : <b>pas mieux que la climatologie</b>. La pluie au Maroc dépend de perturbations
                  atlantiques imprévisibles au-delà de ~10 jours ; c'est pourquoi l'espace citoyen affiche la normale plutôt qu'une fausse prévision.
                </div>
              </>
            )}
          </Section>
        </Col>
      </Row>
    </>
  );
}

// ================================================================= HUMIDITÉ DU SOL
function Sol({ province, setProvince, provs }) {
  const { data, erreur, chargement } = useApi(`/region/sol?province=${encodeURIComponent(province)}`);
  const [depuis, setDepuis] = useState("2022");
  const serie = useMemo(() => {
    if (!data) return [];
    const h = data.mensuel.filter((r) => r.mois >= `${depuis}-01`).map((r) => ({ mois: r.mois, sol: r.humidite_sol_7_28cm, surface: r.humidite_sol_0_7cm, pluie: r.pluie_mm }));
    const last = h.at(-1);
    const p = data.prevision.map((r) => ({ mois: r.mois_cible, prevision: r.prevision, bande: [r.bas, r.haut] }));
    return [...h.slice(0, -1), { ...last, prevision: last.sol, bande: [last.sol, last.sol] }, ...p];
  }, [data, depuis]);
  if (!data) return <Etat chargement={chargement} erreur={erreur} hauteur={400} />;
  const etat = Object.fromEntries(data.etat.map((e) => [e.province, e]));
  const coul = { sec: "#fdae61", normal: "#a6d96a", humide: "#67a9cf" };
  const met = data.metriques;
  return (
    <>
      <Row className="g-3">
        <Col lg={5}>
          <Section titre={`Carte : humidité du sol en ${moisFr(data.etat[0]?.mois)}`} icone="bi-map">
            <CarteRegion choix={province} onChoix={setProvince} hauteur={300}
              couleurs={Object.fromEntries(PROVINCES.map((p) => [p, coul[etat[p]?.classe]]))}
              etiquettes={Object.fromEntries(PROVINCES.map((p) => [p, etat[p] ? `${etat[p].classe} (${Math.round(etat[p].percentile)}e pct)` : ""]))}
              legende={[["#fdae61", "sec (< 33e percentile)"], ["#a6d96a", "normal"], ["#67a9cf", "humide (> 67e)"]]} />
            <div className="small text-secondary mt-2">⚠️ {data.source}. Les provinces d'une même zone partagent la même valeur tant que data/collecte_provinces.py n'a pas été lancé.</div>
          </Section>
        </Col>
        <Col lg={7}>
          <Section titre={`${province} — humidité du sol (m³/m³) et prévision à 2 mois`} icone="bi-moisture">
            <div className="d-flex justify-content-between flex-wrap gap-2 mb-2">
              <ChoixProvince province={province} setProvince={setProvince} />
              <Choix options={[["2010", "Depuis 2010"], ["2022", "Depuis 2022"]]} valeur={depuis} onChange={setDepuis} />
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={serie} margin={{ top: 10, right: 8, left: -10, bottom: 0 }}>
                <CartesianGrid stroke="#eef1ed" vertical={false} />
                <XAxis dataKey="mois" tickFormatter={fmtM} minTickGap={30} tick={{ fontSize: 11 }} />
                <YAxis yAxisId="s" tick={{ fontSize: 12 }} domain={[0, 0.45]} />
                <YAxis yAxisId="p" orientation="right" tick={{ fontSize: 11 }} unit=" mm" width={52} />
                <Tooltip labelFormatter={moisFr} formatter={(v, n) => [Array.isArray(v) ? `${nf(v[0], 3)} – ${nf(v[1], 3)}` : n.includes("Pluie") ? `${nf(v, 0)} mm` : nf(v, 3), n]} />
                <Bar yAxisId="p" dataKey="pluie" name="Pluie (mm)" fill="#cfe3f2" isAnimationActive={false} />
                <Area yAxisId="s" dataKey="bande" name="Intervalle 80 %" fill="#bfe3c9" stroke="none" isAnimationActive={false} />
                <Line yAxisId="s" dataKey="surface" name="Sol 0-7 cm" stroke="#9aa5ad" dot={false} strokeWidth={1.2} isAnimationActive={false} />
                <Line yAxisId="s" dataKey="sol" name="Sol 7-28 cm (racines)" stroke={COULEURS.vert} dot={false} strokeWidth={2.2} isAnimationActive={false} />
                <Line yAxisId="s" dataKey="prevision" name="Prévision" stroke="#14231b" strokeDasharray="5 3" dot={{ r: 3 }} isAnimationActive={false} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </Section>
        </Col>
      </Row>
      <Section titre="Comparaison des modèles (validation : une saison laissée de côté, 2010-2026)" icone="bi-clipboard-data" className="mt-3">
        <Row className="g-3">
          <Col lg={7}>
            <Table size="sm" className="ch-table-compact mb-0">
              <thead><tr><th>Modèle</th><th className="text-end">Erreur à 1 mois</th><th className="text-end">R² à 1 mois</th><th className="text-end">Erreur à 2 mois</th><th className="text-end">R² à 2 mois</th></tr></thead>
              <tbody>{[...new Set(met.map((m) => m.modele))].map((nom) => {
                const a = met.find((m) => m.modele === nom && m.horizon === 1), b = met.find((m) => m.modele === nom && m.horizon === 2);
                const best1 = Math.min(...met.filter((m) => m.horizon === 1).map((m) => m.mae));
                return (<tr key={nom} className={a.mae === best1 ? "fw-bold" : ""}><td>{nom}</td><td className="text-end">{nf(a.mae, 3)}</td><td className="text-end">{nf(a.r2, 2)}</td><td className="text-end">{nf(b.mae, 3)}</td><td className="text-end">{nf(b.r2, 2)}</td></tr>);
              })}</tbody>
            </Table>
          </Col>
          <Col lg={5}>
            <div className="ch-note small">Variables : humidité actuelle (surface et racines), pluie du mois, évapotranspiration, saison. Les trois modèles
              d'apprentissage font nettement mieux que « recopier le mois en cours » à 1 mois (R² ≈ 0,70 contre 0,49). À 2 mois, l'avantage se réduit :
              la pluie à venir, imprévisible, prend le dessus.</div>
          </Col>
        </Row>
      </Section>
    </>
  );
}

// ================================================================= RÉCOLTES
function Recoltes({ province, setProvince }) {
  const tout = useApi("/region/recolte");
  const [culture, setCulture] = useState("Blé tendre");
  const [vue, setVue] = useState("2026");
  if (!tout.data) return <Etat chargement={tout.chargement} erreur={tout.erreur} hauteur={400} />;
  const d = tout.data;
  const hist = d.historique.filter((r) => r.province === province && r.culture === culture);
  const val = Object.fromEntries(d.validation.filter((r) => r.province === province && r.culture === culture).map((r) => [r.campagne, r.prevision_cv]));
  const prev = d.previsions.filter((r) => r.province === province && r.culture === culture);
  const serie = [...hist.map((r) => ({ campagne: r.campagne, reel: r.rendement_qx_ha, cv: val[r.campagne] })),
    ...prev.map((r) => ({ campagne: r.campagne, prevu: r.rendement_prevu }))];
  const moy = prev[0]?.moyenne_qx_ha;
  const ratioProv = (c) => {
    const g = d.previsions.filter((r) => r.campagne === c);
    return Object.fromEntries(PROVINCES.map((p) => {
      const x = g.filter((r) => r.province === p);
      const s = x.reduce((a, r) => a + r.superficie_ha, 0);
      return [p, s ? x.reduce((a, r) => a + r.ratio_moyenne * r.superficie_ha, 0) / s : null];
    }));
  };
  const risque27 = Object.fromEntries(PROVINCES.map((p) => {
    const x = d.scenarios.filter((r) => r.province === p);
    return [p, x.length ? x.reduce((a, r) => a + r.proba_mauvaise_pct, 0) / x.length : null];
  }));
  const vals = vue === "2027" ? risque27 : ratioProv(+vue);
  const regTot = [...d.region.map((r) => ({ campagne: r.campagne, reel: r.reel_Mqx, prevu_cv: r.prevu_Mqx })),
    ...[2024, 2025, 2026].map((c) => ({ campagne: c, prevu: d.previsions.filter((r) => r.campagne === c).reduce((a, r) => a + r.production_prevue_t, 0) / 1e5,
      officiel: c === 2026 ? d.info.officiel_2026_Mqx : null }))];
  const best = d.metriques[0];
  return (
    <>
      <Row className="g-3 mb-3">
        <Col sm={6} lg={3}><Kpi label="Meilleur modèle" valeur={d.info.meilleur_modele} sous="choisi par validation croisée" /></Col>
        <Col sm={6} lg={3}><Kpi label="Erreur moyenne" valeur={`${nf(best.mae_qx_ha, 1)} q/ha`} sous={`référence : ${nf(d.metriques.at(-1).mae_qx_ha, 1)} q/ha`} /></Col>
        <Col sm={6} lg={3}><Kpi label="R² (province × culture)" valeur={nf(best.r2, 2)} sous="une campagne laissée de côté" /></Col>
        <Col sm={6} lg={3}><Kpi label="Région 2026" valeur={`${nf(regTot.find((r) => r.campagne === 2026 && r.prevu)?.prevu, 1)} Mqx`} sous={`officiel : ${nf(d.info.officiel_2026_Mqx, 1)} Mqx`} /></Col>
      </Row>
      <Row className="g-3">
        <Col lg={5}>
          <Section titre="Carte des zones à risque" icone="bi-map">
            <Choix options={[["2026", "Récolte 2026"], ["2025", "2025"], ["2024", "2024"], ["2027", "Risque 2027"]]} valeur={vue} onChange={setVue} />
            <div className="mt-2">
              <CarteRegion choix={province} onChoix={setProvince} hauteur={290}
                couleurs={Object.fromEntries(PROVINCES.map((p) => [p, vue === "2027" ? (vals[p] == null ? "#e9ede7" : vals[p] > 40 ? "#d7301f" : vals[p] > 25 ? "#fdae61" : "#a6d96a") : echelleRatio(vals[p])]))}
                etiquettes={Object.fromEntries(PROVINCES.map((p) => [p, vals[p] == null ? "" : `${Math.round(vals[p])} %`]))}
                legende={vue === "2027" ? [["#a6d96a", "risque < 25 %"], ["#fdae61", "25-40 %"], ["#d7301f", "> 40 %"]]
                  : [["#d7301f", "< 70 % (à risque)"], ["#fdae61", "70-90 %"], ["#a6d96a", "90-110 %"], ["#1a9850", "> 110 %"]]} />
            </div>
            <div className="small text-secondary mt-1">{vue === "2027" ? "Probabilité d'un rendement < 70 % de la moyenne, en rejouant les hivers 2010-2026." : "Rendement prévu en % de la moyenne de la province (pondéré par les surfaces)."}</div>
          </Section>
        </Col>
        <Col lg={7}>
          <Section titre={`${province} — rendement (quintaux / hectare)`} icone="bi-graph-up">
            <div className="d-flex flex-wrap gap-2 mb-2">
              <ChoixProvince province={province} setProvince={setProvince} />
              <Choix options={Object.keys(CULT)} valeur={culture} onChange={setCulture} />
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={serie} margin={{ top: 10, right: 8, left: -10, bottom: 0 }}>
                <CartesianGrid stroke="#eef1ed" vertical={false} />
                <XAxis dataKey="campagne" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v, n) => [`${nf(v, 1)} q/ha`, n]} />
                {moy && <ReferenceLine y={moy} stroke="#9aa5ad" strokeDasharray="4 3" label={{ value: "moyenne", position: "right", fontSize: 11 }} />}
                <Bar dataKey="reel" name="Officiel (HCP)" fill={CULT[culture]} isAnimationActive={false} radius={[3, 3, 0, 0]} />
                <Bar dataKey="prevu" name="Prévu (pas encore publié)" fill={CULT[culture]} fillOpacity={0.35} stroke={CULT[culture]} strokeDasharray="4 2" isAnimationActive={false} />
                <Line dataKey="cv" name="Prévu en validation" stroke="#14231b" strokeWidth={0} dot={{ r: 4, fill: "#14231b", stroke: "#14231b" }} legendType="circle" isAnimationActive={false} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </ComposedChart>
            </ResponsiveContainer>
            {hist.some((r) => r.note) && <div className="small text-secondary">Avant 2012, Settat inclut Berrechid et El Jadida inclut Sidi Bennour.</div>}
          </Section>
        </Col>
      </Row>
      <Row className="g-3 mt-1">
        <Col lg={6}>
          <Section titre="Réel contre prévu (chaque point = province × culture × campagne)" icone="bi-bullseye">
            <ResponsiveContainer width="100%" height={300}>
              <ScatterChart margin={{ top: 10, right: 10, left: -10, bottom: 10 }}>
                <CartesianGrid stroke="#eef1ed" />
                <XAxis type="number" dataKey="rendement_qx_ha" name="Officiel" unit=" q/ha" tick={{ fontSize: 11 }} domain={[0, 60]} />
                <YAxis type="number" dataKey="prevision_cv" name="Prévu" unit=" q/ha" tick={{ fontSize: 11 }} domain={[0, 60]} />
                <ZAxis range={[28, 28]} />
                <Tooltip formatter={(v) => nf(v, 1)} labelFormatter={() => ""} />
                <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 60, y: 60 }]} stroke="#9aa5ad" strokeDasharray="4 3" />
                {Object.entries(CULT).map(([c, col]) => <Scatter key={c} name={c} data={d.validation.filter((r) => r.culture === c)} fill={col} fillOpacity={0.6} isAnimationActive={false} />)}
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </ScatterChart>
            </ResponsiveContainer>
          </Section>
        </Col>
        <Col lg={6}>
          <Section titre="Production régionale (millions de quintaux)" icone="bi-bar-chart-line">
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={regTot} margin={{ top: 10, right: 8, left: -14, bottom: 0 }}>
                <CartesianGrid stroke="#eef1ed" vertical={false} />
                <XAxis dataKey="campagne" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v, n) => [`${nf(v, 1)} Mqx`, n]} />
                <Bar dataKey="reel" name="Officiel HCP" fill="#b0721a" isAnimationActive={false} />
                <Bar dataKey="prevu" name="Prévu" fill="#e9c46a" isAnimationActive={false} />
                <Line dataKey="prevu_cv" name="Prévu en validation" stroke="#14231b" strokeWidth={0} dot={{ r: 4, fill: "#14231b", stroke: "#14231b" }} legendType="circle" isAnimationActive={false} />
                <Line dataKey="officiel" name="Officiel 2026 (DRA)" stroke={COULEURS.rouge} strokeWidth={0} dot={{ r: 7, fill: COULEURS.rouge, stroke: COULEURS.rouge }} legendType="circle" isAnimationActive={false} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </ComposedChart>
            </ResponsiveContainer>
            <div className="small text-secondary">Somme des provinces publiées chaque année (4 provinces en 2010-2011, 8 depuis 2021). 2010 est mal prévue : hiver très humide sans récolte exceptionnelle.</div>
          </Section>
        </Col>
      </Row>
      <Row className="g-3 mt-1">
        <Col lg={5}>
          <Section titre="Modèles comparés" icone="bi-cpu">
            <Table size="sm" className="ch-table-compact">
              <thead><tr><th>Modèle</th><th className="text-end">Erreur (q/ha)</th><th className="text-end">Erreur relative médiane</th><th className="text-end">R²</th></tr></thead>
              <tbody>{d.metriques.map((m, i) => <tr key={m.modele} className={i === 0 ? "fw-bold" : ""}><td>{m.modele}</td><td className="text-end">{nf(m.mae_qx_ha, 1)}</td><td className="text-end">{nf(m.erreur_relative_mediane, 0)} %</td><td className="text-end">{nf(m.r2, 2)}</td></tr>)}</tbody>
            </Table>
            <div className="small text-secondary">CatBoost n'apporte rien de plus sur un si petit jeu (230 lignes) : XGBoost et la forêt aléatoire couvrent les arbres de décision boostés et moyennés.</div>
          </Section>
        </Col>
        <Col lg={7}>
          <Section titre="Ce qui compte le plus pour le modèle" icone="bi-sliders">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={d.importance.map((r) => ({ ...r, nom: { sol_fev_mar: "Humidité du sol févr.-mars", pluie_nov_jan: "Pluie nov.-janv.", tmax_mar_mai: "Chaleur mars-mai", niveau_province: "Niveau habituel de la province", culture_bd: "Culture : blé dur", culture_orge: "Culture : orge", ndvi_fev_mar: "NDVI févr.-mars" }[r.variable] || r.variable }))}
                layout="vertical" margin={{ top: 0, right: 20, left: 10, bottom: 0 }}>
                <XAxis type="number" unit=" %" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="nom" width={190} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(v) => `${nf(v, 1)} %`} />
                <Bar dataKey="importance_pct" fill={COULEURS.vert} radius={[0, 4, 4, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </Section>
        </Col>
      </Row>
      <Section titre="Scénarios 2027 par province (quintaux / hectare, moyenne des 3 cultures)" icone="bi-signpost-split" className="mt-3">
        <Table size="sm" hover responsive className="ch-table-compact mb-0">
          <thead><tr><th>Province</th><th className="text-end">Hiver sec (10 %)</th><th className="text-end">Hiver normal</th><th className="text-end">Hiver pluvieux (90 %)</th><th className="text-end">Moyenne historique</th><th className="text-end">Risque de mauvaise récolte</th></tr></thead>
          <tbody>{PROVINCES.map((p) => {
            const x = d.scenarios.filter((r) => r.province === p);
            if (!x.length) return null;
            const m = (k) => x.reduce((a, r) => a + r[k], 0) / x.length;
            return (<tr key={p} className={p === province ? "table-active" : ""} onClick={() => setProvince(p)} style={{ cursor: "pointer" }}><td>{p}</td><td className="text-end">{nf(m("annee_seche"), 1)}</td><td className="text-end">{nf(m("annee_normale"), 1)}</td><td className="text-end">{nf(m("annee_pluvieuse"), 1)}</td><td className="text-end">{nf(m("moyenne_qx_ha"), 1)}</td><td className="text-end">{nf(m("proba_mauvaise_pct"), 0)} %</td></tr>);
          })}</tbody>
        </Table>
      </Section>
    </>
  );
}

// ================================================================= BARRAGE
function Barrage() {
  const { data, erreur, chargement } = useApi("/region/barrage");
  if (!data) return <Etat chargement={chargement} erreur={erreur} hauteur={400} />;
  const cap = data.info.capacite_Mm3;
  const serie = [...data.releves.map((r) => ({ t: new Date(r.date).getTime(), date: r.date, releve: r.taux_pct })),
    ...data.trajectoire.filter((_, i) => i % 3 === 0 || i === data.trajectoire.length - 1).map((r) => ({ t: new Date(r.date).getTime(), date: r.date, mediane: r.p50_pct, bande: [r.p10_pct, r.p90_pct] }))];
  const der = data.info.dernier;
  serie.push({ t: new Date(der.date).getTime(), date: der.date, mediane: der.taux_pct, bande: [der.taux_pct, der.taux_pct] });
  serie.sort((a, b) => a.t - b.t);
  const v = data.info.validation;
  return (
    <>
      <Row className="g-3 mb-3">
        <Col sm={6} lg={3}><Kpi label="Al Massira aujourd'hui" valeur={`${nf(der.taux_pct, 1)} %`} sous={`${nf(der.volume_Mm3, 0)} Mm³ sur ${nf(cap, 0)} — relevé du ${new Date(der.date).toLocaleDateString("fr-FR")}`} /></Col>
        {data.prevision.map((p) => (
          <Col sm={6} lg={3} key={p.horizon_jours}><Kpi label={`Dans ${p.horizon_jours} jours`} valeur={`${nf(p.median_pct, 1)} %`} sous={`80 % de chances entre ${nf(p.bas_pct, 1)} et ${nf(p.haut_pct, 1)} %`} /></Col>
        ))}
      </Row>
      <Section titre="Barrage Al Massira : relevés officiels 2019-2026 et prévision à 90 jours" icone="bi-water">
        <ResponsiveContainer width="100%" height={340}>
          <ComposedChart data={serie} margin={{ top: 10, right: 8, left: -10, bottom: 0 }}>
            <CartesianGrid stroke="#eef1ed" vertical={false} />
            <XAxis dataKey="t" type="number" scale="time" domain={["dataMin", "dataMax"]} tick={{ fontSize: 11 }} ticks={[2020, 2021, 2022, 2023, 2024, 2025, 2026, 2027].map((a) => Date.UTC(a, 0, 1))} tickFormatter={(t) => new Date(t).getFullYear()} />
            <YAxis tick={{ fontSize: 12 }} unit=" %" domain={[0, 50]} />
            <Tooltip labelFormatter={(t) => new Date(t).toLocaleDateString("fr-FR")} formatter={(v, n) => [Array.isArray(v) ? `${nf(v[0], 1)} – ${nf(v[1], 1)} %` : `${nf(v, 1)} %`, n]} />
            <ReferenceLine y={10} stroke={COULEURS.rouge} strokeDasharray="4 3" label={{ value: "seuil d'alerte 10 %", position: "insideTopLeft", fontSize: 11, fill: COULEURS.rouge }} />
            <Area dataKey="bande" name="Prévision : 80 % des scénarios" fill="#bcd9ee" stroke="none" isAnimationActive={false} connectNulls />
            <Line dataKey="releve" name="Relevé officiel" stroke={BLEU} strokeWidth={2} dot={{ r: 3 }} connectNulls isAnimationActive={false} />
            <Line dataKey="mediane" name="Prévision médiane" stroke="#14231b" strokeDasharray="5 3" dot={false} connectNulls isAnimationActive={false} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </ComposedChart>
        </ResponsiveContainer>
        <div className="small text-secondary">Plus bas historique : 9,7 Mm³ (0,4 %) en octobre 2024. Remontée spectaculaire en 2025-2026 : pluies exceptionnelles et ~690 Mm³ transférés depuis l'amont du bassin.</div>
      </Section>
      <Row className="g-3 mt-1">
        <Col lg={6}>
          <Section titre="Validation du bilan hydrique" icone="bi-bullseye">
            <ResponsiveContainer width="100%" height={260}>
              <ScatterChart margin={{ top: 10, right: 10, left: -6, bottom: 10 }}>
                <CartesianGrid stroke="#eef1ed" />
                <XAxis type="number" dataKey="dv" name="Variation observée" unit=" Mm³" tick={{ fontSize: 11 }} />
                <YAxis type="number" dataKey="dv_loo" name="Variation prévue" unit=" Mm³" tick={{ fontSize: 11 }} />
                <ZAxis range={[40, 40]} />
                <Tooltip formatter={(v) => nf(v, 0)} />
                <ReferenceLine segment={[{ x: -200, y: -200 }, { x: 500, y: 500 }]} stroke="#9aa5ad" strokeDasharray="4 3" />
                <Scatter data={data.intervalles} fill={BLEU} isAnimationActive={false} />
              </ScatterChart>
            </ResponsiveContainer>
            <div className="small text-secondary">{v.n_intervalles} intervalles entre deux relevés, chacun prédit sans lui (validation « un intervalle laissé de côté ») :
              erreur {nf(v.mae_modele_Mm3, 0)} Mm³ contre {nf(v.mae_persistance_Mm3, 0)} Mm³ en supposant « pas de changement » ; R² = {nf(v.r2, 2)}.</div>
          </Section>
        </Col>
        <Col lg={6}>
          <Section titre="Méthode et limites" icone="bi-info-circle">
            <div className="small">
              <p className="mb-2"><b>Bilan hydrique :</b> variation du stock = k₁ × pluie efficace (pluie sur sols déjà humides, CHIRPS sur la province de Settat)
                − k₂ × évaporation − k₃ × prélèvements d'été − k₄ × pertes proportionnelles à la surface du lac. Coefficients positifs ajustés (moindres carrés non négatifs).</p>
              <p className="mb-2"><b>Prévision 7 / 30 / 90 jours :</b> on rejoue, à partir du dernier relevé, la pluie des mêmes semaines de chaque année 2010-2025 (16 scénarios) ;
                les quantiles 10 / 50 / 90 % donnent la fourchette.</p>
              <p className="mb-2"><b>Risque de pénurie :</b> « {data.info.risque} » — le scénario défavorable à 90 jours reste à {nf(data.prevision.at(-1).bas_pct, 0)} %,
                loin du seuil d'alerte de 10 %. Al Massira contient ≈ {nf(der.volume_Mm3 / data.info.conso_casablanca_Mm3_an, 1)} ans de consommation d'eau potable de Casablanca (≈ 225 Mm³/an).</p>
              <p className="mb-0 text-secondary"><b>Limites :</b> l'essentiel des apports vient de l'amont (Moyen Atlas) et de transferts décidés par l'administration, que la pluie
                locale ne capte qu'en partie ; relevés irréguliers (39 dates). Les petits barrages de la région (Tamesna, El Mellah, El Himer, Ain Kouachia) n'ont pas de série publique récente.</p>
            </div>
          </Section>
        </Col>
      </Row>
      <Section titre={`Les ${data.releves.length} relevés officiels utilisés`} icone="bi-link-45deg" className="mt-3">
        <div style={{ maxHeight: 260, overflowY: "auto" }}>
          <Table size="sm" className="ch-table-compact mb-0">
            <thead><tr><th>Date</th><th className="text-end">Taux</th><th className="text-end">Volume (Mm³)</th><th>Source</th></tr></thead>
            <tbody>{[...data.releves].reverse().map((r) => (
              <tr key={r.date}><td>{new Date(r.date).toLocaleDateString("fr-FR")}</td><td className="text-end">{nf(r.taux_pct, 2)} %</td><td className="text-end">{nf(r.volume_Mm3, 1)}</td>
                <td className="text-truncate" style={{ maxWidth: 380 }}><a href={r.source} target="_blank" rel="noreferrer">{new URL(r.source).hostname.replace("www.", "")}</a></td></tr>))}</tbody>
          </Table>
        </div>
      </Section>
    </>
  );
}

// ================================================================= DONNÉES
const DONNEES = [
  ["Récolte", "Production agricole", "Production du blé et de l'orge (tonnes), par province", "HCP (via FEWS NET)", "reel", "2010-2023"],
  ["Récolte", "Superficie cultivée", "Hectares emblavés par province", "HCP (via FEWS NET)", "reel", "2010-2023"],
  ["Récolte", "Rendement", "Quintaux / hectare (production ÷ superficie)", "Calculé", "reel", "2010-2023 ; prévu 2024-2027"],
  ["Récolte + Barrage", "Précipitations", "Pluie mensuelle (mm) par province", "CHIRPS v2.0 (5 km)", "reel", "sept. 2009 → sept. 2026"],
  ["Récolte + Barrage", "Température", "Moyenne et maximale (°C), jours > 30 °C", "ERA5-Land (Open-Meteo)", "approx", "4 zones → 9 provinces ; minimale : script"],
  ["Récolte + Barrage", "Humidité du sol", "0-7 cm et 7-28 cm (m³/m³)", "ERA5-Land (Open-Meteo)", "approx", "4 zones → 9 provinces"],
  ["Barrage", "Évapotranspiration", "ET0 FAO (mm/mois)", "ERA5 (Open-Meteo)", "approx", "4 zones"],
  ["Récolte", "Végétation", "NDVI février-mars", "MODIS MOD13Q1 (ORNL DAAC)", "collecte", "script data/collecte_provinces.py"],
  ["Récolte", "Type de sol", "Argile, sable, limon, carbone, pH", "SoilGrids 2.0 (ISRIC)", "collecte", "description qualitative en attendant"],
  ["Récolte", "Données géographiques", "Limites des 9 préfectures et provinces", "geoBoundaries ADM2", "reel", "—"],
  ["Barrage", "Stock d'eau / remplissage", "Volume (Mm³) et taux (%) d'Al Massira", "Ministère de l'Équipement et de l'Eau (presse)", "reel", "39 relevés 2019-2026"],
  ["Barrage", "Capacité", "2 649,5 Mm³", "Ministère de l'Équipement et de l'Eau", "reel", "—"],
  ["Barrage", "Apports hydriques", "Volume entrant", "ABH Oum Er-Rbia", "approx", "estimés par la pluie efficace (non publiés en série)"],
  ["Barrage", "Consommation d'eau", "Eau potable (Casablanca ≈ 225 Mm³/an) et irrigation", "Presse (Médias24)", "approx", "ordre de grandeur"],
];
const STATUT = { reel: ["Réel", "reel"], approx: ["Approximation", "approx"], collecte: ["À collecter (script fourni)", "collecte"] };

function Donnees() {
  return (
    <Section titre="Les données : ce qui est réel, approché ou à compléter" icone="bi-database">
      <Table size="sm" hover responsive className="ch-table-compact">
        <thead><tr><th>Module</th><th>Donnée</th><th>Variables</th><th>Source</th><th>Statut</th><th>Période / remarque</th></tr></thead>
        <tbody>{DONNEES.map((d) => (
          <tr key={d[1]}><td className="small text-secondary">{d[0]}</td><td className="fw-semibold">{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td>
            <td><span className={`ch-statut ${STATUT[d[4]][1]}`}>{STATUT[d[4]][0]}</span></td><td className="small">{d[5]}</td></tr>))}</tbody>
      </Table>
      <div className="ch-note small">
        <b>Pour compléter (sur un ordinateur connecté à internet) :</b> <code>python data/collecte_provinces.py</code> télécharge ERA5-Land au centre de chaque
        province (y compris la température minimale), le NDVI MODIS et les propriétés du sol SoilGrids ; puis <code>python data/construire_provinces.py</code> et
        <code> python ml/run_region.py</code>. Les modèles intègrent automatiquement le NDVI s'il est présent. Open Data Maroc (data.gov.ma) ne publie pas, à ce jour,
        de série par province plus récente que celle du HCP.
      </div>
    </Section>
  );
}

export default function Etudiant() {
  const [params, setParams] = useSearchParams();
  const onglet = params.get("onglet") || "pluie";
  const setOnglet = (k) => setParams({ onglet: k }, { replace: true });
  const [province, setProvince] = useState("Settat");
  const provs = useApi("/region/provinces");
  return (
    <>
      <Hero variante="ville" titre="🎓 Espace étudiant — Casablanca-Settat"
        texte="Explorer les données des 9 préfectures et provinces, comparer les modèles d'apprentissage automatique et lire leurs prévisions avec leurs marges d'erreur."
        badges={["🌧️ CHIRPS 2009-2026", "🌱 ERA5-Land", "🌾 HCP 2010-2023", "💧 Al Massira 2019-2026", "🤖 Ridge · Forêt aléatoire · XGBoost"]} />
      <Nav variant="pills" className="ch-onglets gap-1 mb-3 flex-wrap" activeKey={onglet} onSelect={(k) => setOnglet(k)}>
        {[["pluie", "🌧️ Précipitations"], ["sol", "🌱 Humidité du sol"], ["recolte", "🌾 Récoltes"], ["barrage", "💧 Barrages & eau"], ["donnees", "🗂️ Données & méthode"]].map(([k, l]) => (
          <Nav.Item key={k}><Nav.Link eventKey={k}>{l}</Nav.Link></Nav.Item>
        ))}
      </Nav>
      {onglet === "pluie" && <Pluie province={province} setProvince={setProvince} provs={provs.data} />}
      {onglet === "sol" && <Sol province={province} setProvince={setProvince} provs={provs.data} />}
      {onglet === "recolte" && <Recoltes province={province} setProvince={setProvince} />}
      {onglet === "barrage" && <Barrage />}
      {onglet === "donnees" && <Donnees />}
    </>
  );
}
