"use client";

/**
 * Data-fetching hook with the loading / error / retry states PRD §9 requires.
 *
 * The screens are client components with entrance animations, so they fetch on
 * mount rather than being converted to server components — that keeps the
 * existing motion work intact.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "./client";

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
  /** True while a retry is in flight but stale data is still on screen. */
  refreshing: boolean;
  retry: () => void;
}

export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [attempt, setAttempt] = useState(0);

  // Guards against setting state after unmount, and against an earlier slow
  // response overwriting a later fast one.
  const liveRequest = useRef(0);

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const requestId = ++liveRequest.current;
    let cancelled = false;

    setError(null);
    if (data === null) setLoading(true);
    else setRefreshing(true);

    fetcherRef
      .current()
      .then((result) => {
        if (cancelled || requestId !== liveRequest.current) return;
        setData(result);
      })
      .catch((err: unknown) => {
        if (cancelled || requestId !== liveRequest.current) return;
        setError(
          err instanceof ApiError
            ? err
            : new ApiError("Something went wrong.", "unknown", true, 0),
        );
      })
      .finally(() => {
        if (cancelled || requestId !== liveRequest.current) return;
        setLoading(false);
        setRefreshing(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt, ...deps]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return { data, loading, error, refreshing, retry };
}
