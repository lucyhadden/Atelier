/** Minimal async-state hook: the four states, without a data library. */

import { useCallback, useEffect, useState } from "react";

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  /** Normalised to an Error so `error && <ErrorState/>` narrows cleanly in JSX. */
  error: Error | null;
  reload: () => void;
  setData: (value: T) => void;
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [nonce, setNonce] = useState(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(fn, deps);

  useEffect(() => {
    let live = true;
    setLoading(true);
    setError(null);
    run()
      .then((value) => live && setData(value))
      .catch((err) => live && setError(err instanceof Error ? err : new Error(String(err))))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [run, nonce]);

  return {
    data,
    loading,
    error,
    reload: () => setNonce((n) => n + 1),
    setData,
  };
}
