// Visual scope bar shown above each story's dashboard slot -- styled like
// the filter row in the reference mockup, but rendered as plain labeled
// chips rather than working <select> controls. There's no backend to
// filter against yet (the real per-story Superset dashboards aren't built),
// so this states each story's actual, fixed scope honestly instead of
// faking interactivity that does nothing.
export default function FilterBar({ filters }) {
  if (!filters?.length) return null;

  return (
    <div className="filter-bar" role="group" aria-label="Dataset scope">
      {filters.map((f) => (
        <div className="filter-chip" key={f.label}>
          <span className="filter-chip-label">{f.label}</span>
          <span className="filter-chip-value">{f.value}</span>
        </div>
      ))}
    </div>
  );
}
