import { useEffect, useState } from "react";

/** Appel GET de l'API Python ; renvoie { data, erreur, chargement }. */
export function useApi(chemin, deps = []) {
  const [etat, setEtat] = useState({ data: null, erreur: null, chargement: true });
  useEffect(() => {
    if (!chemin) return;
    let actif = true;
    setEtat((e) => ({ ...e, chargement: true }));
    fetch(`/api${chemin}`)
      .then(async (r) => {
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Erreur ${r.status}`);
        return r.json();
      })
      .then((data) => actif && setEtat({ data, erreur: null, chargement: false }))
      .catch((e) => actif && setEtat({ data: null, erreur: e.message, chargement: false }));
    return () => { actif = false; };
  }, [chemin, ...deps]);
  return etat;
}

export const ICONES = {
  Tomate: "🍅", "Pomme de terre": "🥔", "Oignon frais": "🧅", "Oignon sec": "🧅", Carotte: "🥕",
  Courgette: "🥒", Aubergine: "🍆", Concombre: "🥒", "Chou-fleur": "🥦", "Chou blanc": "🥬", Courge: "🎃",
  Orange: "🍊", Clémentine: "🍊", "Banane locale": "🍌", "Banane importée": "🍌", "Pomme locale": "🍎",
  "Pomme importée": "🍏", Avocat: "🥑", "Viande bovine": "🥩", "Viande ovine": "🍖",
};
export const COULEURS = { vert: "#0b7a43", or: "#e0a100", rouge: "#c1272d", gris: "#6b7570", grisClair: "#9aa5ad", encre: "#2f3a35" };

export const nf = (v, d = 2) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : Number(v).toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d });
export const dateFr = (s, opts = { day: "2-digit", month: "2-digit", year: "numeric" }) =>
  s ? new Date(s).toLocaleDateString("fr-FR", opts) : "—";
export const moisFr = (s) => (s ? new Date(`${s}-01`).toLocaleDateString("fr-FR", { month: "long", year: "numeric" }) : "—");
