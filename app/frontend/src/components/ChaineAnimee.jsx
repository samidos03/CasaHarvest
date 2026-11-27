/**
 * Animation de l'accueil : Haj Mustapha (agriculteur, Settat) et Allaoui (chauffeur de taxi, Casablanca)
 * reliés par la même chaîne. En haut, les produits circulent du champ au marché (eau → récolte → marché) ;
 * en bas, le prix payé revient vers l'agriculteur.
 */
const PRODUITS = ["💧", "🌾", "🍅", "🥔", "🧅"];
const STATIONS = [
  { pos: 18, icone: "💧", label: "L'eau" },
  { pos: 50, icone: "🌾", label: "La récolte" },
  { pos: 82, icone: "🧺", label: "Le marché" },
];

function Personnage({ emoji, nom, role, ar, fr, cote }) {
  return (
    <div className={`ch-perso ch-perso-${cote}`}>
      <div className="ch-bulle" dir="rtl" lang="ar">{ar}</div>
      <div className="ch-bulle-fr">« {fr} »</div>
      <div className="ch-avatar" aria-hidden="true">{emoji}</div>
      <div className="fw-bold mt-2">{nom}</div>
      <div className="small text-secondary">{role}</div>
    </div>
  );
}

export default function ChaineAnimee() {
  return (
    <div className="ch-card ch-chaine p-3 p-md-4">
      <div className="ch-chaine-grille">
        <Personnage cote="g" emoji="👨‍🌾" nom="Haj Mustapha" role="Agriculteur à Settat"
          ar="أنا دابا عارف شنو نزرع وفوقاش نسقي باش نحسن الإنتاج ديالي"
          fr="Je sais maintenant quoi semer et quand irriguer pour améliorer ma production." />

        <div className="ch-piste-zone" aria-label="Les produits vont du champ au marché, le prix revient vers l'agriculteur">
          <div className="ch-voie-titre"><i className="bi bi-arrow-right me-1" />les produits</div>
          <div className="ch-piste">
            <div className="ch-piste-ligne" />
            {STATIONS.map((s) => (
              <div key={s.label} className="ch-station" style={{ left: `${s.pos}%` }}>
                <div className="ch-station-rond">{s.icone}</div>
                <div className="ch-station-label">{s.label}</div>
              </div>
            ))}
            {PRODUITS.map((p, i) => (
              <span key={p} className="ch-jeton" style={{ animationDelay: `${i * 1.6}s` }} aria-hidden="true">{p}</span>
            ))}
          </div>
          <div className="ch-piste ch-piste-retour">
            <div className="ch-piste-ligne ch-piste-ligne-retour" />
            {[0, 1, 2].map((i) => (
              <span key={i} className="ch-jeton ch-jeton-retour" style={{ animationDelay: `${i * 2.7 + 0.8}s` }} aria-hidden="true">🪙</span>
            ))}
          </div>
          <div className="ch-voie-titre ch-voie-titre-retour">le prix payé<i className="bi bi-arrow-left ms-1" /></div>
        </div>

        <Personnage cote="d" emoji="🚕" nom="Allaoui" role="Chauffeur de taxi à Casablanca"
          ar="وكيفاش كيأثر السوق على المعيشة اليومية"
          fr="Et comment le marché influence-t-il ma vie de tous les jours ?" />
      </div>
      <p className="text-center mb-0 mt-3 fw-semibold" dir="rtl" lang="ar">
        واحد كيزرع، وواحد كيشري… ولكن بجوج مرتبطين بنفس السلسلة.
      </p>
      <p className="text-center mb-0 text-secondary small mt-1">
        L'un sème, l'autre achète… mais tous deux sont reliés par la même chaîne.
      </p>
    </div>
  );
}
