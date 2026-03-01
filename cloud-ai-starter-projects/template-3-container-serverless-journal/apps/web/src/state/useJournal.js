import { useCallback, useState } from "react";

import { createEntry, deleteEntry, getEntry, getMe, listEntries, triggerAi, updateEntry } from "../api/entries";

export function useJournal() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [me, setMe] = useState(null);
  const [entries, setEntries] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [selected, setSelected] = useState(null);
  const [nextToken, setNextToken] = useState(null);
  const [mode, setMode] = useState("detail");

  const bootstrap = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [meResp, listResp] = await Promise.all([getMe(), listEntries()]);
      setMe(meResp);
      setEntries(listResp.items || []);
      setNextToken(listResp.nextToken || null);
      if ((listResp.items || []).length > 0) {
        setSelectedId(listResp.items[0].entryId);
        setSelected(listResp.items[0]);
      }
    } catch (err) {
      setError(err.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  const select = useCallback(async (entryId) => {
    setLoading(true);
    setError("");
    try {
      const resp = await getEntry(entryId);
      setSelectedId(entryId);
      setSelected(resp.item);
      setMode("detail");
    } catch (err) {
      setError(err.message || "Failed to load entry");
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!selectedId) return;
    await select(selectedId);
  }, [select, selectedId]);

  const more = useCallback(async () => {
    if (!nextToken) return;
    setLoading(true);
    setError("");
    try {
      const resp = await listEntries(nextToken);
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
      setEntries((prev) => [resp.item, ...prev]);
      setSelectedId(resp.item.entryId);
      setSelected(resp.item);
      setMode("detail");
    } catch (err) {
      setError(err.message || "Create failed");
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
      setSelected(resp.item);
      setEntries((prev) => prev.map((e) => (e.entryId === selectedId ? resp.item : e)));
      setMode("detail");
    } catch (err) {
      setError(err.message || "Update failed");
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  const remove = useCallback(async (entryId) => {
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
      setError(err.message || "Delete failed");
    } finally {
      setLoading(false);
    }
  }, [entries, selectedId]);

  const queueAi = useCallback(async () => {
    if (!selectedId) return;
    setLoading(true);
    setError("");
    try {
      await triggerAi(selectedId);
      await refresh();
    } catch (err) {
      setError(err.message || "AI trigger failed");
    } finally {
      setLoading(false);
    }
  }, [refresh, selectedId]);

  return {
    loading,
    error,
    me,
    entries,
    selectedId,
    selected,
    nextToken,
    mode,
    setMode,
    bootstrap,
    select,
    refresh,
    more,
    saveCreate,
    saveEdit,
    remove,
    queueAi,
  };
}
