"use client";

import { useState, useEffect, useCallback } from "react";

export function useJsonData<T>(path: string | null): {
  data: T | null;
  loading: boolean;
  error: string | null;
} {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!path) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    fetch(`/lyc-racing-data/data/${path}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to load ${path}`);
        return res.json();
      })
      .then((json) => setData(json as T))
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, [path]);

  return { data, loading, error };
}

/** Read the hash from the URL (e.g. #42 → "42") */
export function useHashParam(): string | null {
  const [hash, setHash] = useState<string | null>(null);

  const update = useCallback(() => {
    const h = typeof window !== "undefined" ? window.location.hash.slice(1) : "";
    setHash(h || null);
  }, []);

  useEffect(() => {
    update();
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, [update]);

  return hash;
}
