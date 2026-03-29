export default function ProviderSelector({ providers, selected, onSelect }) {
  if (!providers.length) return null;

  return (
    <div className="provider-selector">
      <label className="provider-label" htmlFor="provider-select">AI</label>
      <select
        id="provider-select"
        className="provider-select"
        value={selected}
        onChange={(e) => onSelect(e.target.value)}
      >
        {providers.map((p) => (
          <option key={p.name} value={p.name}>
            {p.label}
          </option>
        ))}
      </select>
    </div>
  );
}
