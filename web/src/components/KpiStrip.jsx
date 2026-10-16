import { useEffect, useRef, useState } from "react";

// Real, verified numbers only -- see docs/story1_questions_and_measures.md
// (burden figures), the Census Profile extraction (population), and the
// project proposal's own cited apartment vacancy rate / rent figures
// (section 2.1), independently re-confirmed against
// warehouse.fact_rental_market this session. No invented or placeholder
// values.
const KPIS = [
  { label: "Windsor CMA population (2021)", value: 422630, format: "number" },
  { label: "Owner households spending 30%+ on shelter", value: 10.9, format: "percent" },
  { label: "Renter households spending 30%+ on shelter", value: 34.5, format: "percent" },
  { label: "Apartment vacancy rate (Oct-25)", value: 3.7, format: "percent" },
];

function useCountUp(target, format, started) {
  const [value, setValue] = useState(0);
  const frameRef = useRef();

  useEffect(() => {
    if (!started) return;
    const duration = 900;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(target * eased);
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(tick);
      }
    }

    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target, started]);

  if (format === "percent") return `${value.toFixed(1)}%`;
  return Math.round(value).toLocaleString("en-CA");
}

function KpiStat({ label, value, format, started }) {
  const display = useCountUp(value, format, started);
  return (
    <div className="kpi-stat">
      <span className="kpi-stat-value">{display}</span>
      <span className="kpi-stat-label">{label}</span>
    </div>
  );
}

export default function KpiStrip() {
  const [started, setStarted] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setStarted(true);
          observer.disconnect();
        }
      },
      { threshold: 0.3 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <section className="kpi-strip" ref={ref}>
      {KPIS.map((kpi) => (
        <KpiStat key={kpi.label} {...kpi} started={started} />
      ))}
    </section>
  );
}
