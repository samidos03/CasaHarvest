import { Col, Row, Table } from "react-bootstrap";
import { Hero, Section } from "../components/Ui";

/** Schéma « grand public » : XGBoost expliqué avec l'exemple de la tomate (prévision du 4/11/2026 à 8 semaines). */
function SchemaTomate() {
  const boite = (x, titre, lignes, fond, bord, cTitre, cTexte) => (
    <g>
      <rect x={x} y={40} width={170} height={230} rx={12} fill={fond} stroke={bord} strokeWidth={0.8} />
      <text x={x + 85} y={66} textAnchor="middle" dominantBaseline="central" fontSize={14} fontWeight={600} fill={cTitre}>{titre}</text>
      {lignes.map(([y, t, gras]) => (
        <text key={y} x={x + 85} y={y} textAnchor="middle" dominantBaseline="central" fontSize={gras ? 14 : 12}
          fontWeight={gras ? 600 : 400} fill={gras ? cTitre : cTexte}>{t}</text>
      ))}
    </g>
  );
  return (
    <svg width="100%" viewBox="0 0 680 470" role="img" style={{ maxWidth: 880, display: "block", margin: "0 auto" }}>
      <title>XGBoost expliqué simplement avec la tomate</title>
      <defs>
        <marker id="fl" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M2 1L8 5L2 9" fill="none" stroke="#6B7570" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </marker>
      </defs>
      {boite(40, "1. On lui montre", [[100, "Prix aujourd'hui :"], [120, "7,50 DH le kilo", true], [154, "Le prix a triplé"], [172, "en 3 mois"], [206, "L'hiver approche"]], "#F1EFE8", "#888780", "#2C2C2A", "#5F5E5A")}
      <line x1={212} y1={155} x2={251} y2={155} stroke="#6B7570" strokeWidth={1.5} markerEnd="url(#fl)" />
      {boite(255, "2. Il se souvient", [[100, "Après une flambée,"], [118, "le prix redescend"], [136, "souvent"], [170, "En hiver, la tomate"], [188, "du Souss arrive :"], [206, "le prix baisse"]], "#EEEDFE", "#7F77DD", "#3C3489", "#534AB7")}
      <line x1={427} y1={155} x2={466} y2={155} stroke="#6B7570" strokeWidth={1.5} markerEnd="url(#fl)" />
      {boite(470, "3. Il prévoit", [[112, "≈ 6,35 DH le kilo", true], [134, "dans 8 semaines"], [152, "(une baisse de 15 %)"], [188, "Sans doute entre"], [206, "4 et 10 DH"]], "#E7F3EC", "#0B7A43", "#0B5A33", "#0B7A43")}
      <text x={340} y={304} textAnchor="middle" dominantBaseline="central" fontSize={14} fontWeight={600} fill="#1F2A24">Dans sa « tête » : 400 petites règles simples</text>
      {Array.from({ length: 10 }, (_, i) => <circle key={i} cx={175 + 28 * i} cy={336} r={7} fill="#EEEDFE" stroke="#7F77DD" strokeWidth={0.8} />)}
      <text x={470} y={336} textAnchor="middle" dominantBaseline="central" fontSize={14} fontWeight={600} fill="#3C3489">… × 400</text>
      <text x={340} y={366} textAnchor="middle" dominantBaseline="central" fontSize={12} fill="#5F5E5A">Chacune corrige un peu les erreurs des précédentes, comme une équipe qui affine une estimation</text>
      <rect x={80} y={392} width={520} height={48} rx={8} fill="#FFFFFF" stroke="#B4B2A9" strokeWidth={0.8} />
      <text x={340} y={416} textAnchor="middle" dominantBaseline="central" fontSize={14} fontWeight={600} fill="#1F2A24">Testé sur le passé : 3 fois sur 4, moins de 10 % d'erreur à 1 semaine</text>
    </svg>
  );
}

const MODULES = [
  ["💧 Eau & sécheresse", "Indice SPI-3 du mois suivant, par zone", "Ridge (régression linéaire régularisée)", "Validation temporelle 2018-2026 : R² 0,63 à 1 mois, 76 % des sécheresses détectées"],
  ["🌾 Récolte", "Rendement du blé tendre, du blé dur et de l'orge (q/ha)", "Hybride : XGBoost + garde-fou Ridge hors des valeurs connues", "Une campagne laissée de côté : R² 0,43 ; 2026 : 26,3 Mqx prévus contre 25,8 officiels"],
  ["🧺 Prix du marché", "Prix de gros hebdomadaire de 19 produits (DH/kg)", "XGBoost (un modèle par horizon, 1 à 8 semaines)", "Backtest sans fuite : erreur médiane 2,7 % à 1 semaine, 76 % des prévisions à ±10 %"],
];

export default function APropos() {
  return (
    <>
      <Hero titre="ℹ️ À propos de CasaHarvest" texte="Comment fonctionnent les modèles, d'où viennent les données, et quelles sont leurs limites." />
      <Section titre="Le modèle de prix expliqué simplement — exemple de la tomate" icone="bi-lightbulb" className="mb-3">
        <p className="text-secondary small">XGBoost fonctionne comme un commerçant expérimenté qui a observé 2 ans et demi de prix : il repère dans le passé des situations qui ressemblent à aujourd'hui.</p>
        <SchemaTomate />
      </Section>
      <Section titre="Les modèles" icone="bi-cpu" className="mb-3">
        <Table responsive size="sm" className="ch-table-compact mb-0">
          <thead><tr><th>Module</th><th>Ce qu'il prévoit</th><th>Modèle</th><th>Fiabilité mesurée</th></tr></thead>
          <tbody>{MODULES.map((m) => <tr key={m[0]}>{m.map((c, i) => <td key={i} className={i === 0 ? "fw-semibold text-nowrap" : ""}>{c}</td>)}</tr>)}</tbody>
        </Table>
      </Section>
      <Row className="g-3">
        <Col lg={6}>
          <Section titre="Les données" icone="bi-database">
            <ul className="mb-0">
              <li><b>Prix de gros</b> : bulletins hebdomadaires de Casablanca Prestations (marché de gros des fruits et légumes et abattoirs), collectés dans la presse marocaine en français et en arabe (31 sites), contrôlés entre les deux langues.</li>
              <li><b>Rendements</b> : statistiques officielles du HCP par province (FEWS NET), 2010-2023, regroupées en 4 zones.</li>
              <li><b>Pluie</b> : CHIRPS v2.0 (UCSB, via IRI Data Library), moyenne sur chaque zone.</li>
              <li><b>Humidité du sol, évapotranspiration, températures</b> : ERA5-Land / ERA5 (Copernicus) via Open-Meteo.</li>
              <li><b>Calendrier</b> : Ramadan et Aïd al-Adha.</li>
            </ul>
          </Section>
        </Col>
        <Col lg={6}>
          <Section titre="Limites" icone="bi-exclamation-diamond">
            <ul className="mb-0">
              <li>Prix : un seul marché (Casablanca), prix de gros et non de détail ; environ 80 semaines relevées sur 147.</li>
              <li>Récolte : seulement 14 campagnes ; rendements 2024 et 2025 non vérifiables (pas de bilan régional publié).</li>
              <li>Sécheresse : indice calibré sur 17 ans (30 ans recommandés) ; pas de prévision fiable au-delà de 2 mois.</li>
              <li>Le lien entre récolte de céréales et prix des fruits et légumes est indirect.</li>
            </ul>
          </Section>
        </Col>
      </Row>
    </>
  );
}
