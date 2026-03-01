import { useCallback, useMemo, useState } from "react";

import { getIdProfile, isAuthenticated, loginWithHostedUi, logout } from "../auth/auth";
import { createEntry, deleteEntry, enqueueAi, getEntry, getMe, listEntries, updateEntry } from "../api/entries";

export function useJournalApp() {
  const [authReady, setAuthReady] = useState(isAuthenticated());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [me, setMe] = useState(null);
  const [entries, setEntries] = useState([]);
  const [selectedEntryId, setSelectedEntryId] = useState("");
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [nextToken, setNextToken] = useState(null);

  const [mode, setMode] = useState("detail");

  const idProfile = useMemo(() => getIdProfile(), [authReady]);

  const loadInitial = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [meResp, listResp] = await Promise.all([getMe(), listEntries({ limit: 20 })]);
      setMe(meResp);
      const items = listResp.items || [];
      setEntries(items);
      setNextToken(listResp.nextToken || null);
      if (items.length > 0) {
        setSelectedEntryId(items[0].entryId);
        setSelectedEntry(items[0]);
      }
      setAuthReady(true);
    } catch (err) {
      setError(err.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshSelected = useCallback(async () => {
    if (!selectedEntryId) return;
    setLoading(true);
    setError("");
    try {
      const resp = await getEntry(selectedEntryId);
      setSelectedEntry(resp.item);
      setEntries((prev) => prev.map((e) => (e.entryId === selectedEntryId ? resp.item : e)));
    } catch (err) {
      setError(err.message || "Failed to load entry");
    } finally {
      setLoading(false);
    }
  }, [selectedEntryId]);

  const selectEntry = useCallback(async (entryId) => {
    setSelectedEntryId(entryId);
    setMode("detail");
    setLoading(true);
    setError("");
    try {
      const resp = await getEntry(entryId);
      setSelectedEntry(resp.item);
    } catch (err) {
      setError(err.message || "Failed to load entry");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMore = useCallback(async () => {
    if (!nextToken) return;
    setLoading(true);
    setError("");
    try {
      const resp = await listEntries({ nextToken, limit: 20 });
      setEntries((prev) => [...prev, ...(resp.items || [])]);
      setNextToken(resp.nextToken || null);
    } catch (err) {
      setError(err.message || "Failed to load more entries");
    } finally {
      setLoading(false);
    }
  }, [nextToken]);

  const saveCreate = useCallback(async (payload) => {
    setLoading(true);
    setError("");
    try {
      const resp = await createEntry(payload);
      const created = resp.item;
      setEntries((prev) => [created, ...prev]);
      setSelectedEntryId(created.entryId);
      setSelectedEntry(created);
      setMode("detail");
    } catch (err) {
      setError(err.message || "Failed to create entry");
    } finally {
      setLoading(false);
    }
  }, []);

  const saveEdit = useCallback(async (payload) => {
    if (!selectedEntryId) return;
    setLoading(true);
    setError("");
    try {
      const resp = await updateEntry(selectedEntryId, payload);
      const updated = resp.item;
      setSelectedEntry(updated);
      setEntries((prev) => prev.map((e) => (e.entryId === selectedEntryId ? updated : e)));
      setMode("detail");
    } catch (err) {
      setError(err.message || "Failed to update entry");
    } finally {
      setLoading(false);
    }
  }, [selectedEntryId]);

  const removeEntry = useCallback(async (entryId) => {
    setLoading(true);
    setError("");
    try {
      await deleteEntry(entryId);
      const remaining = entries.filter((e) => e.entryId !== entryId);
      setEntries(remaining);
      if (selectedEntryId === entryId) {
        if (remaining.length) {
          setSelectedEntryId(remaining[0].entryId);
          setSelectedEntry(remaining[0]);
        } else {
          setSelectedEntryId("");
          setSelectedEntry(null);
        }
      }
    } catch (err) {
      setError(err.message || "Failed to delete entry");
    } finally {
      setLoading(false);
    }
  }, [entries, selectedEntryId]);

  const triggerAi = useCallback(async () => {
    if (!selectedEntryId) return;
    setLoading(true);
    setError("");
    try {
      await enqueueAi(selectedEntryId);
      await refreshSelected();
    } catch (err) {
      setError(err.message || "Failed to trigger AI");
    } finally {
      setLoading(false);
    }
  }, [refreshSelected, selectedEntryId]);

  return {
    authReady,
    loading,
    error,
    me,
    idProfile,
    entries,
    selectedEntry,
    selectedEntryId,
    nextToken,
    mode,
    setMode,
    setAuthReady,
    loadInitial,
    loginWithHostedUi,
    logout,
    selectEntry,
    refreshSelected,
    loadMore,
    saveCreate,
    saveEdit,
    removeEntry,
    triggerAi,
  };
}
