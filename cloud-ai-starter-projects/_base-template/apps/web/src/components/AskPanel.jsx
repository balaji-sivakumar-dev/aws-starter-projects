import { useEffect, useState } from "react";
import { askData, clearIndex, deleteConversation, listConversations, searchData, embedAllEntries, ragStatus } from "../api/rag";

export default function AskPanel({ providerName }) {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("ask"); // "ask" or "search"
  const [status, setStatus] = useState(null);
  const [indexing, setIndexing] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  async function loadStatus() {
    try {
      const s = await ragStatus();
      setStatus(s);
    } catch {
      setStatus({ totalVectors: 0, error: "RAG not configured" });
    }
  }

  async function loadHistory() {
    try {
      const resp = await listConversations();
      const stored = (resp.items || []).reverse(); // oldest first
      const historyMessages = [];
      for (const conv of stored) {
        historyMessages.push({ role: "user", content: conv.question, convId: conv.convId });
        historyMessages.push({
          role: "assistant",
          content: conv.answer,
          sources: conv.sources || [],
          provider: conv.provider || "",
          convId: conv.convId,
        });
      }
      setMessages(historyMessages);
    } catch {
      // History not available — start fresh
    }
    setHistoryLoaded(true);
  }

  async function handleDeleteConversation(convId) {
    try {
      await deleteConversation(convId);
      setMessages((prev) => prev.filter((m) => m.convId !== convId));
    } catch {
      // Non-critical — ignore
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userQuery = query.trim();
    setQuery("");
    setMessages((prev) => [...prev, { role: "user", content: userQuery }]);
    setLoading(true);

    try {
      if (mode === "ask") {
        const result = await askData(userQuery, 5, providerName || null);
        // Reload history to get the persisted convId for the new exchange
        const histResp = await listConversations().catch(() => ({ items: [] }));
        const newest = (histResp.items || [])[0]; // newest is first (ScanIndexForward=false)
        const convId = newest?.question === userQuery ? newest.convId : undefined;
        setMessages((prev) => [
          // Attach convId to the user message that was just added
          ...prev.slice(0, -1),
          { ...prev[prev.length - 1], convId },
          {
            role: "assistant",
            content: result.answer,
            sources: result.sources || [],
            provider: result.provider || "",
            convId,
          },
        ]);
      } else {
        const result = await searchData(userQuery);
        setMessages((prev) => [
          ...prev,
          {
            role: "search",
            content: `Found ${result.results.length} matching entries`,
            sources: result.results || [],
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: err.message || "Something went wrong" },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleClearIndex() {
    if (!window.confirm("Remove all your indexed entries from the search index? You can re-index any time.")) return;
    setClearing(true);
    try {
      await clearIndex();
      setMessages((prev) => [
        ...prev,
        { role: "system", content: "All indexed entries removed. Click \"Index all entries\" to re-index." },
      ]);
      loadStatus();
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: `Clear index failed: ${err.message}` },
      ]);
    } finally {
      setClearing(false);
    }
  }

  async function handleEmbedAll() {
    setIndexing(true);
    try {
      const result = await embedAllEntries();
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: `Indexed ${result.embedded} of ${result.totalEntries} entries.${
            result.failed ? ` (${result.failed} failed)` : ""
          }`,
        },
      ]);
      loadStatus();
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: `Indexing failed: ${err.message}` },
      ]);
    } finally {
      setIndexing(false);
    }
  }

  // Load status and history on first render
  useEffect(() => {
    loadStatus();
    loadHistory();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="ask-container">
      <div className="ask-header">
        <h2>Ask Your Data</h2>
        <p className="ask-subtitle">
          Ask questions about your items using semantic search + AI
        </p>
        <div className="ask-controls">
          <div className="ask-mode-toggle">
            <button
              className={`mode-btn${mode === "ask" ? " active" : ""}`}
              onClick={() => setMode("ask")}
            >
              Conversational
            </button>
            <button
              className={`mode-btn${mode === "search" ? " active" : ""}`}
              onClick={() => setMode("search")}
            >
              Search only
            </button>
          </div>
          <div className="ask-status">
            {status && (
              <span className="status-badge">
                {status.totalVectors || 0} entries indexed
              </span>
            )}
            <button
              className="btn-index"
              onClick={handleEmbedAll}
              disabled={indexing || clearing}
            >
              {indexing ? "Indexing..." : "Index all entries"}
            </button>
            <button
              className="btn-clear-index"
              onClick={handleClearIndex}
              disabled={indexing || clearing}
              title="Remove all your indexed data from the search index"
            >
              {clearing ? "Clearing..." : "Clear index"}
            </button>
          </div>
        </div>
      </div>

      <div className="ask-messages">
        {historyLoaded && messages.length > 0 && (
          <div className="ask-history-header">
            <span className="ask-history-label">Conversation history</span>
            <button
              className="btn-clear-history"
              onClick={async () => {
                const convIds = [...new Set(messages.filter((m) => m.convId).map((m) => m.convId))];
                for (const id of convIds) await handleDeleteConversation(id);
              }}
            >
              Clear history
            </button>
          </div>
        )}
        {messages.length === 0 && (
          <div className="ask-empty">
            <p>Try asking something like:</p>
            <div className="ask-suggestions">
              {[
                "What was I stressed about recently?",
                "Find entries about career goals",
                "What recurring themes appear in my writing?",
                "When did I last feel really happy?",
              ].map((s) => (
                <button
                  key={s}
                  className="suggestion-chip"
                  onClick={() => { setQuery(s); }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`ask-message ask-message-${msg.role}`}>
            {msg.role === "user" && (
              <div className="msg-bubble msg-user">{msg.content}</div>
            )}
            {msg.role === "assistant" && (
              <div className="msg-bubble msg-assistant">
                <div className="msg-answer">{msg.content}</div>
                {msg.provider && (
                  <div className="msg-provider-badge">via {msg.provider}</div>
                )}
                {msg.sources?.length > 0 && (
                  <div className="msg-sources">
                    <span className="sources-label">Sources:</span>
                    {msg.sources.map((src, j) => (
                      <span key={j} className="source-tag" title={src.snippet}>
                        {src.createdAt?.slice(0, 10)} — {src.title}
                        <span className="source-score">
                          {Math.round(src.score * 100)}%
                        </span>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
            {msg.role === "search" && (
              <div className="msg-bubble msg-search">
                <div className="msg-answer">{msg.content}</div>
                {msg.sources?.map((src, j) => (
                  <div key={j} className="search-result">
                    <div className="search-result-title">
                      {src.createdAt?.slice(0, 10)} — {src.title}
                      <span className="source-score">
                        {Math.round(src.score * 100)}%
                      </span>
                    </div>
                    <div className="search-result-snippet">{src.snippet}</div>
                  </div>
                ))}
              </div>
            )}
            {msg.role === "system" && (
              <div className="msg-bubble msg-system">{msg.content}</div>
            )}
            {msg.role === "error" && (
              <div className="msg-bubble msg-error">{msg.content}</div>
            )}
          </div>
        ))}

        {loading && (
          <div className="ask-message ask-message-loading">
            <div className="msg-bubble msg-assistant">
              <span className="loading-dots">Thinking...</span>
            </div>
          </div>
        )}
      </div>

      <form className="ask-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          className="ask-input"
          placeholder={
            mode === "ask"
              ? "Ask a question about your data..."
              : "Search your items..."
          }
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn-ask" disabled={loading || !query.trim()}>
          {mode === "ask" ? "Ask" : "Search"}
        </button>
      </form>
    </div>
  );
}
