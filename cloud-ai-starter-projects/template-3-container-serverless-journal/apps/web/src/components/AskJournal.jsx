import { useState } from "react";
import { askJournal, searchJournal, embedAllEntries, ragStatus } from "../api/rag";

export default function AskJournal() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState("ask"); // "ask" or "search"
  const [status, setStatus] = useState(null);
  const [indexing, setIndexing] = useState(false);

  async function loadStatus() {
    try {
      const s = await ragStatus();
      setStatus(s);
    } catch {
      setStatus({ totalVectors: 0, error: "RAG not configured" });
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
        const result = await askJournal(userQuery);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: result.answer,
            sources: result.sources || [],
          },
        ]);
      } else {
        const result = await searchJournal(userQuery);
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

  // Load status on first render
  if (status === null) loadStatus();

  return (
    <div className="ask-container">
      <div className="ask-header">
        <h2>Ask Your Journal</h2>
        <p className="ask-subtitle">
          Ask questions about your journal entries using semantic search + AI
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
              disabled={indexing}
            >
              {indexing ? "Indexing..." : "Index all entries"}
            </button>
          </div>
        </div>
      </div>

      <div className="ask-messages">
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
              ? "Ask a question about your journal..."
              : "Search your journal entries..."
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
