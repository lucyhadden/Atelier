/** The domain (interiors or wardrobe) lives in the URL, like every other filter. */

import { useSearchParams } from "react-router-dom";

import type { Domain } from "./api";

export const DOMAINS: { key: Domain; label: string }[] = [
  { key: "interior", label: "Interiors" },
  { key: "wardrobe", label: "Wardrobe" },
];

export function useDomain(): [Domain, (next: Domain) => void] {
  const [params, setParams] = useSearchParams();
  const raw = params.get("domain");
  const domain: Domain = raw === "wardrobe" ? "wardrobe" : "interior";

  const set = (next: Domain) => {
    const updated = new URLSearchParams(params);
    updated.set("domain", next);
    setParams(updated, { replace: true });
  };
  return [domain, set];
}
