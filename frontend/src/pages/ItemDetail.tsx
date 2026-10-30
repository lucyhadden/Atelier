import { useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { Banner, ErrorState, LoadingLines } from "../components/States";
import {
  api,
  categoryLabel,
  imageUrl,
  sentence,
  TIER_LABEL,
  TIER_ORDER,
  type Item,
  type Source,
  type Tier,
} from "../lib/api";
import { REGION_NAMES, useStatus } from "../lib/useStatus";
import { useAsync } from "../lib/useAsync";

/** Local options first, then overseas ones. Within each, found products before
 *  bare search links. Nothing is hidden - the order carries the preference. */
function orderSources(sources: Source[]): Source[] {
  const rank = (s: Source) =>
    (s.ships === "overseas" ? 2 : 0) + (s.kind === "product" ? 0 : 1);
  return [...sources].sort((a, b) => rank(a) - rank(b));
}

function ShipsTag({ source }: { source: Source }) {
  if (source.ships === "overseas") {
    return (
      <span className="ships ships--overseas">
        ships from {source.region ?? "overseas"}
      </span>
    );
  }
  if (source.ships === "unknown") {
    return <span className="ships ships--unknown">shipping unchecked</span>;
  }
  return null;
}

function TierBlock({ tier, sources }: { tier: Tier; sources: Source[] }) {
  if (sources.length === 0) return null;

  const rows = orderSources(sources);
  const found = rows.filter((s) => s.kind === "product");
  const local = rows.filter((s) => s.ships === "local");

  return (
    <section className="tier">
      <div className="tier__head">
        <h3 className="tier__name">{TIER_LABEL[tier]}</h3>
        <span className="tier__count num">
          {found.length > 0
            ? `${found.length} found`
            : `${rows.length} places to look`}
          {local.length > 0 && local.length < rows.length
            ? `, ${local.length} local`
            : ""}
        </span>
      </div>

      <table className="ruled">
        <thead>
          <tr>
            <th scope="col">Where</th>
            <th scope="col">What</th>
            <th scope="col">Price</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.id} className={s.ships === "overseas" ? "row--overseas" : undefined}>
              <td>
                <span className="seller">{s.retailer}</span>
                <span className="seller__tags">
                  {s.kind === "product" && <span className="found">found</span>}
                  <ShipsTag source={s} />
                </span>
              </td>
              <td>
                <a href={s.url} target="_blank" rel="noreferrer noopener">
                  {s.kind === "product" ? (s.product_name ?? "View") : "Search their site"}
                </a>
                {s.note && <div className="small muted">{s.note}</div>}
              </td>
              <td className={s.kind === "product" ? "num" : "num muted"}>
                {s.price ?? "not listed"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

export function ItemDetail() {
  const { itemId } = useParams();
  const id = Number(itemId);
  const { search } = useLocation();

  const item = useAsync<Item>(() => api.item(id), [id]);
  const status = useStatus();

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function findPlaces(useWebSearch: boolean) {
    setBusy(true);
    setError(null);
    try {
      item.setData(await api.sourceItem(id, useWebSearch));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (item.loading) return <LoadingLines label="Loading piece" lines={5} />;
  if (item.error) return <ErrorState error={item.error} onRetry={item.reload} />;

  const data = item.data!;
  const byTier = (tier: Tier) => data.sources.filter((s) => s.tier === tier);
  const hasSources = data.sources.length > 0;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{sentence(data.name)}</h1>
          <ul className="meta">
            <li>{categoryLabel(data.category)}</li>
            {data.est_tier && data.est_tier !== "unclear" && (
              <li>looks like a {data.est_tier} piece</li>
            )}
          </ul>
        </div>
        <div className="btn-row">
          <Link className="btn btn--quiet" to={{ pathname: `/boards/${data.board_id}`, search }}>
            Back to the board
          </Link>
        </div>
      </div>

      <div className="split">
        <div>
          <p className="prose">{data.description}</p>

          {!hasSources && (
            <div className="state">
              <p className="state__title">Nowhere to buy it yet</p>
              <p className="state__body">
                Atelier can give you tiered search links instantly, or search the web for
                the actual products and prices. That one takes about twenty seconds.
              </p>
              <div className="btn-row">
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={() => findPlaces(true)}
                  disabled={busy}
                >
                  {busy ? "Looking…" : "Find real products"}
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => findPlaces(false)}
                  disabled={busy}
                >
                  Just the search links
                </button>
              </div>
            </div>
          )}

          {error && <Banner tone="error">{error}</Banner>}
          {busy && hasSources && <Banner>Searching…</Banner>}

          {hasSources && (
            <>
              {TIER_ORDER.map((tier) => (
                <TierBlock key={tier} tier={tier} sources={byTier(tier)} />
              ))}

              <p className="notice">
                Rows marked <span className="found">found</span> are products Atelier
                actually located, with the price as listed at the time of the search.
                Check it on the page before buying. Unmarked rows are searches of that
                shop, not a promise they stock it.
                {status && (
                  <>
                    {" "}
                    Shopping for{" "}
                    <strong>{REGION_NAMES[status.region] ?? status.region}</strong>
                    {status.include_international
                      ? ", with overseas sellers listed after the local ones."
                      : ", local sellers only."}
                  </>
                )}
              </p>

              <div className="btn-row">
                <button type="button" className="btn" onClick={() => findPlaces(true)} disabled={busy}>
                  {busy ? "Looking…" : "Search again"}
                </button>
              </div>
            </>
          )}
        </div>

        <div>
          <div className="panel">
            <div className="print__mat">
              <div className="print__window">
                <img
                  className="pin-image"
                  src={imageUrl(data.pin_image_file)}
                  alt={`The saved image this came from: ${data.name}`}
                  width={600}
                  height={800}
                />
              </div>
            </div>
            <p className="pencil">From your saved image</p>

            <h2>What it is</h2>
            <dl className="facts">
              {Object.entries(data.attributes).map(([key, value]) => (
                <div key={key}>
                  <dt>{key.replace(/_/g, " ")}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
              <div>
                <dt>confidence</dt>
                <dd className="num">{Math.round(data.confidence * 100)}%</dd>
              </div>
            </dl>

            {data.search_terms.length > 0 && (
              <div>
                <h3>Search terms</h3>
                <ul className="tags">
                  {data.search_terms.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
