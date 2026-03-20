import { useMemo, useState } from "react";

function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch { return iso.slice(0, 10); }
}

function aiClass(status) {
  if (status === "DONE") return "ai-done";
  if (status === "PROCESSING") return "ai-processing";
  if (status === "ERROR") return "ai-error";
  return "ai-none";
}

const MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function getYearsAndMonths(items) {
  const map = {}; // { year: Set<month 0-based> }
  for (const item of items) {
    if (!item.createdAt) continue;
    const d = new Date(item.createdAt);
    const y = d.getFullYear();
    if (!map[y]) map[y] = new Set();
    map[y].add(d.getMonth());
  }
  // Sort years descending
  return Object.entries(map)
    .sort(([a], [b]) => Number(b) - Number(a))
    .map(([year, months]) => ({
      year: Number(year),
      months: [...months].sort((a, b) => b - a), // most recent first
    }));
}

export default function EntryList({
  items, loading, selectedId, onSelect, onDelete, nextToken, onMore,
  totalCount, checkedIds, onToggleCheck, onCheckAll, onClearChecked, onDeleteMany,
}) {
  const [filterYear, setFilterYear] = useState(null);
  const [filterMonth, setFilterMonth] = useState(null);
  const [manageMode, setManageMode] = useState(false);

  const yearMonths = useMemo(() => getYearsAndMonths(items), [items]);

  const filtered = useMemo(() => {
    if (filterYear === null) return items;
    return items.filter((item) => {
      if (!item.createdAt) return false;
      const d = new Date(item.createdAt);
      if (d.getFullYear() !== filterYear) return false;
      if (filterMonth !== null && d.getMonth() !== filterMonth) return false;
      return true;
    });
  }, [items, filterYear, filterMonth]);

  function handleYearClick(year) {
    if (filterYear === year) {
      // Deselect → show all
      setFilterYear(null);
      setFilterMonth(null);
    } else {
      setFilterYear(year);
      setFilterMonth(null);
    }
  }

  function handleMonthClick(month) {
    setFilterMonth(filterMonth === month ? null : month);
  }

  if (loading && !items.length) {
    return <div className="entry-list-empty">Loading…</div>;
  }
  if (!items.length) {
    return <div className="entry-list-empty">No entries yet.<br />Click "+ New" to write your first entry.</div>;
  }

  const allFilteredIds = filtered.map((i) => i.entryId);
  const allChecked = allFilteredIds.length > 0 && allFilteredIds.every((id) => checkedIds?.has(id));

  function toggleManage() {
    setManageMode((m) => {
      if (m && onClearChecked) onClearChecked();
      return !m;
    });
  }

  function handleSelectAll() {
    if (allChecked) {
      if (onClearChecked) onClearChecked();
    } else {
      if (onCheckAll) onCheckAll(allFilteredIds);
    }
  }

  const checkedCount = checkedIds ? checkedIds.size : 0;

  return (
    <div className="entry-list-root">
      {/* ── Manage toolbar ── */}
      <div className="entry-manage-bar">
        {totalCount !== null && (
          <span className="entry-total-count">{totalCount} total</span>
        )}
        <button
          className={`btn-manage${manageMode ? " active" : ""}`}
          onClick={toggleManage}
          title={manageMode ? "Exit manage mode" : "Manage entries"}
        >
          {manageMode ? "Done" : "Manage"}
        </button>
      </div>

      {manageMode && (
        <div className="entry-bulk-bar">
          <label className="bulk-select-all">
            <input
              type="checkbox"
              checked={allChecked}
              onChange={handleSelectAll}
            />
            {allChecked ? "Deselect all" : "Select all"}
          </label>
          <button
            className="btn-bulk-delete"
            disabled={loading || checkedCount === 0}
            onClick={() => checkedCount > 0 && onDeleteMany && onDeleteMany([...checkedIds])}
          >
            {checkedCount > 0 ? `Delete ${checkedCount}` : "Delete selected"}
          </button>
        </div>
      )}

      {/* ── Filters ── */}
      {yearMonths.length > 0 && (
        <div className="entry-filters">
          {yearMonths.map(({ year, months }) => (
            <div key={year} className="filter-year-group">
              <button
                className={`filter-year-btn${filterYear === year ? " active" : ""}`}
                onClick={() => handleYearClick(year)}
              >
                {year}
                <span className="filter-year-count">
                  {items.filter(i => i.createdAt && new Date(i.createdAt).getFullYear() === year).length}
                </span>
              </button>
              {filterYear === year && (
                <div className="filter-month-row">
                  {months.map((m) => (
                    <button
                      key={m}
                      className={`filter-month-btn${filterMonth === m ? " active" : ""}`}
                      onClick={() => handleMonthClick(m)}
                    >
                      {MONTH_NAMES[m]}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          {filterYear !== null && (
            <button className="filter-clear-btn" onClick={() => { setFilterYear(null); setFilterMonth(null); }}>
              Clear filter
            </button>
          )}
        </div>
      )}

      {/* ── Entry list ── */}
      <div className="entry-list-scroll">
        {filtered.length === 0 && (
          <div className="entry-list-empty">No entries for this period.</div>
        )}
        {filtered.map((item) => {
          const isChecked = checkedIds?.has(item.entryId) ?? false;
          return (
            <div
              key={item.entryId}
              className={`entry-item${item.entryId === selectedId && !manageMode ? " selected" : ""}${manageMode && isChecked ? " checked" : ""}${manageMode ? " manage-row" : ""}`}
              onClick={manageMode ? () => onToggleCheck && onToggleCheck(item.entryId) : undefined}
            >
              {manageMode && (
                <input
                  type="checkbox"
                  className="entry-item-checkbox"
                  checked={isChecked}
                  onChange={() => onToggleCheck && onToggleCheck(item.entryId)}
                  onClick={(e) => e.stopPropagation()}
                />
              )}
              <button
                className={`entry-item-btn${manageMode ? " manage-mode-btn" : ""}`}
                onClick={manageMode
                  ? (e) => { e.stopPropagation(); onToggleCheck && onToggleCheck(item.entryId); }
                  : () => onSelect(item.entryId)
                }
                tabIndex={manageMode ? -1 : 0}
              >
                <span className="entry-item-title">{item.title}</span>
                <span className="entry-item-meta">
                  <span className="entry-item-date">{formatDate(item.createdAt)}</span>
                  {item.aiStatus && item.aiStatus !== "PENDING" && (
                    <span className={`entry-item-ai ${aiClass(item.aiStatus)}`}>{item.aiStatus}</span>
                  )}
                </span>
              </button>
              {!manageMode && (
                <button className="entry-item-delete" title="Delete entry" onClick={(e) => { e.stopPropagation(); onDelete(item.entryId); }}>✕</button>
              )}
            </div>
          );
        })}
        {nextToken && (
          <button className="btn-load-more" onClick={onMore}>Load more…</button>
        )}
      </div>
    </div>
  );
}
