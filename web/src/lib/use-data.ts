"use client";

import { useState, useEffect, useCallback, useReducer } from "react";

interface JsonState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  path: string | null;
}

type JsonAction<T> =
  | { type: "start"; path: string }
  | { type: "success"; path: string; data: T }
  | { type: "error"; path: string; error: string };

function jsonReducer<T>(state: JsonState<T>, action: JsonAction<T>): JsonState<T> {
  switch (action.type) {
    case "start":
      return {
        data: action.path === state.path ? state.data : null,
        loading: true,
        error: null,
        path: action.path,
      };
    case "success":
      if (action.path !== state.path) {
        return state;
      }
      return { data: action.data, loading: false, error: null, path: action.path };
    case "error":
      if (action.path !== state.path) {
        return state;
      }
      return { data: null, loading: false, error: action.error, path: action.path };
    default:
      return state;
  }
}

export function useJsonData<T>(path: string | null): {
  data: T | null;
  loading: boolean;
  error: string | null;
} {
  const [state, dispatch] = useReducer(jsonReducer<T>, {
    data: null,
    loading: false,
    error: null,
    path: null,
  });

  useEffect(() => {
    if (!path) {
      return;
    }

    const controller = new AbortController();
    dispatch({ type: "start", path });

    fetch(`/lyc-racing-data/data/${path}`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load ${path}`);
        return res.json();
      })
      .then((json) => {
        dispatch({ type: "success", path, data: json as T });
      })
      .catch((err) => {
        if (controller.signal.aborted) {
          return;
        }
        dispatch({
          type: "error",
          path,
          error: err instanceof Error ? err.message : String(err),
        });
      });

    return () => {
      controller.abort();
    };
  }, [path]);

  if (!path) {
    return { data: null, loading: false, error: null };
  }

  return { data: state.data, loading: state.loading, error: state.error };
}

/** Read the hash from the URL (e.g. #42 → "42") */
export function useHashParam(): string | null {
  const [hash, setHash] = useState<string | null>(null);

  const update = useCallback(() => {
    const h = typeof window !== "undefined" ? window.location.hash.slice(1) : "";
    setHash(h || null);
  }, []);

  useEffect(() => {
    // Read initial hash on mount (after hydration)
    update();
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, [update]);

  return hash;
}
