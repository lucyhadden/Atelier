import { useRef, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";

import { Banner, Empty, ErrorState, LoadingLines } from "../components/States";
import {
  api,
  imageUrl,
  type Board,
  type DesignPlan,
  type FloorPlan,
  type Space,
} from "../lib/api";
import { useAsync } from "../lib/useAsync";

function PlanImage({
  plan,
  spaceId,
  onRead,
}: {
  plan: FloorPlan;
  spaceId: number;
  onRead: (updated: FloorPlan) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function read() {
    setBusy(true);
    setError(null);
    try {
      onRead(await api.analyzePlan(spaceId, plan.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const a = plan.analysis;

  return (
    <div className="panel">
      <div className="print__mat">
        <div className="print__window" style={{ aspectRatio: "4 / 3" }}>
          <img
            className="pin-image"
            src={imageUrl(plan.image_file)}
            alt={plan.label ?? (plan.kind === "floorplan" ? "Floor plan" : "Room photo")}
            style={{ objectFit: "contain", background: "var(--color-card)" }}
            width={800}
            height={600}
          />
        </div>
      </div>
      <p className="pencil">
        {plan.label || (plan.kind === "floorplan" ? "Floor plan" : "Room photo")}
      </p>

      {error && <Banner tone="error">{error}</Banner>}

      {!a && (
        <button type="button" className="btn btn--primary" onClick={read} disabled={busy}>
          {busy ? "Reading…" : "Read this plan"}
        </button>
      )}

      {a && (
        <>
          <p className="prose">{a.summary}</p>

          {a.scale_confidence === "none" || a.scale_confidence === "low" ? (
            <p className="notice">
              Dimensions were not legible on this image ({a.scale_confidence} confidence), so
              nothing here is measured. Type the real dimensions into the brief below and the
              plan will use them.
            </p>
          ) : null}

          {a.rooms.length > 0 && (
            <table className="ruled">
              <thead>
                <tr>
                  <th scope="col">Room</th>
                  <th scope="col">Size</th>
                </tr>
              </thead>
              <tbody>
                {a.rooms.map((r, i) => (
                  <tr key={`${r.name}-${i}`}>
                    <td>
                      {r.name ?? "Unnamed"}
                      {r.notes && <div className="small muted">{r.notes}</div>}
                    </td>
                    <td className="num">{r.approx_dimensions ?? "unclear"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {a.fixed_features.length > 0 && (
            <div>
              <h3>Fixed features</h3>
              <ul className="tags">
                {a.fixed_features.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
            </div>
          )}

          {a.constraints.length > 0 && (
            <div>
              <h3>Constraints</h3>
              <ul className="prose">
                {a.constraints.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}

          <button type="button" className="btn btn--quiet" onClick={read} disabled={busy}>
            Read again
          </button>
        </>
      )}
    </div>
  );
}

export function SpaceDetail() {
  const { spaceId } = useParams();
  const id = Number(spaceId);
  const { search } = useLocation();
  const fileInput = useRef<HTMLInputElement>(null);

  const space = useAsync<Space>(() => api.space(id), [id]);
  const designs = useAsync<DesignPlan[]>(() => api.designs(id), [id]);
  const boards = useAsync<Board[]>(
    () => (space.data ? api.boards(space.data.domain) : Promise.resolve([])),
    [space.data?.domain],
  );

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [kind, setKind] = useState("floorplan");
  const [label, setLabel] = useState("");

  const [boardId, setBoardId] = useState("");
  const [brief, setBrief] = useState("");
  const [building, setBuilding] = useState(false);
  const [buildError, setBuildError] = useState<string | null>(null);

  async function upload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    try {
      await api.uploadPlan(id, file, kind, label);
      setLabel("");
      if (fileInput.current) fileInput.current.value = "";
      space.reload();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  }

  async function build(event: React.FormEvent) {
    event.preventDefault();
    setBuilding(true);
    setBuildError(null);
    try {
      await api.buildDesign(id, {
        board_id: boardId ? Number(boardId) : null,
        brief: brief.trim(),
      });
      designs.reload();
    } catch (err) {
      setBuildError(err instanceof Error ? err.message : String(err));
    } finally {
      setBuilding(false);
    }
  }

  if (space.loading) return <LoadingLines label="Loading space" lines={4} />;
  if (space.error) return <ErrorState error={space.error} onRetry={space.reload} />;

  const data = space.data!;
  const readBoards = (boards.data ?? []).filter((b) => b.analyzed_count > 0);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{data.name}</h1>
          {data.kind && <p className="page-head__meta">{data.kind}</p>}
        </div>
        <Link className="btn btn--quiet" to={{ pathname: "/spaces", search }}>
          All spaces
        </Link>
      </div>

      {data.notes && <p className="prose">{data.notes}</p>}

      <div className="split">
        <div>
          <h2 className="section-head">The plan</h2>

          <form className="panel" onSubmit={build}>
            <label className="field">
              <span className="field__label">Built from which board</span>
              <select
                className="field__select"
                name="board_id"
                value={boardId}
                onChange={(e) => setBoardId(e.target.value)}
              >
                <option value="">No board: use the space alone</option>
                {readBoards.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name} ({b.item_count} pieces)
                  </option>
                ))}
              </select>
              <span className="field__help">
                {readBoards.length === 0
                  ? "No boards have been read yet. Read one first for a style-led plan."
                  : "Only boards that have been read appear here."}
              </span>
            </label>

            <label className="field">
              <span className="field__label">Anything else it should know</span>
              <textarea
                className="field__textarea"
                name="brief"
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                placeholder="The room is 4.2m x 3.1m. Budget is about £3k. The sofa stays."
              />
              <span className="field__help">
                Real dimensions and a budget change the plan more than anything else.
              </span>
            </label>

            <button type="submit" className="btn btn--primary" disabled={building}>
              {building ? "Writing the plan…" : "Build the plan"}
            </button>
            {buildError && <Banner tone="error">{buildError}</Banner>}
          </form>

          {designs.loading && <LoadingLines label="Loading plans" />}
          {designs.error && <ErrorState error={designs.error} onRetry={designs.reload} />}

          {designs.data && designs.data.length === 0 && !building && (
            <Empty
              title="No plan yet"
              body="Pick a board above and build one. It takes about thirty seconds."
            />
          )}

          {(designs.data ?? []).map((plan) => (
            <article key={plan.id} style={{ marginTop: "var(--space-2xl)" }}>
              <h2 className="section-head">{plan.title}</h2>
              <p className="prose">{plan.narrative}</p>

              {plan.zones.length > 0 && (
                <>
                  <h3 style={{ marginTop: "var(--space-lg)" }}>Zones</h3>
                  <div className="rows">
                    {plan.zones.map((z) => (
                      <div className="row" key={z.zone}>
                        <div className="row__main">
                          <div>{z.zone}</div>
                          <div className="small muted">{z.intent}</div>
                          {z.pieces.length > 0 && (
                            <ul className="tags" style={{ marginTop: "var(--space-2xs)" }}>
                              {z.pieces.map((p) => (
                                <li key={p}>{p}</li>
                              ))}
                            </ul>
                          )}
                          {z.notes && <div className="small muted">{z.notes}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {plan.shopping_list.length > 0 && (
                <>
                  <h3 style={{ marginTop: "var(--space-lg)" }}>What to buy, in order</h3>
                  <table className="ruled">
                    <thead>
                      <tr>
                        <th scope="col">What</th>
                        <th scope="col">Why</th>
                        <th scope="col">When</th>
                        <th scope="col">Spend</th>
                      </tr>
                    </thead>
                    <tbody>
                      {plan.shopping_list.map((row, i) => (
                        <tr key={`${row.category}-${i}`}>
                          <td>{row.what}</td>
                          <td className="small muted">{row.why}</td>
                          <td>{row.priority}</td>
                          <td>{row.budget_band}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}

              {plan.cautions.length > 0 && (
                <>
                  <h3 style={{ marginTop: "var(--space-lg)" }}>Where this will fight the space</h3>
                  <ul className="prose">
                    {plan.cautions.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                </>
              )}
            </article>
          ))}
        </div>

        <div>
          <h2 className="section-head">Floor plans and photos</h2>

          <div className="panel">
            <label className="field">
              <span className="field__label">What is it</span>
              <select
                className="field__select"
                name="kind"
                value={kind}
                onChange={(e) => setKind(e.target.value)}
              >
                <option value="floorplan">A floor plan</option>
                <option value="photo">A photo of the space</option>
              </select>
              <span className="field__help" />
            </label>

            <label className="field">
              <span className="field__label">Label (optional)</span>
              <input
                className="field__input"
                name="label"
                type="text"
                autoComplete="off"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                placeholder="Ground floor"
              />
              <span className="field__help" />
            </label>

            <label className="field">
              <span className="field__label">File</span>
              <input
                ref={fileInput}
                className="field__input"
                name="file"
                type="file"
                accept="image/*"
                onChange={upload}
                disabled={uploading}
              />
              <span className="field__help">
                {uploading ? "Uploading…" : "PNG or JPEG, up to 25MB."}
              </span>
            </label>

            {uploadError && <Banner tone="error">{uploadError}</Banner>}
          </div>

          {data.plans.length === 0 && (
            <Empty
              title="Nothing uploaded"
              body="A floor plan lets the plan talk about real walls and windows instead of generic advice."
            />
          )}

          {data.plans.map((plan) => (
            <div key={plan.id} style={{ marginTop: "var(--space-lg)" }}>
              <PlanImage
                plan={plan}
                spaceId={id}
                onRead={(updated) =>
                  space.setData({
                    ...data,
                    plans: data.plans.map((p) => (p.id === updated.id ? updated : p)),
                  })
                }
              />
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
