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
import { useAsync } from "../lib/useAsync";

function TierBlock({ tier, sources }: { tier: Tier; sources: Source[] }) {
  if (sources.length === 0) return null;

  const found = sources.filter((s) => s.kind === "product");
  const searches = sources.filter((s) => s.kind === "search");

  return (
    <section className="tier">
      <div className="tier__head">
        <h3 className="tier__name">{TIER_LABEL[tier]}</h3>
        <span className="tier__count num">
          {found.length > 0 ? `${found.length} found` : `${searches.length} places to look`}
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
          {found.map((s) => (
            <tr key={s.id}>
              <td>
                {s.retailer} <span className="found">found</span>
              </td>
              <td>
                <a href={s.url} target="_blank" rel="noreferrer noopener">
                  {s.product_name ?? "View"}
                </a>
                {s.note && <div className="small muted">{s.note}</div>}
              </td>
              <td className="num">{s.price ?? "not listed"}</td>
            </tr>
          ))}
          {searches.map((s) => (
            <tr key={s.id}>
              <td>{s.retailer}</td>
              <td>
                <a href={s.url} target="_blank" rel="noreferrer noopener">
                  Search their site
                </a>
                {s.note && <div className="small muted">{s.note}</div>}
              </td>
              <td className="num muted">not listed</td>
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
