function Bar({ label, value, tone }) {
  return (
    <div className="bar-row">
      <span className="bar-label">{label}</span>
      <div className="bar">
        <div className={`bar-fill ${tone}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
      <span className="bar-value">{value}%</span>
    </div>
  );
}

function Chips({ items, tone, empty, render }) {
  if (items.length === 0) return <p className="muted">{empty}</p>;
  return (
    <div className="chips">
      {items.map((s) => (
        <span key={s.skill_id ?? s} className={`chip ${tone}`}>
          {render ? render(s) : s.name}
          {s.required === false && <small> (nice to have)</small>}
        </span>
      ))}
    </div>
  );
}

export default function Results({ data }) {
  return (
    <section className="card results">
      <h2>Your fit</h2>
      <div className="score">
        <div className="score-number">
          {data.score}
          <span>%</span>
        </div>
        <div className="bars">
          <Bar label="With related skills" value={data.score} tone="main" />
          <Bar label="Exact matches only" value={data.exact_score} tone="base" />
        </div>
      </div>

      <h3>You already have</h3>
      <Chips items={data.matched} tone="good" empty="No exact matches yet." />

      <h3>Close, but not exact</h3>
      <Chips
        items={data.near}
        tone="warn"
        empty="Nothing here."
        render={(s) => (
          <>
            {s.name} <small>{Math.round(s.credit * 100)}% credit from {s.via}</small>
          </>
        )}
      />

      <h3>Missing</h3>
      <Chips items={data.missing} tone="bad" empty="Nothing missing. Nice!" />

      <h3>Suggested learning order</h3>
      {data.path.length === 0 ? (
        <p className="muted">Nothing to learn for this job.</p>
      ) : (
        <ol className="path">
          {data.path.map((s) => (
            <li key={s.skill_id}>
              <strong>{s.name}</strong> <span className={`badge ${s.priority}`}>{s.priority}</span>
              <div className="muted">
                {s.reason}
                {s.depends_on.length > 0 && ` - builds on ${s.depends_on.join(", ")}`}
              </div>
            </li>
          ))}
        </ol>
      )}

      <details>
        <summary>Other skills on your resume ({data.extra.length})</summary>
        <Chips items={data.extra} tone="neutral" empty="None." render={(s) => s} />
      </details>
    </section>
  );
}
