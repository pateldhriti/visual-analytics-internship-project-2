import { motion, useInView } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import useSpotlight from "../hooks/useSpotlight.js";

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

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09 } },
};

const item = {
  hidden: { opacity: 0, y: 16, scale: 0.96 },
  show: { opacity: 1, y: 0, scale: 1, transition: { type: "spring", stiffness: 260, damping: 22 } },
};

function useCountUp(target, format, started) {
  const [value, setValue] = useState(0);
  const frameRef = useRef();

  useEffect(() => {
    if (!started) return;
    const duration = 1000;
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
  const spotlight = useSpotlight();

  return (
    <motion.div
      className={`kpi-stat ${spotlight.className}`}
      onMouseMove={spotlight.onMouseMove}
      variants={item}
      whileHover={{ y: -4 }}
    >
      <span className="kpi-stat-value">{display}</span>
      <span className="kpi-stat-label">{label}</span>
    </motion.div>
  );
}

export default function KpiStrip() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, amount: 0.3 });

  return (
    <motion.section
      className="kpi-strip"
      ref={ref}
      variants={container}
      initial="hidden"
      animate={inView ? "show" : "hidden"}
    >
      {KPIS.map((kpi) => (
        <KpiStat key={kpi.label} {...kpi} started={inView} />
      ))}
    </motion.section>
  );
}
