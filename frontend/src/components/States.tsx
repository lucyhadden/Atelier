/** The four states every data region owes: loading, empty, error, full.
 *  "Full" is the caller's own markup; these cover the other three. */

import type { ReactNode } from "react";

export function Loading({ label = "Loading", frames = 6 }: { label?: string; frames?: number }) {
  return (
    <div className="skeleton-grid" role="status" aria-live="polite">
      <span className="visually-hidden">{label}</span>
      {Array.from({ length: frames }, (_, i) => (
        <div key={i} aria-hidden="true">
          <div className="skeleton skeleton--frame" />
          <div className="skeleton skeleton--line" style={{ width: "70%" }} />
          <div className="skeleton skeleton--line" style={{ width: "45%" }} />
        </div>
      ))}
    </div>
  );
}

export function LoadingLines({ label = "Loading", lines = 3 }: { label?: string; lines?: number }) {
  return (
    <div role="status" aria-live="polite">
      <span className="visually-hidden">{label}</span>
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="skeleton skeleton--line"
          aria-hidden="true"
          style={{ width: `${90 - i * 15}%` }}
        />
      ))}
    </div>
  );
}

export function Empty({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <div className="state">
      <p className="state__title">{title}</p>
      <p className="state__body">{body}</p>
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className="state state--error" role="alert">
      <p className="state__title">That did not work</p>
      <p className="state__body">{message}</p>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function Banner({
  children,
  tone = "info",
}: {
  children: ReactNode;
  tone?: "info" | "error";
}) {
  return (
    <p className={`banner${tone === "error" ? " banner--error" : ""}`} role={tone === "error" ? "alert" : undefined}>
      {children}
    </p>
  );
}
