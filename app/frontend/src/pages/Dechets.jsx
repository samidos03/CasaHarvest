import { useMemo, useState } from "react";
import { Col, Row, Table } from "react-bootstrap";
import {
  Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { COULEURS, dateFr, nf, useApi } from "../api";
import { Choix, Etat, Hero, Kpi, Section } from "../components/Ui";
import CarteSvg from "../components/CarteSvg";

const TYPO = {
  "Pôles touristiques et hôteliers": "#b0721a",
  "Quartiers aisés et mixtes (part touristique notable)": "#1d6fa5",
  "Quartiers à forte saison estivale": "#3f9e6a",
  "Quartiers populaires denses (pic de l'Aïd)": "#7a5aa6",
  "Quartiers résidentiels": "#6b7570",
};
const COURT = {
  "Pôles touristiques et hôteliers": "Pôle touristique", "Quartiers aisés et mixtes (part touristique notable)": "Aisé & mixte",
  "Quartiers à forte saison estivale": "Saison estivale", "Quartiers populaires denses (pic de l'Aïd)": "Populaire dense",
};
const SCENARIOS = [["semaine", "Semaine prochaine"], ["haute_saison", "Haute saison touristique"], ["aid", "Semaine de l'Aïd al-Adha"]];
const COUL_TOURNEES = ["#0b7a43", "#1d6fa5", "#b0721a", "#7a5aa6", "#c1272d", "#3f7280", "#9a6b00", "#2c6e49"];

function Serie({ ville }) {
  const { data, erreur, chargement } = useApi(`/dechets/serie?ville=${encodeURIComponent(ville)}`);
  const d = useMemo(() => {
    if (!data) return [];
    const h = data.historique.map((r) => ({ semaine: r.semaine, reel: r.tonnes / 7, aid: r.aid_al_adha, ram: r.ramadan }));
    const last = h[h.length - 1];
    const p = data.prevision.map((r) => ({ semaine: r.semaine, prevision: r.prevision / 7, bande: [r.bas / 7, r.haut / 7] }));
    return [...h.slice(0, -1), { ...last, prevision: last.reel, bande: [last.reel, last.reel] }, ...p];
  }, [data]);
  if (!data) return <Etat chargement={chargement} erreur={erreur} hauteur={340} />;
  const aids = d.filter((r, i) => r.aid && !d[i - 1]?.aid).map((r) => r.semaine);
  return (
    <Section titre={`${ville} — déchets ménagers collectés (tonnes par jour, moyenne de la semaine)`} icone="bi-graph-up">
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={d} margin={{ top: 14, right: 8, left: 4, bottom: 0 }}>
          <CartesianGrid stroke="#eef1ed" vertical={false} />
          <XAxis dataKey="semaine" minTickGap={40} tick={{ fontSize: 12 }} tickFormatter={(s) => dateFr(s, { month: "short", year: "2-digit" })} />
          <YAxis tick={{ fontSize: 12 }} width={56} domain={["auto", "auto"]} tickFormatter={(v) => nf(v, 0)} unit=" t" />
          <Tooltip labelFormatter={(s) => `Semaine du ${dateFr(s)}`} formatter={(v, n) => [Array.isArray(v) ? `${nf(v[0], 0)} – ${nf(v[1], 0)} t/j` : `${nf(v, 0)} t/j`, n]} />
          {aids.map((s) => <ReferenceLine key={s} x={s} stroke="#7a5aa6" strokeDasharray="3 3" label={{ value: "Aïd", position: "top", fontSize: 11, fill: "#7a5aa6" }} />)}
          <Area dataKey="bande" name="Intervalle 80 %" stroke="none" fill="#cfe8da" fillOpacity={0.8} isAnimationActive={false} />
          <Line dataKey="reel" name="Observé" stroke={COULEURS.encre} strokeWidth={1.8} dot={false} isAnimationActive={false} />
          <Line dataKey="prevision" name="Prévision 8 semaines" stroke={COULEURS.vert} strokeWidth={2.4} strokeDasharray="6 3" dot={{ r: 2.5 }} isAnimationActive={false} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="small text-secondary">Pics réguliers : Aïd al-Adha (+50 à +60 % dans les quartiers populaires), Ramadan (+15 %), été (retour des MRE, saison balnéaire à Agadir). Les nuitées prévues par le module Tourisme alimentent la prévision.</div>
    </Section>
  );
}

function Tournees({ ville }) {
  const [sc, setSc] = useState("semaine");
  const { data, erreur, chargement } = useApi(`/dechets/tournees?ville=${encodeURIComponent(ville)}&scenario=${sc}`);
  return (
    <Section titre="Optimisation des tournées de collecte (une journée)" icone="bi-truck">
      <div className="mb-3"><Choix options={SCENARIOS} valeur={sc} onChange={setSc} /></div>
      <Etat chargement={chargement} erreur={erreur} hauteur={420}>
        {data && (
          <Row className="g-3">
            <Col lg={8}>
              <CarteSvg largeur={760} hauteur={430}
                traces={data.tournees.filter((t) => t.points.length > 1).map((t, i) => ({ coords: t.trace, couleur: COUL_TOURNEES[i % COUL_TOURNEES.length], epaisseur: 2.2 }))}
                points={[
                  ...data.points.map((p) => ({ lat: p.lat, lon: p.lon, r: 2.5 + Math.sqrt(p.tonnes) * 0.9, couleur: "#0b7a43", opacite: 0.55, titre: `${p.point} : ${nf(p.tonnes, 1)} t/j` })),
                  { lat: data.depot.lat, lon: data.depot.lon, r: 7, couleur: "#1f2a24", forme: "depot", label: data.depot.nom, taillePolice: 22, titre: data.depot.nom },
                ]} />
              <div className="ch-legende mt-2"><span><i style={{ background: "#0b7a43" }} />point de regroupement (taille = tonnes/jour)</span><span><i style={{ background: "#1f2a24", borderRadius: 2 }} />centre de traitement</span><span>lignes : tournées groupées (les chargements pleins font un aller-retour direct)</span></div>
            </Col>
            <Col lg={4}>
              <Row className="g-2">
                <Col xs={6}><Kpi label="Tonnes / jour" valeur={nf(data.tonnes_jour, 0)} /></Col>
                <Col xs={6}><Kpi label="Camions" valeur={data.camions} sous={<>sans optimisation : {data.camions_naif}</>} /></Col>
                <Col xs={6}><Kpi label="Km parcourus" valeur={nf(data.km, 0)} sous={<>au lieu de {nf(data.km_naif, 0)}</>} /></Col>
                <Col xs={6}><Kpi label="Gain" valeur={<span className="text-success">−{nf(data.gain_km_pct, 0)} %</span>} sous="de kilomètres" /></Col>
              </Row>
              <div className="small fw-semibold mt-3 mb-1">Camions nécessaires selon le scénario</div>
              <ResponsiveContainer width="100%" height={150}>
                <BarChart data={data.comparaison.map((c) => ({ ...c, nom: SCENARIOS.find((s) => s[0] === c.scenario)[1].replace("Semaine de l'", "").replace(" touristique", "") }))} margin={{ top: 4, right: 4, left: -18, bottom: 0 }}>
                  <XAxis dataKey="nom" tick={{ fontSize: 11 }} interval={0} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => [`${v} camions`, "Flotte"]} />
                  <Bar dataKey="camions" fill={COULEURS.vert} radius={[4, 4, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
              <div className="small text-secondary mt-1">Hypothèses : benne de 10 t, 3 rotations par camion et par jour, distances routières ≈ 1,35 × vol d'oiseau. Méthode : chargements pleins en direct, reliquats regroupés par l'algorithme de Clarke-Wright, puis ordre de passage amélioré par 2-opt.</div>
            </Col>
          </Row>
        )}
      </Etat>
    </Section>
  );
}

export default function Dechets() {
  const [ville, setVille] = useState("Marrakech");
  const q = useApi(`/dechets/quartiers?ville=${encodeURIComponent(ville)}`);
  const ev = useApi("/dechets/evaluation");
  const tot = q.data ? q.data.reduce((a, r) => a + (r.prevision_semaine || 0), 0) / 7 : null;
  return (
    <>
      <Hero titre="🗑️ Déchets ménagers par quartier"
        texte="Estimer les tonnes à collecter dans chaque quartier selon la population, le type d'habitat, le calendrier et le tourisme — puis dimensionner la flotte et optimiser les tournées."
        badges={["📍 Marrakech · Casablanca · Agadir", "🏘️ 29 quartiers, hebdomadaire 2019-2026", "🤖 K-means + XGBoost", "🚛 Clarke-Wright + 2-opt"]} />
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <Choix options={["Marrakech", "Casablanca", "Agadir"]} valeur={ville} onChange={setVille} />
        {tot && <div className="text-secondary">Semaine prochaine : <b className="text-dark fs-5">{nf(tot, 0)} t/jour</b> prévues</div>}
      </div>
      <Serie ville={ville} />
      <Row className="g-3 mt-1">
        <Col xl={7}>
          <Section titre="Quartiers : production et typologie" icone="bi-houses">
            <Etat chargement={q.chargement} erreur={q.erreur}>
              {q.data && (
                <Table size="sm" hover responsive className="ch-table-compact mb-0">
                  <thead><tr><th>Quartier</th><th>Typologie (K-means)</th><th className="text-end">Habitants</th><th className="text-end">kg/hab/j</th><th className="text-end">Part tourisme</th><th className="text-end">Effet Aïd</th><th className="text-end">Prévu (t/j)</th></tr></thead>
                  <tbody>{q.data.map((r) => (
                    <tr key={r.quartier}>
                      <td className="fw-semibold">{r.quartier}<div className="small text-secondary fw-normal">{r.habitat}</div></td>
                      <td><span className="ch-pill" style={{ background: `${TYPO[r.typologie] || "#6b7570"}1a`, color: TYPO[r.typologie] || "#6b7570" }} title={r.typologie}>{COURT[r.typologie] || r.typologie}</span></td>
                      <td className="text-end">{nf(r.population, 0)}</td>
                      <td className="text-end">{nf(r.kg_hab_j, 2)}</td>
                      <td className="text-end">{nf(r.part_touristique, 0)} %</td>
                      <td className="text-end">+{nf(r.effet_aid, 0)} %</td>
                      <td className="text-end fw-semibold">{nf(r.prevision_semaine / 7, 0)}</td>
                    </tr>))}
                  </tbody>
                </Table>
              )}
            </Etat>
          </Section>
        </Col>
        <Col xl={5}>
          <Section titre="Carte des quartiers" icone="bi-geo">
            {q.data && (
              <CarteSvg largeur={460} hauteur={330} marge={0.12}
                points={q.data.map((r) => ({ lat: r.lat, lon: r.lon, r: 3 + Math.sqrt(r.prevision_semaine / 7) * 0.9, couleur: TYPO[r.typologie],
                  label: r.quartier, taillePolice: 11, titre: `${r.quartier} : ${nf(r.prevision_semaine / 7, 0)} t/j` }))} />
            )}
            <div className="ch-legende mt-2">{Object.entries(TYPO).slice(0, 4).map(([k, c]) => <span key={k}><i style={{ background: c }} />{k}</span>)}</div>
          </Section>
        </Col>
      </Row>
      <div className="mt-3"><Tournees ville={ville} /></div>
      <Section titre="Fiabilité de la prévision (test sur les 12 derniers mois, horizons 1 à 8 semaines)" icone="bi-clipboard-data" className="mt-3">
        <Etat chargement={ev.chargement} erreur={ev.erreur}>
          {ev.data && (
            <Row className="g-3">
              <Col lg={5}>
                <Table size="sm" className="ch-table-compact mb-0">
                  <thead><tr><th>Ville</th><th className="text-end">XGBoost</th><th className="text-end">Dernière semaine</th><th className="text-end">Année passée</th></tr></thead>
                  <tbody>{ev.data.metriques.map((m) => (
                    <tr key={m.ville} className={m.ville === "Toutes" ? "fw-bold" : ""}><td>{m.ville}</td><td className="text-end">{nf(m.mape_modele, 1)} %</td>
                      <td className="text-end">{nf(m.mape_persistance, 1)} %</td><td className="text-end">{nf(m.mape_annee_passee, 1)} %</td></tr>))}
                  </tbody>
                </Table>
              </Col>
              <Col lg={7}>
                <div className="ch-note mb-2">
                  Erreur moyenne de <b>{nf(ev.data.metriques.at(-1).mape_modele, 1)} %</b>. Pendant le Ramadan et l'Aïd, quand la collecte doit être renforcée,
                  le modèle se trompe de <b>{nf(ev.data.exceptionnelles.mape_modele, 1)} %</b> contre <b>{nf(ev.data.exceptionnelles.mape_persistance, 1)} %</b> si l'on recopie la semaine précédente.
                </div>
                <div className="small text-secondary">
                  {ev.data.typologies.length} typologies trouvées par K-means (nombre choisi par le score de silhouette) :{" "}
                  {ev.data.typologies.map((t) => `${t.typologie} (${t.n})`).join(" · ")}.
                </div>
              </Col>
            </Row>
          )}
        </Etat>
      </Section>
    </>
  );
}
