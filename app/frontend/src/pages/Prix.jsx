import { useMemo, useState } from "react";
import { Button, ButtonGroup, Col, Form, ProgressBar, Row, Tab, Table, Tabs } from "react-bootstrap";
import {
  Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis,
} from "recharts";
import { COULEURS, ICONES, dateFr, nf, useApi } from "../api";
import { Etat, Fleche, Hero, Kpi, PillErreur, Section } from "../components/Ui";

const FAMILLES = ["Tous", "Légumes", "Fruits", "Viandes"];
const moisCourt = (d) => new Date(d).toLocaleDateString("fr-FR", { month: "short", year: "2-digit" });

function GraphiquePrevision({ data }) {
  const lignes = useMemo(() => {
    const h = data.historique.map((r) => ({ date: r.date, prix: r.prix, releve: r.releve ? r.prix : null }));
    const der = h[h.length - 1];
    der.prevision = data.dernier_prix;
    der.bande = [data.dernier_prix, data.dernier_prix];
    const f = data.prevision.map((p) => ({ date: p.semaine, prevision: p.prevision, bande: [p.bas, p.haut] }));
    return [...h, ...f];
  }, [data]);
  return (
    <ResponsiveContainer width="100%" height={380}>
      <ComposedChart data={lignes} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="#eef1ed" vertical={false} />
        <XAxis dataKey="date" tickFormatter={moisCourt} minTickGap={40} tick={{ fontSize: 12, fill: COULEURS.gris }} />
        <YAxis tick={{ fontSize: 12, fill: COULEURS.gris }} unit=" DH" width={62} domain={["auto", "auto"]} />
        <Tooltip labelFormatter={(d) => `Semaine du ${dateFr(d)}`}
          formatter={(v, n) => (Array.isArray(v) ? [`${nf(v[0])} – ${nf(v[1])} DH`, n] : [`${nf(v)} DH/kg`, n])} />
        <Legend wrapperStyle={{ fontSize: 13 }} />
        <Area dataKey="bande" name="Fourchette 80 %" fill={COULEURS.vert} fillOpacity={0.15} stroke="none" isAnimationActive={false} />
        <Line dataKey="prix" name="Historique" stroke="#55626b" strokeWidth={2} dot={false} type="monotone" isAnimationActive={false} />
        <Scatter dataKey="releve" name="Semaines relevées" fill="#fff" stroke={COULEURS.encre} strokeWidth={1.6} isAnimationActive={false} />
        <Line dataKey="prevision" name="Prévision XGBoost" stroke={COULEURS.vert} strokeWidth={3}
          dot={{ r: 3.5, fill: COULEURS.vert }} isAnimationActive={false} />
        <ReferenceLine x={data.date_dernier_releve} stroke={COULEURS.gris} strokeDasharray="4 4" />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function OngletPrevision({ produit, h }) {
  const { data, erreur, chargement } = useApi(`/prix/prevision/${encodeURIComponent(produit)}?h=${h}`);
  return (
    <Etat chargement={chargement} erreur={erreur} hauteur={420}>
      {data && (() => {
        const p0 = data.dernier_prix, fin = data.prevision[data.prevision.length - 1];
        const v = (fin.prevision / p0 - 1) * 100;
        const pic = data.prevision.reduce((a, b) => (b.prevision > a.prevision ? b : a));
        const tendance = v > 3 ? "hausse" : v < -3 ? "baisse" : "stabilité";
        const csv = () => {
          const t = "semaine;prevision_DH_kg;bas_80;haut_80\n" +
            data.prevision.map((p) => `${p.semaine};${nf(p.prevision)};${nf(p.bas)};${nf(p.haut)}`).join("\n");
          const a = document.createElement("a");
          a.href = URL.createObjectURL(new Blob(["﻿" + t], { type: "text/csv" }));
          a.download = `prevision_${produit}_${h}sem.csv`;
          a.click();
        };
        return (
          <>
            <Row className="g-3 mb-3">
              <Col sm={6} xl={3}><Kpi label={`${ICONES[produit] || "🛒"} Dernier prix relevé`} valeur={`${nf(p0)} DH`} sous={`le ${dateFr(data.date_dernier_releve)}`} /></Col>
              <Col sm={6} xl={3}><Kpi label={`Prévision à ${h} sem.`} valeur={`${nf(fin.prevision)} DH`} sous={<><Fleche v={v} /> · semaine du {dateFr(fin.semaine, { day: "2-digit", month: "2-digit" })}</>} /></Col>
              <Col sm={6} xl={3}><Kpi label="Fourchette probable (80 %)" valeur={`${nf(fin.bas)} – ${nf(fin.haut)}`} sous={<>DH/kg · <PillErreur err={data.erreur_attendue_pct} /></>} /></Col>
              <Col sm={6} xl={3}><Kpi label="Pic prévu" valeur={`${nf(pic.prevision)} DH`} sous={`semaine du ${dateFr(pic.semaine)}`} /></Col>
            </Row>
            <Section titre={`${produit} — 12 derniers mois et prévision XGBoost`} icone="bi-graph-up">
              <GraphiquePrevision data={data} />
              <div className="small text-secondary mt-1">Points : semaines réellement relevées · ligne grise : interpolation entre relevés · zone verte : intervalle de prévision à 80 %.</div>
            </Section>
            <Row className="g-3 mt-1">
              <Col lg={7}>
                <Section titre="Détail semaine par semaine" icone="bi-table">
                  <Table hover size="sm" className="ch-table-compact mb-0">
                    <thead><tr><th>Semaine (mercredi)</th><th className="text-end">Prévision</th><th className="text-end">Bas 80 %</th><th className="text-end">Haut 80 %</th><th className="text-end">vs dernier prix</th></tr></thead>
                    <tbody>
                      {data.prevision.map((p) => (
                        <tr key={p.semaine}>
                          <td>{dateFr(p.semaine)}</td><td className="text-end fw-semibold">{nf(p.prevision)} DH</td>
                          <td className="text-end">{nf(p.bas)} DH</td><td className="text-end">{nf(p.haut)} DH</td>
                          <td className="text-end"><Fleche v={(p.prevision / p0 - 1) * 100} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </Section>
              </Col>
              <Col lg={5}>
                <Section titre="À retenir" icone="bi-lightbulb">
                  <div className="ch-note mb-3">
                    <b>{produit}</b> : {tendance} attendue d'ici {h} semaine(s) (<Fleche v={v} />), de {nf(p0)} à <b>{nf(fin.prevision)} DH/kg</b>.
                    <br /><br />Dans 8 cas sur 10, le prix devrait rester entre <b>{nf(fin.bas)}</b> et <b>{nf(fin.haut)} DH/kg</b>.
                    <br /><br />Erreur moyenne de XGBoost à cet horizon pour ce produit : <b>±{nf(data.erreur_attendue_pct, 0)} %</b>.
                  </div>
                  <Button variant="outline-primary" className="w-100" onClick={csv}><i className="bi bi-download me-2" />Télécharger la prévision (CSV)</Button>
                </Section>
              </Col>
            </Row>
          </>
        );
      })()}
    </Etat>
  );
}

function OngletMarche({ h, famille }) {
  const { data, erreur, chargement } = useApi(`/prix/marche?h=${h}`);
  const vue = (data || []).filter((d) => famille === "Tous" || d.famille === famille);
  const tri = [...vue].sort((a, b) => b.variation_pct - a.variation_pct);
  return (
    <Etat chargement={chargement} erreur={erreur} hauteur={420}>
      {data && (
        <>
          <Row className="g-3 mb-3">
            <Col md={4}><Kpi label="En hausse attendue" valeur={`${vue.filter((d) => d.variation_pct > 3).length} produits`} sous="variation > +3 %" icone="bi-arrow-up-right" /></Col>
            <Col md={4}><Kpi label="En baisse attendue" valeur={`${vue.filter((d) => d.variation_pct < -3).length} produits`} sous="variation < −3 %" icone="bi-arrow-down-right" /></Col>
            <Col md={4}>{tri.length > 0 && (() => {
              const top = [...vue].sort((a, b) => Math.abs(b.variation_pct) - Math.abs(a.variation_pct))[0];
              return <Kpi label="Plus forte variation" valeur={`${ICONES[top.produit] || ""} ${top.produit}`} sous={<Fleche v={top.variation_pct} />} />;
            })()}</Col>
          </Row>
          <Row className="g-3">
            <Col lg={5}>
              <Section titre={`Variation prévue à ${h} semaine(s)`} icone="bi-bar-chart">
                <ResponsiveContainer width="100%" height={Math.max(300, tri.length * 28)}>
                  <BarChart data={tri} layout="vertical" margin={{ left: 10, right: 20 }}>
                    <CartesianGrid stroke="#eef1ed" horizontal={false} />
                    <XAxis type="number" unit=" %" tick={{ fontSize: 12 }} />
                    <YAxis type="category" dataKey="produit" width={120} tick={{ fontSize: 12 }} />
                    <Tooltip formatter={(v) => [`${nf(v, 1)} %`, "Variation"]} />
                    <ReferenceLine x={0} stroke="#999" />
                    <Bar dataKey="variation_pct" radius={[0, 4, 4, 0]} isAnimationActive={false}>
                      {tri.map((d) => <Cell key={d.produit} fill={d.variation_pct > 0 ? COULEURS.rouge : COULEURS.vert} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Section>
            </Col>
            <Col lg={7}>
              <Section titre="Tous les produits" icone="bi-basket">
                <Table hover size="sm" responsive className="ch-table-compact mb-0">
                  <thead><tr><th>Produit</th><th>6 derniers mois</th><th className="text-end">Dernier prix</th><th className="text-end">Prévision</th><th className="text-end">Variation</th><th style={{ width: 110 }}>Erreur moy.</th></tr></thead>
                  <tbody>
                    {vue.map((d) => (
                      <tr key={d.produit}>
                        <td className="text-nowrap">{ICONES[d.produit] || "🛒"} {d.produit}</td>
                        <td style={{ width: 130 }}>
                          <ResponsiveContainer width={120} height={30}>
                            <LineChart data={d.evolution}><Line dataKey="prix" stroke={COULEURS.vert} dot={false} strokeWidth={1.6} isAnimationActive={false} /><YAxis hide domain={["auto", "auto"]} /></LineChart>
                          </ResponsiveContainer>
                        </td>
                        <td className="text-end">{nf(d.dernier_prix)} DH</td>
                        <td className="text-end fw-semibold">{nf(d.prevision)} DH</td>
                        <td className="text-end"><Fleche v={d.variation_pct} /></td>
                        <td><ProgressBar now={Math.min(d.erreur_pct, 40)} max={40} variant={d.erreur_pct < 10 ? "success" : d.erreur_pct < 20 ? "warning" : "danger"} style={{ height: 8 }} title={`±${nf(d.erreur_pct, 0)} %`} /></td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </Section>
            </Col>
          </Row>
        </>
      )}
    </Etat>
  );
}

function OngletEvaluation() {
  const { data, erreur, chargement } = useApi("/prix/evaluation");
  return (
    <Etat chargement={chargement} erreur={erreur} hauteur={420}>
      {data && (() => {
        const t = data.par_horizon, h1 = t[0], h8 = t[t.length - 1];
        const sens = t.reduce((a, b) => a + b.sens_correct_pct, 0) / t.length;
        return (
          <>
            <p className="text-secondary">Backtest sans fuite de données : sur les 40 dernières semaines, toutes les 2 semaines, XGBoost est ré-entraîné avec les seuls prix connus à cette date, puis ses prévisions sont comparées aux prix réellement relevés.</p>
            <Row className="g-3 mb-3">
              <Col sm={6} xl={3}><Kpi label="Erreur médiane à 1 sem." valeur={`${nf(h1.erreur_mediane_pct, 1)} %`} sous="la moitié des prévisions font mieux" /></Col>
              <Col sm={6} xl={3}><Kpi label="Prévisions à ±10 % (1 sem.)" valeur={`${nf(h1.part_a_10pct, 0)} %`} sous={`${nf(h8.part_a_10pct, 0)} % à 8 semaines`} /></Col>
              <Col sm={6} xl={3}><Kpi label="Erreur moyenne (MAPE)" valeur={`${nf(h1.MAPE_pct, 1)} → ${nf(h8.MAPE_pct, 1)} %`} sous="de 1 à 8 semaines" /></Col>
              <Col sm={6} xl={3}><Kpi label="Sens de variation correct" valeur={`${nf(sens, 0)} %`} sous="quand le prix bouge d'au moins 2 %" /></Col>
            </Row>
            <Row className="g-3">
              <Col lg={7}>
                <Section titre="Erreur selon l'horizon" icone="bi-graph-up">
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={t}>
                      <CartesianGrid stroke="#eef1ed" />
                      <XAxis dataKey="horizon" tickFormatter={(v) => `${v} sem.`} tick={{ fontSize: 12 }} />
                      <YAxis unit=" %" tick={{ fontSize: 12 }} />
                      <Tooltip formatter={(v) => `${nf(v, 1)} %`} labelFormatter={(v) => `Horizon ${v} semaine(s)`} />
                      <Legend />
                      <Line dataKey="MAPE_pct" name="Erreur moyenne (MAPE)" stroke={COULEURS.vert} strokeWidth={2.5} isAnimationActive={false} />
                      <Line dataKey="erreur_mediane_pct" name="Erreur médiane" stroke={COULEURS.or} strokeWidth={2.5} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </Section>
              </Col>
              <Col lg={5}>
                <Section titre="Ce que XGBoost a appris" icone="bi-cpu">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={data.importance} layout="vertical" margin={{ left: 10 }}>
                      <XAxis type="number" tickFormatter={(v) => `${Math.round(v * 100)} %`} tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="variable" width={170} tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v) => [`${nf(v * 100, 1)} %`, "Part du gain"]} />
                      <Bar dataKey="importance" fill={COULEURS.vert} radius={[0, 4, 4, 0]} isAnimationActive={false} />
                    </BarChart>
                  </ResponsiveContainer>
                </Section>
              </Col>
            </Row>
            <Section titre="Erreur moyenne par produit (tous horizons)" icone="bi-bullseye" className="mt-3">
              <Row className="g-2">
                {data.par_produit.map((p) => (
                  <Col md={6} lg={4} key={p.produit}>
                    <div className="d-flex justify-content-between small"><span>{ICONES[p.produit] || "🛒"} {p.produit}</span><b>{nf(p.erreur_pct, 1)} %</b></div>
                    <ProgressBar now={Math.min(p.erreur_pct, 40)} max={40} variant={p.erreur_pct < 10 ? "success" : p.erreur_pct < 20 ? "warning" : "danger"} style={{ height: 7 }} />
                  </Col>
                ))}
              </Row>
            </Section>
          </>
        );
      })()}
    </Etat>
  );
}

export default function Prix() {
  const produits = useApi("/prix/produits");
  const [famille, setFamille] = useState("Tous");
  const [produit, setProduit] = useState("Tomate");
  const [h, setH] = useState(8);
  const [onglet, setOnglet] = useState("prevision");
  const choix = (produits.data || []).filter((p) => famille === "Tous" || p.famille === famille);
  const changerFamille = (f) => {
    setFamille(f);
    const c = (produits.data || []).filter((p) => f === "Tous" || p.famille === f);
    if (c.length && !c.find((p) => p.produit === produit)) setProduit(c[0].produit);
  };
  return (
    <>
      <Hero titre="🧺 Prix du marché de gros" texte="Marché de gros des fruits et légumes et abattoirs de Casablanca — prix en DH/kg, prévus semaine par semaine par XGBoost."
        badges={["🤖 XGBoost · 1 à 8 semaines", "📰 bulletins de Casablanca Prestations", "🌦️ saison, Ramadan, météo du Souss"]} />
      <Section className="mb-3">
        <Row className="g-3 align-items-end">
          <Col md="auto">
            <Form.Label className="small fw-semibold">Famille</Form.Label><br />
            <ButtonGroup>{FAMILLES.map((f) => <Button key={f} size="sm" variant={famille === f ? "primary" : "outline-primary"} onClick={() => changerFamille(f)}>{f}</Button>)}</ButtonGroup>
          </Col>
          <Col md={4}>
            <Form.Label className="small fw-semibold">Produit</Form.Label>
            <Form.Select value={produit} onChange={(e) => setProduit(e.target.value)} disabled={onglet !== "prevision"}>
              {choix.map((p) => <option key={p.produit} value={p.produit}>{ICONES[p.produit] || "🛒"}  {p.produit}</option>)}
            </Form.Select>
          </Col>
          <Col md>
            <Form.Label className="small fw-semibold">Horizon : <b>{h} semaine(s)</b></Form.Label>
            <Form.Range min={1} max={8} value={h} onChange={(e) => setH(Number(e.target.value))} disabled={onglet === "evaluation"} />
          </Col>
        </Row>
      </Section>
      <Tabs activeKey={onglet} onSelect={setOnglet} className="mb-3" variant="pills">
        <Tab eventKey="prevision" title={<><i className="bi bi-graph-up me-1" />Prévision</>}>{onglet === "prevision" && <OngletPrevision produit={produit} h={h} />}</Tab>
        <Tab eventKey="marche" title={<><i className="bi bi-basket me-1" />Vue d'ensemble du marché</>}>{onglet === "marche" && <OngletMarche h={h} famille={famille} />}</Tab>
        <Tab eventKey="evaluation" title={<><i className="bi bi-clipboard-data me-1" />Évaluation du modèle</>}>{onglet === "evaluation" && <OngletEvaluation />}</Tab>
      </Tabs>
    </>
  );
}
