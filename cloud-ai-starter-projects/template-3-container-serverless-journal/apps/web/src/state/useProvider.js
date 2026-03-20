import { useState, useEffect, useCallback } from "react";
import { getProviders } from "../api/config";

const STORAGE_KEY = "reflect-llm-provider";

export function useProvider() {
  const [providers, setProviders] = useState([]);
  const [selected, setSelected] = useState(
    () => localStorage.getItem(STORAGE_KEY) || ""
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getProviders();
        if (cancelled) return;
        setProviders(data.providers || []);
        // If nothing stored yet, use server default
        if (!localStorage.getItem(STORAGE_KEY) && data.default) {
          setSelected(data.default);
        }
      } catch {
        // Config endpoint may not be available (e.g. older backend)
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const select = useCallback((name) => {
    setSelected(name);
    localStorage.setItem(STORAGE_KEY, name);
  }, []);

  return { providers, selected, select, loading };
}
