import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { Banner, Empty, ErrorState, LoadingLines } from "../components/States";
import { api, type Board } from "../lib/api";
import { useDomain } from "../lib/domain";
import { useAsync } from "../lib/useAsync";

function ImportForm({ domain, onDone }: { domain: "interior" | "wardrobe"; onDone: () => void }) {
  const [path, setPath] = useState("");
  const [name, setName] = useState("");
  const [isExport, setIsExport] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!path.trim()) return;
    setBusy(true);
    setError(null);
    setDone(null);
    try {
      const result = await api.importFolder({
        path: path.trim(),
        domain,
        board_name: name.trim() || undefined,
        is_pinterest_export: isExport,
      });
      const added = result.total_added ?? result.added ?? 0;
      setDone(`Imported ${added} image${added === 1 ? "" : "s"}.`);
      setPath("");
      setName("");
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={submit}>
      <h2>Import a folder</h2>
      <p className="small muted">
        Point Atelier at a folder of saved images. Nothing is uploaded anywhere;
        the files are copied into this project&rsquo;s own data directory.
      </p>

      <label className="field">
        <span className="field__label">Folder path</span>
        <input
          className="field__input"
          name="path"
          type="text"
          autoComplete="off"
          spellCheck={false}
          placeholder="/Users/you/Pictures/future-home"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          required
        />
        <span className="field__help">
          {isExport
            ? "Each subfolder of images becomes its own board."
            : "The folder name becomes the board name unless you set one below."}
        </span>
      </label>

      <label className="field">
        <span className="field__label">Board name (optional)</span>
        <input
          className="field__input"
          name="board_name"
          type="text"
          autoComplete="off"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isExport}
        />
        <span className="field__help" />
      </label>

      <label className="field small">
        <input
          type="checkbox"
          name="is_export"
          checked={isExport}
          onChange={(e) => setIsExport(e.target.checked)}
        />{" "}
        This is an unzipped Pinterest data export
      </label>

      <div className="btn-row">
        <button type="submit" className="btn btn--primary" disabled={busy || !path.trim()}>
          {busy ? "Importing…" : "Import"}
        </button>
        {done && <span className="small muted">{done}</span>}
      </div>
      {error && <Banner tone="error">{error}</Banner>}
    </form>
  );
}

function PinterestPanel({ domain, onSynced }: { domain: "interior" | "wardrobe"; onSynced: () => void }) {
  const status = useAsync(() => api.pinterestStatus(), []);
  const [boards, setBoards] = useState<{ external_id: string; name: string; pin_count: number }[] | null>(
    null,
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (status.loading) return <div className="panel"><LoadingLines label="Checking Pinterest" /></div>;
  if (status.error) return <div className="panel"><ErrorState error={status.error} onRetry={status.reload} /></div>;

  const s = status.data!;

  if (!s.configured) {
    return (
      <div className="panel">
        <h2>Pinterest</h2>
        <p className="small muted">
          Not configured yet. Create an app at developers.pinterest.com, add{" "}
          <code>{s.redirect_uri}</code> as its redirect URI, then put the client id and
          secret in <code>.env</code> and restart the backend.
        </p>
        <p className="small muted">
          Until then, use &ldquo;Request your data&rdquo; in Pinterest settings and import the
          unzipped export with the form above.
        </p>
      </div>
    );
  }

  if (!s.connected) {
    return (
      <div className="panel">
        <h2>Pinterest</h2>
        <p className="small muted">Configured, but not connected yet.</p>
        <a className="btn btn--primary" href="/api/pinterest/login">
          Connect Pinterest
        </a>
      </div>
    );
  }

  async function loadBoards() {
    setError(null);
    try {
      const result = await api.pinterestBoards();
      setBoards(result.boards);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function sync(externalId: string, name: string) {
    setBusy(externalId);
    setError(null);
    try {
      await api.pinterestSync({ external_id: externalId, domain, name });
      onSynced();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="panel">
      <h2>Pinterest</h2>
      <p className="small muted">Connected.</p>
      <div className="btn-row">
        <button type="button" className="btn" onClick={loadBoards}>
          {boards ? "Refresh boards" : "Show my boards"}
        </button>
        <button
          type="button"
          className="btn btn--quiet"
          onClick={() => api.pinterestDisconnect().then(status.reload)}
        >
          Disconnect
        </button>
      </div>

      {error && <Banner tone="error">{error}</Banner>}

      {boards && boards.length === 0 && <p className="small muted">No boards came back.</p>}

      {boards && boards.length > 0 && (
        <div className="rows">
          {boards.map((b) => (
            <div className="row" key={b.external_id}>
              <div className="row__main">
                <div>{b.name}</div>
                <div className="small muted num">{b.pin_count} pins</div>
              </div>
              <div className="row__aside">
                <button
                  type="button"
                  className="btn"
                  disabled={busy === b.external_id}
                  onClick={() => sync(b.external_id, b.name)}
                >
                  {busy === b.external_id ? "Syncing…" : "Sync"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function Boards() {
  const [domain] = useDomain();
  const { search } = useLocation();
  const boards = useAsync<Board[]>(() => api.boards(domain), [domain]);

  return (
    <>
      <div className="page-head">
        <h1>Boards</h1>
        <p className="page-head__meta">
          {boards.data ? `${boards.data.length} saved` : ""}
        </p>
      </div>

      <div className="split">
        <div>
          {boards.loading && <LoadingLines label="Loading boards" lines={4} />}
          {boards.error && <ErrorState error={boards.error} onRetry={boards.reload} />}

          {boards.data && boards.data.length === 0 && (
            <Empty
              title="No boards here yet"
              body={
                domain === "interior"
                  ? "Import a folder of saved interiors, or connect Pinterest and sync a board. Once images are in, Atelier reads them one by one."
                  : "Import a folder of saved outfits, or connect Pinterest and sync a board."
              }
            />
          )}

          {boards.data && boards.data.length > 0 && (
            <div className="rows">
              {boards.data.map((b) => (
                <Link className="row" key={b.id} to={{ pathname: `/boards/${b.id}`, search }}>
                  <div className="row__main">
                    <div>{b.name}</div>
                    <ul className="meta num">
                      <li>{b.pin_count} images</li>
                      <li>{b.analyzed_count} read</li>
                      <li>{b.item_count} pieces</li>
                      {b.source === "pinterest" && <li>from Pinterest</li>}
                    </ul>
                  </div>
                  <div className="row__aside">
                    {b.analyzed_count < b.pin_count ? "Needs reading" : "Read"}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div>
          <ImportForm domain={domain} onDone={boards.reload} />
          <div style={{ marginTop: "var(--space-lg)" }}>
            <PinterestPanel domain={domain} onSynced={boards.reload} />
          </div>
        </div>
      </div>
    </>
  );
}
