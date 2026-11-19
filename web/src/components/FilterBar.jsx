// What the story's data covers (place, period, units), as one plain line of
// text. It used to be a row of chips, which looked like filters you could
// click; the real filters are inside the dashboard.
export default function FilterBar({ filters }) {
  if (!filters?.length) return null;

  return (
    <p className="scope-line">
      <span className="scope-line-title">About this data:</span>{" "}
      {filters.map((f, i) => (
        <span key={f.label}>
          {i > 0 && <span aria-hidden="true"> · </span>}
          <span className="scope-line-label">{f.label}</span> {f.value}
        </span>
      ))}
    </p>
  );
}
