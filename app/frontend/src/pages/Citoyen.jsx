import { useState } from "react";
import { Col, Row } from "react-bootstrap";
import { Link, useSearchParams } from "react-router-dom";
import { useApi } from "../api";
import { Etat } from "../components/Ui";
import CarteRegion, { NOMS_AR } from "../components/CarteRegion";

const PROVINCES = ["Casablanca", "Mohammedia", "Settat", "Berrechid", "El Jadida", "Sidi Bennour", "Benslimane", "Nouaceur", "Médiouna"];
const MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
const MOIS_AR = ["يناير", "فبراير", "مارس", "أبريل", "ماي", "يونيو", "يوليوز", "غشت", "شتنبر", "أكتوبر", "نونبر", "دجنبر"];
const VERT = "#1a9850", JAUNE = "#e0a100", ORANGE = "#e07b00", ROUGE = "#c1272d", BLEU = "#1d6fa5";

/* Textes : français / arabe. Phrases courtes, sans jargon. */
const T = {
  fr: {
    titre: "Ma province en un coup d'œil", sous: "Pluie, sol, récolte et eau des barrages — expliqués simplement.",
    choisir: "Choisissez votre province (touchez la carte ou un nom)", prefecture: "Préfecture", province: "Province",
    pluie: "Pluie", sol: "Sol", recolte: "Récolte de céréales", eau: "Eau des barrages",
    saison: "Saison 2025-2026 (septembre à août)", fois: (x) => `soit ${x} fois la quantité habituelle`,
    pluieNiv: { tres: "Très pluvieuse", normal: "Normale", peu: "Un peu sèche", sec: "Sèche" },
    pluieMm: (mm, n) => `${mm} mm de pluie, pour ${n} mm habituellement`,
    hiver: (mm) => `Cet hiver (décembre à février), il tombe en moyenne ${mm} mm.`,
    imprevisible: "Personne ne peut prévoir de façon fiable la pluie de plusieurs mois : nous montrons donc ce qui est habituel.",
    annees: "Les 6 dernières saisons", normale: "habituel",
    solNiv: { humide: "Humide", normal: "Normal", sec: "Sec" },
    solPour: (m) => `pour un mois de ${m}`, solPrev: (m, c) => `Prévision pour ${m} : sol ${c.toLowerCase()}`,
    solExpl: "Un sol humide aide le blé et l'orge à bien pousser.",
    recNiv: { bonne: "Bonne récolte", moyenne: "Récolte moyenne", faible: "Récolte faible", mauvaise: "Mauvaise récolte" },
    rec2026: "Récolte 2026 (estimation)", recPct: (x) => `${x} % d'une année habituelle`,
    recTonnes: (t) => `≈ ${t} tonnes de blé et d'orge`,
    rec2027: "Et en 2027 ? Tout dépendra de la pluie de l'hiver :", scen: { seche: "Hiver sec", normale: "Hiver moyen", pluie: "Hiver pluvieux" },
    qx: "quintaux par hectare", habituel: (x) => `Une année habituelle : ${x} quintaux par hectare.`, risqueRec: (p) => `Risque de mauvaise récolte en 2027 : ${p} %`,
    massira: "Barrage Al Massira (province de Settat)", rempli: "rempli",
    annees_casa: (x) => `Il contient environ ${x} années d'eau potable de Casablanca.`,
    dans3mois: (a, b) => `Dans 3 mois : entre ${a} % et ${b} %`,
    risque: "Risque de pénurie d'eau", risqueNiv: { faible: "Faible", moyen: "Moyen", "élevé": "Élevé" },
    sert: "Al Massira alimente en eau potable El Jadida, Sidi Bennour, Settat, Berrechid et le sud de Casablanca.",
    unAn: (x) => `Il y a un an : ${x} %`, releve: (d) => `Relevé officiel du ${d}`,
    comprendre: "Comment lire ces résultats ?",
    c1: "Vert = situation bonne, orange = à surveiller, rouge = difficile.",
    c2: "« Habituel » = moyenne des saisons 2010 à 2025.",
    c3: "Les chiffres viennent de mesures par satellite (pluie, sol), des statistiques officielles (récoltes) et du ministère de l'Équipement et de l'Eau (barrages).",
    etudiant: "Voir les détails, les graphiques et les modèles dans l'Espace étudiant",
    langue: "العربية",
  },
  ar: {
    titre: "إقليمي في لمحة", sous: "الأمطار، التربة، المحصول وماء السدود — بشرح بسيط.",
    choisir: "اختر إقليمك (المس الخريطة أو الاسم)", prefecture: "عمالة", province: "إقليم",
    pluie: "الأمطار", sol: "التربة", recolte: "محصول الحبوب", eau: "ماء السدود",
    saison: "موسم 2025-2026 (من شتنبر إلى غشت)", fois: (x) => `أي ${x} مرة الكمية المعتادة`,
    pluieNiv: { tres: "ممطر جدا", normal: "عادي", peu: "جاف قليلا", sec: "جاف" },
    pluieMm: (mm, n) => `${mm} ملم من الأمطار، مقابل ${n} ملم عادة`,
    hiver: (mm) => `في هذا الشتاء (من دجنبر إلى فبراير) تسقط في المتوسط ${mm} ملم.`,
    imprevisible: "لا يمكن توقع الأمطار بدقة لعدة أشهر، لذلك نعرض ما هو معتاد.",
    annees: "آخر 6 مواسم", normale: "المعتاد",
    solNiv: { humide: "رطبة", normal: "عادية", sec: "جافة" },
    solPour: (m) => `بالنسبة لشهر ${m}`, solPrev: (m, c) => `توقع شهر ${m}: تربة ${c}`,
    solExpl: "التربة الرطبة تساعد القمح والشعير على النمو الجيد.",
    recNiv: { bonne: "محصول جيد", moyenne: "محصول متوسط", faible: "محصول ضعيف", mauvaise: "محصول سيء" },
    rec2026: "محصول 2026 (تقدير)", recPct: (x) => `${x}٪ من سنة عادية`,
    recTonnes: (t) => `حوالي ${t} طن من القمح والشعير`,
    rec2027: "وفي 2027؟ كل شيء يتوقف على أمطار الشتاء:", scen: { seche: "شتاء جاف", normale: "شتاء متوسط", pluie: "شتاء ممطر" },
    qx: "قنطار في الهكتار", habituel: (x) => `في سنة عادية: ${x} قنطار في الهكتار.`, risqueRec: (p) => `خطر محصول سيء في 2027: ${p}٪`,
    massira: "سد المسيرة (إقليم سطات)", rempli: "نسبة الملء",
    annees_casa: (x) => `يحتوي على حوالي ${x} سنوات من الماء الشروب للدار البيضاء.`,
    dans3mois: (a, b) => `بعد 3 أشهر: بين ${a}٪ و ${b}٪`,
    risque: "خطر نقص الماء", risqueNiv: { faible: "ضعيف", moyen: "متوسط", "élevé": "مرتفع" },
    sert: "يزود سد المسيرة بالماء الشروب الجديدة وسيدي بنور وسطات وبرشيد وجنوب الدار البيضاء.",
    unAn: (x) => `قبل سنة: ${x}٪`, releve: (d) => `قياس رسمي بتاريخ ${d}`,
    comprendre: "كيف تقرأ هذه النتائج؟",
    c1: "الأخضر = وضع جيد، البرتقالي = يحتاج إلى متابعة، الأحمر = وضع صعب.",
    c2: "«المعتاد» = متوسط مواسم 2010 إلى 2025.",
    c3: "الأرقام مصدرها قياسات الأقمار الاصطناعية (الأمطار، التربة)، والإحصاءات الرسمية (المحاصيل)، ووزارة التجهيز والماء (السدود).",
    etudiant: "التفاصيل والرسوم البيانية والنماذج في فضاء الطالب",
    langue: "Français",
  },
};

const nfx = (v, d, ar) => (v == null ? "—" : Number(v).toLocaleString(ar ? "ar-MA" : "fr-FR", { maximumFractionDigits: d, minimumFractionDigits: d }));
const niveauPluie = (p) => (p >= 120 ? ["tres", BLEU] : p >= 90 ? ["normal", VERT] : p >= 70 ? ["peu", ORANGE] : ["sec", ROUGE]);
const niveauRec = (r) => (r >= 110 ? ["bonne", VERT] : r >= 90 ? ["moyenne", JAUNE] : r >= 70 ? ["faible", ORANGE] : ["mauvaise", ROUGE]);
const couleurSol = { humide: BLEU, normal: VERT, sec: ORANGE };
const couleurRisque = { faible: VERT, moyen: ORANGE, "élevé": ROUGE };

function Carte({ icone, titre, couleur, statut, children }) {
  return (
    <div className="ch-citoyen-carte h-100" style={{ borderTopColor: couleur }}>
      <div className="d-flex align-items-center gap-2 mb-2">
        <span className="ch-citoyen-icone">{icone}</span>
        <span className="fw-bold text-secondary text-uppercase small">{titre}</span>
      </div>
      <div className="ch-citoyen-statut" style={{ color: couleur }}>{statut}</div>
      {children}
    </div>
  );
}

function Fiche({ province, t, ar }) {
  const { data: d, erreur, chargement } = useApi(`/region/citoyen?province=${encodeURIComponent(province)}`);
  if (!d) return <Etat chargement={chargement} erreur={erreur} hauteur={420} />;
  const MOIS = ar ? MOIS_AR : MOIS_FR;
  const [np, cp] = niveauPluie(d.pluie.pct);
  const ratioRec = d.recolte.ratio;
  const [nr, cr] = niveauRec(ratioRec);
  const solMois = MOIS[+d.sol.mois.slice(5) - 1];
  const sp = d.sol.prevision[0];
  const solPrevClasse = sp ? (sp.percentile < 33 ? "sec" : sp.percentile > 67 ? "humide" : "normal") : null;
  const p90 = d.eau.prevision.find((x) => x.horizon_jours === 90);
  const sc = d.recolte.scenarios_2027;
  const moy = (k) => sc.reduce((a, r) => a + r[k], 0) / Math.max(1, sc.length);
  const risque27 = moy("proba_mauvaise_pct");
  const dernieres = d.pluie.par_saison.slice(-6);
  const releve = new Date(d.eau.date).toLocaleDateString(ar ? "ar-MA" : "fr-FR", { day: "numeric", month: "long", year: "numeric" });
  return (
    <Row className="g-3">
      <Col md={6}>
        <Carte icone="🌧️" titre={t.pluie} couleur={cp} statut={t.pluieNiv[np]}>
          <div className="small text-secondary mb-1">{t.saison}</div>
          <div className="ch-citoyen-chiffre">{t.pluieMm(nfx(d.pluie.total_mm, 0, ar), nfx(d.pluie.normale_mm, 0, ar))}</div>
          <div className="fw-semibold" style={{ color: cp }}>{t.fois(nfx(d.pluie.pct / 100, 1, ar))}</div>
          <div className="small text-secondary mt-3 mb-1">{t.annees}</div>
          <div className="ch-mini-barres">
            {dernieres.map((s) => {
              const [, c] = niveauPluie(s.pct);
              return (
                <div key={s.saison} title={`${s.saison - 1}-${s.saison} : ${Math.round(s.pct)} %`}>
                  <div className="barre" style={{ height: `${Math.min(100, s.pct / 1.8)}%`, background: c }} />
                  <span>{String(s.saison).slice(2)}</span>
                </div>
              );
            })}
            <div className="ligne-normale" style={{ bottom: `${100 / 1.8}%` }}><span>{t.normale}</span></div>
          </div>
          <div className="mt-3">{t.hiver(nfx(d.pluie.hiver_normale_mm, 0, ar))}</div>
          <div className="small text-secondary">{t.imprevisible}</div>
        </Carte>
      </Col>
      <Col md={6}>
        <Carte icone="🌱" titre={t.sol} couleur={couleurSol[d.sol.classe]} statut={t.solNiv[d.sol.classe]}>
          <div className="text-secondary">{t.solPour(solMois)}</div>
          <div className="ch-thermo mt-3 mb-1">
            <div className="zone sec" /><div className="zone normal" /><div className="zone humide" />
            <div className="curseur" style={{ [ar ? "right" : "left"]: `${d.sol.percentile}%` }} />
          </div>
          <div className="d-flex justify-content-between small text-secondary"><span>{t.solNiv.sec}</span><span>{t.solNiv.normal}</span><span>{t.solNiv.humide}</span></div>
          {sp && <div className="mt-3 fw-semibold" style={{ color: couleurSol[solPrevClasse] }}>{t.solPrev(MOIS[+sp.mois.slice(5) - 1], t.solNiv[solPrevClasse])}</div>}
          <div className="small text-secondary mt-2">{t.solExpl}</div>
        </Carte>
      </Col>
      <Col md={6}>
        <Carte icone="🌾" titre={t.recolte} couleur={cr} statut={t.recNiv[nr]}>
          <div className="small text-secondary mb-1">{t.rec2026}</div>
          <div className="ch-citoyen-chiffre">{t.recPct(nfx(ratioRec, 0, ar))}</div>
          <div className="text-secondary">{t.recTonnes(nfx(Math.round(d.recolte.production_t / 1000) * 1000, 0, ar))}</div>
          <div className="mt-3 fw-semibold">{t.rec2027}</div>
          <div className="d-flex flex-wrap gap-2 mt-2">
            {[["seche", "annee_seche", ORANGE], ["normale", "annee_normale", JAUNE], ["pluie", "annee_pluvieuse", VERT]].map(([k, col, c]) => (
              <div key={k} className="ch-scenario" style={{ borderColor: c }}>
                <div className="small">{t.scen[k]}</div>
                <b style={{ color: c }}>{nfx(moy(col), 0, ar)}</b> <span className="small text-secondary">{t.qx}</span>
              </div>
            ))}
          </div>
          <div className="small mt-2 text-secondary">{t.habituel(nfx(moy("moyenne_qx_ha"), 0, ar))}</div>
          <div className="small" style={{ color: risque27 > 30 ? ORANGE : "inherit" }}>{t.risqueRec(nfx(risque27, 0, ar))}</div>
        </Carte>
      </Col>
      <Col md={6}>
        <Carte icone="💧" titre={t.eau} couleur={couleurRisque[d.eau.risque]} statut={`${t.risque} : ${t.risqueNiv[d.eau.risque]}`}>
          <div className="d-flex gap-3 align-items-center mt-1">
            <div className="ch-reservoir"><div className="eau" style={{ height: `${d.eau.taux_pct}%` }} /><b>{nfx(d.eau.taux_pct, 0, ar)} %</b></div>
            <div>
              <div className="fw-semibold">{t.massira}</div>
              <div className="ch-citoyen-chiffre">{nfx(d.eau.taux_pct, 1, ar)} % {t.rempli}</div>
              <div className="small text-secondary">{t.releve(releve)}</div>
              {p90 && <div className="mt-2 fw-semibold">{t.dans3mois(nfx(p90.bas_pct, 0, ar), nfx(p90.haut_pct, 0, ar))}</div>}
            </div>
          </div>
          <div className="mt-3">{t.annees_casa(nfx(d.eau.annees_conso_casa, 0, ar))}</div>
          <div className="small text-secondary mt-1">{t.sert}</div>
        </Carte>
      </Col>
    </Row>
  );
}

export default function Citoyen() {
  const [params, setParams] = useSearchParams();
  const langue = params.get("langue") === "ar" ? "ar" : "fr";
  const setLangue = (l) => setParams(l === "ar" ? { langue: "ar" } : {}, { replace: true });
  const [province, setProvince] = useState("Settat");
  const ar = langue === "ar";
  const t = T[langue];
  const provs = useApi("/region/provinces");
  const couleurs = {};
  (provs.data || []).forEach((p) => { couleurs[p.province] = niveauPluie(p.pluie_2026_pct)[1] + "55"; });
  couleurs[province] = (couleurs[province] || "#cfe8da").slice(0, 7) + "cc";
  const info = provs.data?.find((p) => p.province === province);
  return (
    <div dir={ar ? "rtl" : "ltr"} className={ar ? "ch-arabe" : ""}>
      <div className="ch-citoyen-entete mb-3">
        <div>
          <h1 className="m-0">👨‍👩‍👧 {t.titre}</h1>
          <div className="opacity-75 mt-1">{t.sous}</div>
        </div>
        <button type="button" className="btn btn-light fw-bold" onClick={() => setLangue(ar ? "fr" : "ar")}>
          <i className="bi bi-translate mx-1" />{t.langue}
        </button>
      </div>
      <Row className="g-3 mb-3 align-items-stretch">
        <Col lg={5}>
          <div className="ch-card p-3 h-100">
            <div className="fw-semibold mb-2">{t.choisir}</div>
            <CarteRegion couleurs={couleurs} choix={province} onChoix={setProvince} hauteur={300} arabe={ar} />
          </div>
        </Col>
        <Col lg={7}>
          <div className="ch-card p-3 h-100">
            <div className="ch-choix-grand">
              {PROVINCES.map((p) => (
                <button key={p} type="button" className={p === province ? "actif" : ""} onClick={() => setProvince(p)}>{ar ? NOMS_AR[p] : p}</button>
              ))}
            </div>
            {info && (
              <div className="mt-3 p-3 rounded-3" style={{ background: "#f3f7f2" }}>
                <div className="fs-3 fw-bold">{ar ? info.nom_ar : province}</div>
                <div className="text-secondary">{info.type === "Préfecture" ? t.prefecture : t.province} · {nfx(info.surface_km2, 0, ar)} km²</div>
              </div>
            )}
            <div className="small text-secondary mt-3">
              <div>🟢 {t.c1}</div><div>📅 {t.c2}</div>
            </div>
          </div>
        </Col>
      </Row>
      <Fiche province={province} t={t} ar={ar} />
      <div className="ch-card p-3 mt-3">
        <div className="fw-bold mb-1">{t.comprendre}</div>
        <div className="small">{t.c1} {t.c2}</div>
        <div className="small text-secondary">{t.c3}</div>
        <Link to="/etudiant" className="btn btn-outline-success btn-sm mt-2"><i className="bi bi-mortarboard mx-1" />{t.etudiant}</Link>
      </div>
    </div>
  );
}
