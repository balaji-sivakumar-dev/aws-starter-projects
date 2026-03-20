export default function ProviderSelector({ providers, selected, onSelect }) {
  if (!providers.length) return null;

  return (
    <div className="provider-selector">
      <label className="provider-label">AI Provider</label>
      <div className="provider-options">
        {providers.map((p) => (
          <button
            key={p.name}
            className={`provider-btn${selected === p.name ? " active" : ""}`}
            onClick={() => onSelect(p.name)}
            title={`${p.label} — ${p.model}`}
          >
            <span className="provider-name">{p.label}</span>
            <span className="provider-model">{p.model}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
