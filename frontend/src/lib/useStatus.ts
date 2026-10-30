/** The backend's current configuration — model, region, what's connected.
 *  Cached for the lifetime of the page; it only changes when .env does. */

import { api, type Status } from "./api";
import { useAsync } from "./useAsync";

let cached: Status | null = null;

export function useStatus() {
  const state = useAsync<Status>(async () => {
    if (cached) return cached;
    cached = await api.status();
    return cached;
  }, []);
  return state.data;
}

export const REGION_NAMES: Record<string, string> = {
  AU: "Australia",
  NZ: "New Zealand",
  UK: "the UK",
  US: "the US",
};
