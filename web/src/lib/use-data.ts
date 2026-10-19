"use client";

import { useEffect, useReducer, useSyncExternalStore } from "react";

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

function subscribeToHash(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  window.addEventListener("popstate", onChange);
  return () => {
    window.removeEventListener("hashchange", onChange);
    window.removeEventListener("popstate", onChange);
  };
}

function getHashSnapshot(): string | null {
  return window.location.hash.slice(1) || null;
}

function getServerHashSnapshot(): string | null {
  return null;
}

/** Read the hash from the URL (e.g. #42 → "42"). Null during SSR/hydration. */
export function useHashParam(): string | null {
  return useSyncExternalStore(subscribeToHash, getHashSnapshot, getServerHashSnapshot);
}

/**
 * Read a numeric id from the URL hash (e.g. #42 → "42"). Anything else
 * (e.g. a crafted "#../overview") is ignored so it never reaches a fetch path.
 */
export function useNumericHashParam(): string | null {
  const hash = useHashParam();
  return hash && /^\d+$/.test(hash) ? hash : null;
}
