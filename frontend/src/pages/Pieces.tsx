import { Link, useLocation, useSearchParams } from "react-router-dom";

import { Empty, ErrorState, LoadingLines } from "../components/States";
import { api, categoryLabel, imageUrl, type Item } from "../lib/api";
import { useDomain } from "../lib/domain";
import { useAsync } from "../lib/useAsync";

/** Everything found across every board in this domain, grouped by category.
 *  The "what do I actually keep saving" view. */
export function Pieces() {
  const [domain] = useDomain();
  const { search } = useLocation();
  const [params, setParams] = useSearchParams();

  const heroOnly = params.get("hero") === "1";
  const category = params.get("category") ?? "";

  const items = useAsync<Item[]>(
    () => api.items({ domain, hero_only: heroOnly }),
    [domain, heroOnly],
  );

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  const all = items.data ?? [];
  const categories = Array.from(new Set(all.map((i) => i.category))).sort();
  const shown = category ? all.filter((i) => i.category === category) : all;

  const grouped = new Map<string, Item[]>();
  for (const item of shown) {
    const list = grouped.get(item.category) ?? [];
    list.push(item);
    grouped.set(item.category, list);
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Pieces</h1>
          <p className="page-head__meta num">
            {shown.length} found across your {domain === "interior" ? "interiors" : "wardrobe"}{" "}
            boards
          </p>
        </div>

        <div className="btn-row">
          <label className="small muted" htmlFor="category-filter">
            Category
          </label>
          <select
            id="category-filter"
            name="category"
            className="field__select"
            style={{ width: "auto" }}
            value={category}
            onChange={(e) => setParam("category", e.target.value)}
          >
            <option value="">All</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {categoryLabel(c)}
              </option>
            ))}
          </select>

          <button
            type="button"
            className="btn"
            aria-pressed={heroOnly}
            onClick={() => setParam("hero", heroOnly ? "" : "1")}
          >
            {heroOnly ? "Showing standouts" : "Standouts only"}
          </button>
        </div>
      </div>

      {items.loading && <LoadingLines label="Loading pieces" lines={6} />}
      {items.error && <ErrorState error={items.error} onRetry={items.reload} />}

      {items.data && all.length === 0 && (
        <Empty
          title="Nothing found yet"
          body="Pieces show up here once a board has been read. Open a board and read it first."
          action={
            <Link className="btn btn--primary" to={{ pathname: "/", search }}>
              Go to boards
            </Link>
          }
        />
      )}

      {items.data && all.length > 0 && shown.length === 0 && (
        <Empty title="Nothing in that category" body="Clear the filter to see everything else." />
      )}

      {Array.from(grouped.entries()).map(([cat, list]) => (
        <section key={cat}>
          <h2 className="section-head">
            {categoryLabel(cat)} <span className="muted small num">({list.length})</span>
          </h2>
          <div className="hang">
            {list.map((item, index) => (
              <Link
                key={item.id}
                className="print"
                to={{ pathname: `/items/${item.id}`, search }}
                style={{ textDecoration: "none" }}
              >
                <span className="print__mat">
                  <span className="print__window">
                    <img
                      className="pin-image"
                      src={imageUrl(item.pin_image_file)}
                      alt=""
                      loading={index === 0 ? "eager" : "lazy"}
                      fetchPriority={index === 0 ? "high" : undefined}
                      width={600}
                      height={800}
                    />
                  </span>
                </span>
                <span className="label">
                  <span className="label__name">{item.name}</span>
                  <br />
                  <span className="label__meta">
                    {item.sources.length
                      ? `${item.sources.length} places to buy`
                      : "Not sourced yet"}
                  </span>
                </span>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </>
  );
}
