import { useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { Print } from "../components/Print";
import { Banner, Empty, ErrorState, Loading, LoadingLines } from "../components/States";
import { api, categoryLabel, type Pin, type StyleProfile } from "../lib/api";
import { useAsync } from "../lib/useAsync";

function StylePanel({ boardId, pinCount }: { boardId: number; pinCount: number }) {
  const style = useAsync<StyleProfile | null>(() => api.latestStyle(boardId), [boardId]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function read() {
    setBusy(true);
    setError(null);
    try {
      style.setData(await api.readStyle(boardId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  if (style.loading) {
    return <div className="panel"><LoadingLines label="Loading style read" /></div>;
  }

  const profile = style.data;

  return (
    <div className="panel">
      <h2>The read</h2>

      {!profile && !error && (
        <p className="small muted">
          Atelier can look at the whole board at once and name what ties it together:
          the palette, the materials, and where two directions in it disagree.
        </p>
      )}

      {error && <Banner tone="error">{error}</Banner>}

      {profile && (
        <>
          <p className="prose">{profile.summary}</p>

          {profile.palette.length > 0 && (
            <ul className="palette">
              {profile.palette.map((c) => (
                <li className="swatch" key={`${c.name}-${c.hex}`}>
                  <div
                    className="swatch__chip"
                    style={{ background: c.hex }}
                    aria-hidden="true"
                  />
                  <div className="swatch__name">{c.name}</div>
                  <ul className="meta num swatch__role">
                    <li>{c.role}</li>
                    <li>{c.hex}</li>
                  </ul>
                </li>
              ))}
            </ul>
          )}

          {profile.materials.length > 0 && (
            <div>
              <h3>Materials</h3>
              <ul className="tags">
                {profile.materials.map((m) => (
                  <li key={m}>{m}</li>
                ))}
              </ul>
            </div>
          )}

          {Object.keys(profile.axes).length > 0 && (
            <dl className="facts">
              {Object.entries(profile.axes).map(([axis, where]) => (
                <div key={axis}>
                  <dt>{axis}</dt>
                  <dd>{where}</dd>
                </div>
              ))}
            </dl>
          )}

          {profile.tensions.length > 0 && (
            <div>
              <h3>Where it fights itself</h3>
              <ul className="prose">
                {profile.tensions.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </div>
          )}

          <p className="small muted num">Read from {profile.pin_count} images.</p>
        </>
      )}

      <div className="btn-row">
        <button
          type="button"
          className={profile ? "btn" : "btn btn--primary"}
          onClick={read}
          disabled={busy || pinCount === 0}
        >
          {busy ? "Reading…" : profile ? "Read again" : "Read this board"}
        </button>
      </div>
    </div>
  );
}

export function BoardDetail() {
  const { boardId } = useParams();
  const id = Number(boardId);
  const { search } = useLocation();

  const board = useAsync(() => api.board(id), [id]);
  const pins = useAsync<Pin[]>(() => api.pins(id), [id]);

  const [selected, setSelected] = useState<Pin | null>(null);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function readAll() {
    setBusy(true);
    setError(null);
    setReport(null);
    try {
      const result = await api.analyzeBoard(id);
      const parts = [`Read ${result.analyzed}`];
      if (result.skipped) parts.push(`${result.skipped} already done`);
      if (result.failed.length) parts.push(`${result.failed.length} failed`);
      setReport(parts.join(", "));
      pins.reload();
      board.reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function readOne(pin: Pin) {
    setError(null);
    try {
      const updated = await api.analyzePin(id, pin.id);
      pins.setData((pins.data ?? []).map((p) => (p.id === updated.id ? updated : p)));
      setSelected(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const unread = (pins.data ?? []).filter((p) => !p.analyzed_at).length;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{board.data?.name ?? "Board"}</h1>
          {board.data && (
            <ul className="meta num">
              <li>{board.data.pin_count} images</li>
              <li>{board.data.analyzed_count} read</li>
              <li>{board.data.item_count} pieces found</li>
            </ul>
          )}
        </div>
        <div className="btn-row">
          <Link className="btn btn--quiet" to={{ pathname: "/", search }}>
            All boards
          </Link>
          <button
            type="button"
            className="btn btn--primary"
            onClick={readAll}
            disabled={busy || unread === 0}
          >
            {busy
              ? "Reading the board…"
              : unread === 0
                ? "All read"
                : `Read ${unread} unread`}
          </button>
        </div>
      </div>

      {report && <Banner>{report}</Banner>}
      {error && <Banner tone="error">{error}</Banner>}
      {busy && (
        <Banner>
          Reading one image at a time, a few seconds each. Leave the tab open.
        </Banner>
      )}

      <div className="split">
        <div>
          {pins.loading && <Loading label="Loading images" />}
          {pins.error && <ErrorState error={pins.error} onRetry={pins.reload} />}

          {pins.data && pins.data.length === 0 && (
            <Empty
              title="This board has no images"
              body="Sync it again from Pinterest, or import the folder once more."
            />
          )}

          {pins.data && pins.data.length > 0 && (
            <div className="hang">
              {pins.data.map((pin, index) => (
                <Print
                  key={pin.id}
                  pin={pin}
                  priority={index === 0}
                  selected={selected?.id === pin.id}
                  onSelect={setSelected}
                />
              ))}
            </div>
          )}
        </div>

        <div>
          {selected ? (
            <div className="panel">
              <h2>{selected.title || "Untitled"}</h2>
              {selected.scene_summary && <p className="prose">{selected.scene_summary}</p>}

              {!selected.analyzed_at && (
                <>
                  <p className="small muted">This one has not been read yet.</p>
                  <button type="button" className="btn btn--primary" onClick={() => readOne(selected)}>
                    Read this image
                  </button>
                </>
              )}

              {selected.analyzed_at && selected.items.length === 0 && (
                <p className="small muted">
                  Nothing shoppable found here. It may be an architectural shot or a mood
                  image rather than a product.
                </p>
              )}

              {selected.items.length > 0 && (
                <div className="rows">
                  {selected.items.map((item) => (
                    <Link
                      className="row"
                      key={item.id}
                      to={{ pathname: `/items/${item.id}`, search }}
                    >
                      <div className="row__main">
                        <div>{item.name}</div>
                        <ul className="meta">
                          <li>{categoryLabel(item.category)}</li>
                          {item.is_hero && <li>the subject</li>}
                        </ul>
                      </div>
                      <div className="row__aside num">
                        {Math.round(item.confidence * 100)}%
                      </div>
                    </Link>
                  ))}
                </div>
              )}

              {selected.link && (
                <p className="small">
                  <a href={selected.link} target="_blank" rel="noreferrer noopener">
                    Where this pin pointed
                  </a>
                </p>
              )}

              <button type="button" className="btn btn--quiet" onClick={() => setSelected(null)}>
                Close
              </button>
            </div>
          ) : (
            <StylePanel boardId={id} pinCount={board.data?.pin_count ?? 0} />
          )}
        </div>
      </div>
    </>
  );
}
