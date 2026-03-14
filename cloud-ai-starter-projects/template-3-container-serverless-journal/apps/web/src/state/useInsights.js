import { useCallback, useState } from "react";
import {
  deleteSummary,
  generateSummary,
  listSummaries,
  regenerateSummary,
} from "../api/insights";

export function useInsights() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [summaries, setSummaries] = useState([]);
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await listSummaries();
      setSummaries(resp.items || []);
    } catch (err) {
      setError(err.message || "Failed to load summaries");
    } finally {
      setLoading(false);
    }
  }, []);

  const select = useCallback((summary) => {
    setSelected(summary);
  }, []);

  const generate = useCallback(async (payload) => {
    setLoading(true);
    setError("");
    try {
      const resp = await generateSummary(payload);
      setSummaries((prev) => [resp.item, ...prev]);
      setSelected(resp.item);
    } catch (err) {
      setError(err.message || "Failed to generate summary");
    } finally {
      setLoading(false);
    }
  }, []);

  const remove = useCallback(async (summaryId) => {
    setLoading(true);
    setError("");
    try {
      await deleteSummary(summaryId);
      setSummaries((prev) => prev.filter((s) => s.summaryId !== summaryId));
      if (selected?.summaryId === summaryId) setSelected(null);
    } catch (err) {
      setError(err.message || "Failed to delete summary");
    } finally {
      setLoading(false);
    }
  }, [selected]);

  const regenerate = useCallback(async (summaryId) => {
    setLoading(true);
    setError("");
    try {
      const resp = await regenerateSummary(summaryId);
      setSummaries((prev) =>
        prev.map((s) => (s.summaryId === summaryId ? resp.item : s))
      );
      setSelected(resp.item);
    } catch (err) {
      setError(err.message || "Failed to regenerate summary");
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    summaries,
    selected,
    load,
    select,
    generate,
    remove,
    regenerate,
  };
}
