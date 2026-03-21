import { useCallback, useState } from "react";

import { bulkDeleteEntries, countEntries, createEntry, deleteEntry, getEntry, getMe, listEntries, triggerAi, updateEntry } from "../api/entries";

export function useJournal(providerName) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [me, setMe] = useState(null);
  const [entries, setEntries] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [selected, setSelected] = useState(null);
  const [nextToken, setNextToken] = useState(null);
  const [mode, setMode] = useState("detail");
  const [totalCount, setTotalCount] = useState(null);
  const [checkedIds, setCheckedIds] = useState(new Set());

  const bootstrap = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [meResp, listResp, countResp] = await Promise.all([getMe(), listEntries(), countEntries()]);
      setMe(meResp);
      setEntries(listResp.items || []);
      setNextToken(listResp.nextToken || null);
      setTotalCount(countResp.count ?? null);
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
      setTotalCount((c) => (c !== null ? c - 1 : null));
      setCheckedIds((prev) => { const next = new Set(prev); next.delete(entryId); return next; });
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

  const removeMany = useCallback(async (entryIds) => {
    if (!entryIds.length) return;
    setLoading(true);
    setError("");
    try {
      const resp = await bulkDeleteEntries(entryIds);
      const deletedSet = new Set(entryIds);
      const remaining = entries.filter((e) => !deletedSet.has(e.entryId));
      setEntries(remaining);
      setTotalCount((c) => (c !== null ? c - resp.deleted : null));
      setCheckedIds(new Set());
      if (deletedSet.has(selectedId)) {
        const first = remaining[0] || null;
        setSelectedId(first ? first.entryId : "");
        setSelected(first);
      }
    } catch (err) {
      setError(err.message || "Bulk delete failed");
    } finally {
      setLoading(false);
    }
  }, [entries, selectedId]);

  const toggleCheck = useCallback((entryId) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      next.has(entryId) ? next.delete(entryId) : next.add(entryId);
      return next;
    });
  }, []);

  const checkAll = useCallback((ids) => {
    setCheckedIds(new Set(ids));
  }, []);

  const clearChecked = useCallback(() => {
    setCheckedIds(new Set());
  }, []);

  const queueAi = useCallback(async () => {
    if (!selectedId) return;
    setLoading(true);
    setError("");
    try {
      await triggerAi(selectedId, providerName || undefined);
      await refresh();
    } catch (err) {
      setError(err.message || "AI trigger failed");
    } finally {
      setLoading(false);
    }
  }, [refresh, selectedId, providerName]);

  return {
    loading,
    error,
    me,
    entries,
    selectedId,
    selected,
    nextToken,
    mode,
    totalCount,
    checkedIds,
    setMode,
    bootstrap,
    select,
    refresh,
    more,
    saveCreate,
    saveEdit,
    remove,
    removeMany,
    toggleCheck,
    checkAll,
    clearChecked,
    queueAi,
  };
}
