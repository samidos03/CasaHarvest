import { Alert, Spinner } from "react-bootstrap";
import { nf } from "../api";

export function Kpi({ label, valeur, sous, icone }) {
  return (
    <div className="ch-card ch-kpi">
      <div className="lab">{icone && <i className={`bi ${icone} me-1`} />}{label}</div>
      <div className="val">{valeur}</div>
      {sous && <div className="sub">{sous}</div>}
    </div>
  );
}

export function Fleche({ v }) {
  if (v === null || v === undefined) return null;
  if (Math.abs(v) < 1) return <span className="ch-stable">● {nf(v, 1)} %</span>;
  return v > 0
    ? <span className="ch-hausse">▲ +{nf(v, 1)} %</span>
    : <span className="ch-baisse">▼ {nf(v, 1)} %</span>;
}

export function PillErreur({ err }) {
  if (err === null || err === undefined) return null;
  const [cls, txt] = err < 10 ? ["ok", "fiable"] : err < 20 ? ["mid", "moyenne"] : ["bad", "incertaine"];
  return <span className={`ch-pill ch-pill-${cls}`}>précision {txt} · ±{nf(err, 0)} %</span>;
}

export function Etat({ chargement, erreur, children, hauteur = 200 }) {
  if (erreur) return <Alert variant="danger" className="my-3"><i className="bi bi-exclamation-triangle me-2" />{erreur}</Alert>;
  if (chargement)
    return (
      <div className="d-flex align-items-center justify-content-center text-secondary" style={{ minHeight: hauteur }}>
        <Spinner animation="border" size="sm" className="me-2" /> Chargement…
      </div>
    );
  return children;
}

export function Section({ titre, icone, children, className = "" }) {
  return (
    <div className={`ch-card p-3 p-md-4 ${className}`}>
      {titre && <div className="ch-section-titre">{icone && <i className={`bi ${icone} me-2 text-primary`} />}{titre}</div>}
      {children}
    </div>
  );
}

export function Hero({ titre, texte, badges = [], variante = "" }) {
  return (
    <div className={`ch-hero mb-4 ${variante ? `ch-hero-${variante}` : ""}`}>
      <h1>{titre}</h1>
      <p>{texte}</p>
      {badges.length > 0 && (
        <div className="d-flex flex-wrap gap-2 mt-3">
          {badges.map((b) => <span key={b} className="ch-badge">{b}</span>)}
        </div>
      )}
    </div>
  );
}

/** Boutons de choix (ville, polluant, scénario…) */
export function Choix({ options, valeur, onChange }) {
  return (
    <div className="ch-choix">
      {options.map((o) => {
        const [v, l] = Array.isArray(o) ? o : [o, o];
        return <button key={v} type="button" className={v === valeur ? "actif" : ""} onClick={() => onChange(v)}>{l}</button>;
      })}
    </div>
  );
}

export function Jauge({ v, max = 100, couleur = "#0b7a43" }) {
  return <div className="ch-jauge"><div style={{ width: `${Math.max(0, Math.min(100, (v / max) * 100))}%`, background: couleur }} /></div>;
}
