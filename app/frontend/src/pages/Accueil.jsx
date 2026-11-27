import { Col, Row } from "react-bootstrap";
import { Link } from "react-router-dom";
import { nf, useApi } from "../api";
import CarteRegion from "../components/CarteRegion";

const couleurPluie = (p) => (p == null ? "#e9ede7" : p >= 130 ? "#2166ac" : p >= 110 ? "#67a9cf" : p >= 90 ? "#a6d96a" : p >= 70 ? "#fdae61" : "#d7301f");

function Theme({ to, icone, titre, texte, couleur, fond }) {
  return (
    <Link to={to} className="ch-card ch-module p-3 h-100 d-block">
      <div className="d-flex align-items-center gap-3">
        <div className="icone" style={{ background: fond, color: couleur, fontSize: "1.5rem" }}>{icone}</div>
        <div>
          <div className="fw-bold">{titre}</div>
          <div className="small text-secondary">{texte}</div>
        </div>
      </div>
    </Link>
  );
}

export default function Accueil() {
  const provs = useApi("/region/provinces");
  const eau = useApi("/region/citoyen?province=Settat");
  const p = provs.data || [];
  const moyPluie = p.length ? p.reduce((a, x) => a + x.pluie_2026_pct * x.surface_km2, 0) / p.reduce((a, x) => a + x.surface_km2, 0) : null;
  return (
    <>
      <section className="ch-couverture mb-4">
        <div className="contenu">
          <img src="/img/logo-embleme.png" alt="Logo CasaHarvest" className="embleme" />
          <h1>CasaHarvest</h1>
          <div className="slogan">De l'eau à la récolte, de la récolte au marché.</div>
          <p className="intro">
            La pluie, l'humidité du sol, les récoltes de céréales et l'eau des barrages dans la <b>région Casablanca-Settat</b> :
            9 préfectures et provinces, des données satellites et officielles depuis 2009, et des prévisions par apprentissage automatique.
          </p>
          <div className="d-flex flex-wrap gap-2 mt-3">
            <Link to="/citoyen" className="btn btn-light btn-lg px-4"><i className="bi bi-people me-2" />Espace citoyen</Link>
            <Link to="/etudiant" className="btn btn-outline-light btn-lg px-4"><i className="bi bi-mortarboard me-2" />Espace étudiant</Link>
          </div>
          <div className="ch-chiffres">
            <div><b>9</b><span>préfectures et provinces</span></div>
            <div><b>{moyPluie ? `${nf(moyPluie, 0)} %` : "…"}</b><span>de la pluie normale en 2025-26</span></div>
            <div><b>{eau.data ? `${nf(eau.data.eau.taux_pct, 0)} %` : "…"}</b><span>barrage Al Massira</span></div>
            <div><b>17 ans</b><span>de données (2009-2026)</span></div>
          </div>
        </div>
      </section>

      <div className="ch-portes mb-4">
        <Link to="/citoyen" className="ch-porte citoyen">
          <div className="gros">👨‍👩‍👧</div>
          <h2>Espace citoyen</h2>
          <div>Choisissez votre province : pluie, sol, récolte et eau des barrages, expliqués en une phrase avec un code couleur. En français et en arabe.</div>
          <div className="mt-3 fw-bold">Ouvrir <i className="bi bi-arrow-right" /></div>
        </Link>
        <Link to="/etudiant" className="ch-porte etudiant">
          <div className="gros">🎓</div>
          <h2>Espace étudiant</h2>
          <div>Graphiques interactifs, cartes, statistiques, modèles comparés (Ridge, forêt aléatoire, XGBoost) et prévisions avec leurs marges d'erreur.</div>
          <div className="mt-3 fw-bold">Ouvrir <i className="bi bi-arrow-right" /></div>
        </Link>
      </div>

      <Row className="g-3 align-items-stretch">
        <Col lg={6}>
          <div className="ch-card p-3 h-100">
            <div className="ch-section-titre"><i className="bi bi-map me-2 text-primary" />La région Casablanca-Settat</div>
            <CarteRegion hauteur={330}
              couleurs={Object.fromEntries(p.map((x) => [x.province, couleurPluie(x.pluie_2026_pct)]))}
              etiquettes={Object.fromEntries(p.map((x) => [x.province, `${nf(x.pluie_2026_pct, 0)} %`]))}
              legende={[["#d7301f", "< 70 %"], ["#fdae61", "70-90"], ["#a6d96a", "90-110"], ["#67a9cf", "110-130"], ["#2166ac", "> 130 % de la pluie normale (2025-26)"]]} />
            <div className="small text-secondary mt-2">Chef-lieu : Casablanca. Préfectures : Casablanca, Mohammedia. Provinces : Settat, El Jadida, Sidi Bennour, Berrechid, Benslimane, Nouaceur, Médiouna.</div>
          </div>
        </Col>
        <Col lg={6}>
          <div className="d-grid gap-3 h-100">
            <Theme to="/etudiant?onglet=pluie" icone="🌧️" titre="Précipitations (CHIRPS 2009-2026)" couleur="#1d6fa5" fond="#e3f0f9"
              texte="Pluie de chaque province, saison par saison, et indice de sécheresse SPI." />
            <Theme to="/etudiant?onglet=sol" icone="🌱" titre="Humidité du sol (ERA5-Land)" couleur="#0b7a43" fond="#e7f3ec"
              texte="Le sol est-il sec ou humide ? Prévision à 1 et 2 mois." />
            <Theme to="/etudiant?onglet=recolte" icone="🌾" titre="Récoltes de céréales" couleur="#b0721a" fond="#fbf1e0"
              texte="Rendement du blé et de l'orge par province, zones à risque, scénarios 2027." />
            <Theme to="/etudiant?onglet=barrage" icone="💧" titre="Barrages et risque de pénurie" couleur="#3f7280" fond="#e4f0f2"
              texte="Barrage Al Massira : niveau dans 7, 30 et 90 jours." />
          </div>
        </Col>
      </Row>
      <div className="ch-card p-3 mt-4">
        <div className="small text-secondary mb-2">Autres analyses CasaHarvest</div>
        <div className="d-flex flex-wrap gap-2">
          <Link className="btn btn-sm btn-outline-secondary" to="/prix">🧺 Prix du marché de gros de Casablanca</Link>
          <Link className="btn btn-sm btn-outline-secondary" to="/tourisme">🧳 Tourisme</Link>
          <Link className="btn btn-sm btn-outline-secondary" to="/dechets">🗑️ Déchets ménagers</Link>
          <Link className="btn btn-sm btn-outline-secondary" to="/air">🌬️ Qualité de l'air</Link>
        </div>
      </div>
    </>
  );
}
