import { useCallback, useState } from "react";

import { createEntry, deleteEntry, enqueueAi, getEntry, getMe, listEntries, updateEntry } from "../api/entries";

export function useJournalApp() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [me, setMe] = useState(null);
  const [entries, setEntries] = useState([]);
  const [nextToken, setNextToken] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [selected, setSelected] = useState(null);
  const [mode, setMode] = useState("detail");

  const bootstrap = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [meResp, listResp] = await Promise.all([getMe(), listEntries({ limit: 20 })]);
      setMe(meResp);
      setEntries(listResp.items || []);
      setNextToken(listResp.nextToken || null);

      const first = (listResp.items || [])[0];
      if (first) {
        setSelectedId(first.entryId);
        setSelected(first);
      }
    } catch (err) {
      setError(err.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  const selectEntry = useCallback(async (entryId) => {
    setMode("detail");
    setSelectedId(entryId);
    setLoading(true);
    setError("");
    try {
      const resp = await getEntry(entryId);
      setSelected(resp.item);
    } catch (err) {
      setError(err.message || "Failed to load entry");
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!selectedId) return;
    await selectEntry(selectedId);
  }, [selectEntry, selectedId]);

  const loadMore = useCallback(async () => {
    if (!nextToken) return;
    setLoading(true);
    setError("");
    try {
      const resp = await listEntries({ nextToken, limit: 20 });
      setEntries((prev) => [...prev, ...(resp.items || [])]);
      setNextToken(resp.nextToken || null);
    } catch (err) {
      setError(err.message || "Failed to load more");
    } finally {
      setLoading(false);
    }
  }, [nextToken]);

  const saveCreate = useCallback(async (payload) => {
    setLoading(true);
    setError("");
    try {
      const resp = await createEntry(payload);
      const item = resp.item;
      setEntries((prev) => [item, ...prev]);
      setSelectedId(item.entryId);
      setSelected(item);
      setMode("detail");
    } catch (err) {
      setError(err.message || "Failed to create");
    } finally {
      setLoading(false);
    }
  }, []);

  const saveEdit = useCallback(async (payload) => {
    if (!selectedId) return;
    setLoading(true);
    setError("");
    try {
      const resp = await updateEntry(selectedId, payload);
      const item = resp.item;
      setSelected(item);
      setEntries((prev) => prev.map((x) => (x.entryId === selectedId ? item : x)));
      setMode("detail");
    } catch (err) {
      setError(err.message || "Failed to update");
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  const removeEntry = useCallback(async (entryId) => {
    setLoading(true);
    setError("");
    try {
      await deleteEntry(entryId);
      const remaining = entries.filter((e) => e.entryId !== entryId);
      setEntries(remaining);
      if (entryId === selectedId) {
        const first = remaining[0] || null;
        setSelectedId(first ? first.entryId : "");
        setSelected(first);
      }
    } catch (err) {
      setError(err.message || "Failed to delete");
    } finally {
      setLoading(false);
    }
  }, [entries, selectedId]);

  const triggerAi = useCallback(async () => {
    if (!selectedId) return;
    setLoading(true);
    setError("");
    try {
      await enqueueAi(selectedId);
      await refresh();
    } catch (err) {
      setError(err.message || "Failed to trigger AI");
    } finally {
      setLoading(false);
    }
  }, [refresh, selectedId]);

  return {
    loading,
    error,
    me,
    entries,
    nextToken,
    selectedId,
    selected,
    mode,
    setMode,
    bootstrap,
    selectEntry,
    refresh,
    loadMore,
    saveCreate,
    saveEdit,
    removeEntry,
    triggerAi,
  };
}
