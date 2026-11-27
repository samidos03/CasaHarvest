import { Container, Nav, NavDropdown, Navbar } from "react-bootstrap";
import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useEffect } from "react";
import Accueil from "./pages/Accueil";
import Prix from "./pages/Prix";
import Recolte from "./pages/Recolte";
import Secheresse from "./pages/Secheresse";
import APropos from "./pages/APropos";
import Citoyen from "./pages/Citoyen";
import Analytique from "./pages/Analytique";

export const MODULES = {
  autres: [
    ["/prix", "Prix du marché de gros", "bi-basket"],
    ["/secheresse", "Sécheresse (4 zones, version 1)", "bi-cloud-drizzle"],
    ["/recolte", "Récolte (4 zones, version 1)", "bi-flower1"],
  ],
};

function Menu({ titre, icone, liens, pathname }) {
  const actif = liens.some(([to]) => pathname.startsWith(to));
  return (
    <NavDropdown title={<><i className={`bi ${icone} me-1`} />{titre}</>} className={actif ? "ch-menu-actif" : ""}>
      {liens.map(([to, label, ic]) => (
        <NavDropdown.Item key={to} as={NavLink} to={to} eventKey={to}><i className={`bi ${ic} me-2`} />{label}</NavDropdown.Item>
      ))}
    </NavDropdown>
  );
}

export default function App() {
  const { pathname } = useLocation();
  // accolades indispensables : un effet ne doit rien renvoyer d'autre qu'une fonction de nettoyage
  // (les Chrome récents font renvoyer une promesse à window.scrollTo -> page blanche au changement de page)
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return (
    <>
      <Navbar expand="lg" className="ch-navbar sticky-top py-2" collapseOnSelect>
        <Container>
          <Navbar.Brand as={NavLink} to="/" className="d-flex align-items-center gap-2">
            <img src="/img/logo-embleme.png" alt="" width="38" height="38" />
            <span>Casa<span className="ch-brand-2">Harvest</span></span>
          </Navbar.Brand>
          <Navbar.Toggle aria-controls="menu" />
          <Navbar.Collapse id="menu">
            <Nav className="ms-auto gap-1 align-items-lg-center">
              <Nav.Link as={NavLink} to="/" end eventKey="/"><i className="bi bi-house me-1" />Accueil</Nav.Link>
              <Nav.Link as={NavLink} to="/citoyen" eventKey="/citoyen"><i className="bi bi-people me-1" />Espace citoyen</Nav.Link>
              <Nav.Link as={NavLink} to="/analytique" eventKey="/analytique"><i className="bi bi-graph-up me-1" />Espace analytique</Nav.Link>
              <Menu titre="Autres analyses" icone="bi-grid" liens={MODULES.autres} pathname={pathname} />
              <Nav.Link as={NavLink} to="/a-propos" eventKey="/a-propos"><i className="bi bi-info-circle me-1" />À propos</Nav.Link>
            </Nav>
          </Navbar.Collapse>
        </Container>
      </Navbar>
      <Container className="py-4">
        <Routes>
          <Route path="/" element={<Accueil />} />
          <Route path="/citoyen" element={<Citoyen />} />
          <Route path="/analytique" element={<Analytique />} />
          <Route path="/etudiant" element={<Navigate to="/analytique" replace />} />
          <Route path="/secheresse" element={<Secheresse />} />
          <Route path="/recolte" element={<Recolte />} />
          <Route path="/prix" element={<Prix />} />
          <Route path="/a-propos" element={<APropos />} />
          <Route path="*" element={<Accueil />} />
        </Routes>
        <footer className="mt-5 pt-4 border-top">
          <div className="d-flex flex-wrap align-items-center justify-content-between gap-3">
            <div className="d-flex align-items-center gap-2">
              <img src="/img/logo-embleme.png" alt="" width="32" height="32" />
              <div><b className="text-dark">CasaHarvest</b> · Région Casablanca-Settat · De l'eau à la récolte, de la récolte au marché.</div>
            </div>
            <div>Projet de Master IA/ML · Espace citoyen et espace analytique</div>
          </div>
          <div className="mt-2">
            Données : CHIRPS v2.0 (pluie), ERA5-Land via Open-Meteo (sol, température), HCP via FEWS NET (récoltes), ministère de
            l'Équipement et de l'Eau (barrages), geoBoundaries (limites). Autres analyses : voir « À propos ».
          </div>
        </footer>
      </Container>
    </>
  );
}
