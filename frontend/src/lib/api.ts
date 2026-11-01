/** Typed client for the Atelier API. Vite proxies /api to the backend. */

export type Domain = "interior" | "wardrobe";
export type Tier = "splurge" | "mid" | "budget" | "secondhand";

export const TIER_ORDER: Tier[] = ["splurge", "mid", "budget", "secondhand"];
export const TIER_LABEL: Record<Tier, string> = {
  splurge: "Splurge",
  mid: "Middle",
  budget: "Budget",
  secondhand: "Secondhand",
};

export type Ships = "local" | "overseas" | "unknown";

export interface Source {
  id: number;
  tier: Tier;
  retailer: string;
  url: string;
  kind: "search" | "product";
  product_name: string | null;
  price: string | null;
  note: string | null;
  ships: Ships;
  region: string | null;
}

export interface Item {
  id: number;
  pin_id: number;
  pin_image_file: string;
  board_id: number;
  domain: Domain;
  category: string;
  name: string;
  description: string;
  attributes: Record<string, string>;
  search_terms: string[];
  est_tier: string | null;
  confidence: number;
  bbox: number[] | null;
  is_hero: boolean;
  sources: Source[];
}

export interface Pin {
  id: number;
  board_id: number;
  title: string | null;
  note: string | null;
  link: string | null;
  image_file: string;
  scene_summary: string | null;
  analyzed_at: string | null;
  items: Item[];
}

export interface Board {
  id: number;
  name: string;
  domain: Domain;
  source: "pinterest" | "local";
  external_id: string | null;
  description: string | null;
  synced_at: string | null;
  pin_count: number;
  analyzed_count: number;
  item_count: number;
}

export interface StyleProfile {
  id: number;
  board_id: number;
  domain: Domain;
  summary: string;
  palette: { name: string; hex: string; role: string }[];
  materials: string[];
  keywords: string[];
  axes: Record<string, string>;
  tensions: string[];
  pin_count: number;
  created_at: string;
}

export interface FloorPlan {
  id: number;
  space_id: number;
  image_file: string;
  kind: "floorplan" | "photo";
  label: string | null;
  analysis: {
    summary: string;
    rooms: { name?: string; approx_dimensions?: string; notes?: string }[];
    fixed_features: string[];
    circulation: string[];
    opportunities: string[];
    constraints: string[];
    scale_confidence: string;
  } | null;
  analyzed_at: string | null;
}

export interface Space {
  id: number;
  name: string;
  domain: Domain;
  kind: string | null;
  notes: string | null;
  plans: FloorPlan[];
}

export interface DesignPlan {
  id: number;
  space_id: number;
  board_id: number | null;
  title: string;
  narrative: string;
  zones: { zone: string; intent: string; pieces: string[]; notes: string }[];
  shopping_list: {
    category: string;
    what: string;
    why: string;
    priority: string;
    budget_band: string;
  }[];
  cautions: string[];
  created_at: string;
}

export interface Status {
  claude_configured: boolean;
  model: string;
  effort: string;
  region: string;
  include_international: boolean;
  web_search_enabled: boolean;
  pinterest_configured: boolean;
  pinterest_connected: boolean;
  board_count: number;
  item_count: number;
}

export interface PinterestAccount {
  username: string | null;
  account_type: string | null;
  pin_count: number | null;
  board_count: number | null;
}

export interface PinterestStatus {
  configured: boolean;
  connected: boolean;
  redirect_uri: string;
  scopes: string[];
  account: PinterestAccount | null;
  account_error?: string;
}

export interface SyncReport {
  board_id: number;
  board_name: string;
  remote_pins: number;
  added: number;
  already_had: number;
  failed: { pin: string; error: string }[];
  sections: string[];
  skipped_no_image: number;
  truncated: boolean;
  gone_from_pinterest: number;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      headers: init?.body instanceof FormData ? {} : { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError("Could not reach the Atelier backend. Is it running on port 8787?", 0);
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* a non-JSON error body is not worth surfacing */
    }
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  status: () => request<Status>("/status"),

  boards: (domain?: Domain) => request<Board[]>(`/boards${domain ? `?domain=${domain}` : ""}`),
  board: (id: number) => request<Board>(`/boards/${id}`),
  deleteBoard: (id: number) => request<unknown>(`/boards/${id}`, { method: "DELETE" }),
  pins: (boardId: number) => request<Pin[]>(`/boards/${boardId}/pins`),
  importFolder: (payload: {
    path: string;
    domain: Domain;
    board_name?: string;
    is_pinterest_export?: boolean;
  }) => post<{ board_id?: number; added?: number; total_added?: number }>(
    "/boards/import-folder",
    payload,
  ),
  analyzeBoard: (id: number, force = false) =>
    post<{ analyzed: number; skipped: number; failed: { pin_id: number; error: string }[] }>(
      `/boards/${id}/analyze?force=${force}`,
    ),
  analyzePin: (boardId: number, pinId: number) =>
    post<Pin>(`/boards/${boardId}/pins/${pinId}/analyze`),
  readStyle: (id: number) => post<StyleProfile>(`/boards/${id}/style`),
  latestStyle: (id: number) => request<StyleProfile | null>(`/boards/${id}/style`),

  items: (params: { domain?: Domain; board_id?: number; hero_only?: boolean } = {}) => {
    const q = new URLSearchParams();
    if (params.domain) q.set("domain", params.domain);
    if (params.board_id !== undefined) q.set("board_id", String(params.board_id));
    if (params.hero_only) q.set("hero_only", "true");
    return request<Item[]>(`/items?${q}`);
  },
  item: (id: number) => request<Item>(`/items/${id}`),
  searchLinks: (id: number) =>
    request<{ sources: Omit<Source, "id">[] }>(`/items/${id}/search-links`),
  sourceItem: (id: number, useWebSearch?: boolean) =>
    post<Item>(`/items/${id}/source`, { use_web_search: useWebSearch ?? null, region: null }),

  spaces: (domain?: Domain) => request<Space[]>(`/spaces${domain ? `?domain=${domain}` : ""}`),
  space: (id: number) => request<Space>(`/spaces/${id}`),
  createSpace: (payload: { name: string; domain: Domain; kind?: string; notes?: string }) =>
    post<Space>("/spaces", payload),
  deleteSpace: (id: number) => request<unknown>(`/spaces/${id}`, { method: "DELETE" }),
  uploadPlan: (spaceId: number, file: File, kind: string, label: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("kind", kind);
    if (label) form.append("label", label);
    return request<FloorPlan>(`/spaces/${spaceId}/plans`, { method: "POST", body: form });
  },
  analyzePlan: (spaceId: number, planId: number) =>
    post<FloorPlan>(`/spaces/${spaceId}/plans/${planId}/analyze`),
  buildDesign: (spaceId: number, payload: { board_id: number | null; brief: string }) =>
    post<DesignPlan>(`/spaces/${spaceId}/design`, payload),
  designs: (spaceId: number) => request<DesignPlan[]>(`/spaces/${spaceId}/designs`),

  pinterestStatus: () =>
    request<PinterestStatus>("/pinterest/status"),
  pinterestBoards: () =>
    request<{
      boards: {
        external_id: string;
        name: string;
        pin_count: number;
        privacy: string | null;
      }[];
    }>("/pinterest/boards"),
  pinterestSync: (payload: { external_id: string; domain: Domain; name?: string }) =>
    post<SyncReport>("/pinterest/sync", payload),
  pinterestDisconnect: () => post<unknown>("/pinterest/disconnect"),
};

export const imageUrl = (file: string) => `/images/${file}`;

/** "ribbed opal glass" -> "Ribbed opal glass" without shouting. */
export const sentence = (text: string) =>
  text.length ? text[0].toUpperCase() + text.slice(1) : text;

export const categoryLabel = (category: string) =>
  sentence(category.replace(/-/g, " "));
