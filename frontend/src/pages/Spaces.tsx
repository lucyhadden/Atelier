import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { Banner, Empty, ErrorState, LoadingLines } from "../components/States";
import { api, type Space } from "../lib/api";
import { useDomain } from "../lib/domain";
import { useAsync } from "../lib/useAsync";

export function Spaces() {
  const [domain] = useDomain();
  const { search } = useLocation();
  const spaces = useAsync<Space[]>(() => api.spaces(domain), [domain]);

  const [name, setName] = useState("");
  const [kind, setKind] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isInterior = domain === "interior";

  async function create(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.createSpace({
        name: name.trim(),
        domain,
        kind: kind.trim() || undefined,
        notes: notes.trim() || undefined,
      });
      setName("");
      setKind("");
      setNotes("");
      spaces.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>{isInterior ? "Spaces" : "Briefs"}</h1>
        <p className="page-head__meta num">{spaces.data ? `${spaces.data.length}` : ""}</p>
      </div>

      <div className="split">
        <div>
          {spaces.loading && <LoadingLines label="Loading spaces" lines={3} />}
          {spaces.error && <ErrorState error={spaces.error} onRetry={spaces.reload} />}

          {spaces.data && spaces.data.length === 0 && (
            <Empty
              title={isInterior ? "No rooms yet" : "No briefs yet"}
              body={
                isInterior
                  ? "Add a room, upload its floor plan or a photo, and Atelier will apply a board's look to the actual space, including where that look will fight the room."
                  : "Add a brief (a trip, a season, an occasion) and Atelier will build the plan from a board you have read."
              }
            />
          )}

          {spaces.data && spaces.data.length > 0 && (
            <div className="rows">
              {spaces.data.map((s) => (
                <Link className="row" key={s.id} to={{ pathname: `/spaces/${s.id}`, search }}>
                  <div className="row__main">
                    <div>{s.name}</div>
                    <ul className="meta num">
                      {s.kind && <li>{s.kind}</li>}
                      <li>
                        {s.plans.length} {s.plans.length === 1 ? "image" : "images"}
                      </li>
                    </ul>
                  </div>
                  <div className="row__aside">
                    {s.plans.some((p) => p.analyzed_at) ? "Read" : "Not read"}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <form className="panel" onSubmit={create}>
          <h2>{isInterior ? "Add a room" : "Add a brief"}</h2>

          <label className="field">
            <span className="field__label">Name</span>
            <input
              className="field__input"
              name="name"
              type="text"
              autoComplete="off"
              placeholder={isInterior ? "Living room" : "Autumn capsule"}
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <span className="field__help" />
          </label>

          <label className="field">
            <span className="field__label">Kind (optional)</span>
            <input
              className="field__input"
              name="kind"
              type="text"
              autoComplete="off"
              placeholder={isInterior ? "north-facing, 4m x 5m" : "work, cold weather"}
              value={kind}
              onChange={(e) => setKind(e.target.value)}
            />
            <span className="field__help" />
          </label>

          <label className="field">
            <span className="field__label">What you want from it</span>
            <textarea
              className="field__textarea"
              name="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={
                isInterior
                  ? "Somewhere to read in the afternoon, has to seat four, the floor stays."
                  : "Things I can wear to the office and to dinner without changing."
              }
            />
            <span className="field__help">The more constraints you give, the better the plan.</span>
          </label>

          <button type="submit" className="btn btn--primary" disabled={busy || !name.trim()}>
            {busy ? "Adding…" : "Add"}
          </button>
          {error && <Banner tone="error">{error}</Banner>}
        </form>
      </div>
    </>
  );
}
