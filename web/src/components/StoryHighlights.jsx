import { useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import data from "../data/highlights.json";
import { fadeUp, reveal } from "../lib/motion.js";

// "The story in four charts": the project's four strongest findings as the
// site's own charts, each linking to the dashboard tab that explores it.
// Every number comes from web/src/data/highlights.json, exported from the
// warehouse views by etl/export_site_highlights.py; the headline figures
// below are calculated from it, never typed in.

const fmtMoney = (n) => `$${Math.round(n).toLocaleString("en-CA")}`;
const fmtInt = (n) => Math.round(n).toLocaleString("en-CA");
const pct = (n, digits = 0) => `${n.toFixed(digits)}%`;
const abbreviate = (c) => ({ "Kitchener-Waterloo": "K-W", "St. Catharines": "St. Cath." })[c] ?? c;
const cagr = (from, to, years) => (Math.pow(to / from, 1 / years) - 1) * 100;

// --- layout helpers ---------------------------------------------------------

function useWidth() {
  const ref = useRef(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    observer.observe(el);
    setWidth(Math.floor(el.getBoundingClientRect().width));
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

const scale = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0)) * (r1 - r0);

// One tooltip per chart, shown for whichever mark is hovered or focused, so
// keyboard users get the same details as mouse users. It sits above the
// mark, or below it when the mark is near the top of the chart (the card
// would clip it). `side` places it beside a point instead, for the
// full-height year columns of the line chart.
const TIP_ROOM = 120;

function useTooltip(containerRef) {
  const [tip, setTip] = useState(null);
  const show = (target, content, side = null) => {
    const box = containerRef.current?.getBoundingClientRect();
    const mark = target.getBoundingClientRect();
    if (!box) return;
    const x = mark.left + mark.width / 2 - box.left;
    if (side) {
      const right = x < box.width / 2;
      setTip({
        content,
        style: { left: x + (right ? 14 : -14), top: side.y },
        place: right ? "right" : "left",
      });
      return;
    }
    const below = mark.top - box.top < TIP_ROOM;
    setTip({
      content,
      style: {
        left: Math.min(Math.max(x, 90), box.width - 90),
        top: below ? mark.bottom - box.top : mark.top - box.top,
      },
      place: below ? "below" : "above",
    });
  };
  const hide = () => setTip(null);
  const markProps = (content) => ({
    tabIndex: 0,
    role: "img",
    onMouseEnter: (e) => show(e.currentTarget, content),
    onFocus: (e) => show(e.currentTarget, content),
    onMouseLeave: hide,
    onBlur: hide,
  });
  const node = tip ? (
    <div className={`hl-tooltip hl-tooltip--${tip.place}`} role="status" style={tip.style}>
      {tip.content}
    </div>
  ) : null;
  return { show, hide, markProps, node };
}

function DataTable({ caption, head, rows }) {
  return (
    <details className="hl-data">
      <summary>Show the numbers</summary>
      <table>
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            {head.map((h) => (
              <th key={h} scope="col">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r[0]}>
              {r.map((c, i) => (i === 0 ? <th key={i}>{c}</th> : <td key={i}>{c}</td>))}
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

// --- 1. waffle: renters who cannot afford a 2-bedroom ---------------------

function AffordWaffle() {
  const a = data.affordability;
  const filled = Math.round(a.pct);
  const [ref, width] = useWidth();
  const tooltip = useTooltip(ref);
  const gap = 4;
  const cell = Math.max(14, Math.min(30, Math.floor((Math.min(width, 380) - gap * 9) / 10)));
  const size = cell * 10 + gap * 9;
  const short = { label: "Cannot afford it", count: a.cannot };
  const ok = { label: "Can afford it", count: a.renters - a.cannot };

  return (
    <div className="hl-chart" ref={ref}>
      {width > 0 && (
        <svg
          width={size}
          height={size}
          role="img"
          aria-label={`${filled} of every 100 Windsor renter households cannot afford an average 2-bedroom`}
        >
          {Array.from({ length: 100 }, (_, i) => {
            const isShort = i < filled;
            const group = isShort ? short : ok;
            return (
              <motion.rect
                key={i}
                x={(i % 10) * (cell + gap)}
                y={Math.floor(i / 10) * (cell + gap)}
                width={cell}
                height={cell}
                rx={4}
                className={isShort ? "hl-fill-windsor" : "hl-fill-empty"}
                initial={{ opacity: 0, scale: 0.4 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.008, duration: 0.25 }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }}
                {...tooltip.markProps(
                  <>
                    <strong>{group.label}</strong>
                    <br />
                    {fmtInt(group.count)} of {fmtInt(a.renters)} renter households
                  </>
                )}
                // One keyboard stop per group (its first square), not 100.
                {...(i === 0 || i === filled
                  ? { "aria-label": `${group.label}: ${fmtInt(group.count)} households` }
                  : { tabIndex: -1, role: undefined, "aria-hidden": true })}
              />
            );
          })}
        </svg>
      )}
      <ul className="hl-legend">
        <li>
          <span className="hl-swatch hl-fill-windsor" /> Cannot afford it ({fmtInt(a.cannot)})
        </li>
        <li>
          <span className="hl-swatch hl-fill-empty" /> Can afford it ({fmtInt(a.renters - a.cannot)}
          )
        </li>
      </ul>
      {tooltip.node}
    </div>
  );
}

// --- 2. scatter: rent against renter income ---------------------------------

function RentIncomeScatter() {
  const [ref, width] = useWidth();
  const tooltip = useTooltip(ref);
  const height = 330;
  const m = { top: 16, right: 24, bottom: 46, left: 60 };
  const x = scale(44000, 62000, m.left, width - m.right);
  const y = scale(1100, 1950, height - m.bottom, m.top);
  const line = (share) => [44000, 62000].map((inc) => [x(inc), y((share * inc) / 12)]);
  const [l30a, l30b] = line(0.3);
  const [l36a, l36b] = line(0.36);

  return (
    <div className="hl-chart hl-chart--wide" ref={ref}>
      {width > 0 && (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label="Two-bedroom rent against median renter income for five cities"
        >
          <polygon
            points={`${l30a[0]},${l30a[1]} ${l30b[0]},${l30b[1]} ${l30b[0]},${m.top} ${l30a[0]},${m.top}`}
            className="hl-zone"
          />
          {[1200, 1400, 1600, 1800].map((v) => (
            <g key={v}>
              <line x1={m.left} x2={width - m.right} y1={y(v)} y2={y(v)} className="hl-grid" />
              <text
                x={m.left - 8}
                y={y(v)}
                className="hl-axis"
                textAnchor="end"
                dominantBaseline="middle"
              >
                {fmtMoney(v)}
              </text>
            </g>
          ))}
          {[46000, 50000, 54000, 58000].map((v) => (
            <text
              key={v}
              x={x(v)}
              y={height - m.bottom + 20}
              className="hl-axis"
              textAnchor="middle"
            >
              ${v / 1000}k
            </text>
          ))}
          <text x={width - m.right} y={height - 6} className="hl-axis" textAnchor="end">
            Median renter household income (2020)
          </text>
          <line x1={l30a[0]} y1={l30a[1]} x2={l30b[0]} y2={l30b[1]} className="hl-ref" />
          <text
            x={x(60500)}
            y={y((0.3 * 60500) / 12)}
            dy={16}
            className="hl-ref-label"
            textAnchor="end"
            transform={`rotate(${(Math.atan2(l30b[1] - l30a[1], l30b[0] - l30a[0]) * 180) / Math.PI} ${x(60500)} ${y((0.3 * 60500) / 12)})`}
          >
            Rent = 30% of income (affordable)
          </text>
          <line
            x1={l36a[0]}
            y1={l36a[1]}
            x2={l36b[0]}
            y2={l36b[1]}
            className="hl-ref hl-ref--soft"
          />
          <text
            x={l36b[0] - 4}
            y={l36b[1] - 8}
            className="hl-ref-label hl-ref-label--soft"
            textAnchor="end"
          >
            36% of income
          </text>
          {data.cities.map((c, i) => {
            const cx = x(c.income);
            const cy = y(c.rent);
            const right = cx < width - 150;
            return (
              <motion.g
                key={c.city}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.2 + i * 0.12 }}
              >
                <circle
                  cx={cx}
                  cy={cy}
                  r={c.isWindsor ? 10 : 7}
                  className={c.isWindsor ? "hl-fill-windsor hl-dot" : "hl-fill-peer hl-dot"}
                  aria-label={`${c.city}: rent ${fmtMoney(c.rent)}, income ${fmtMoney(c.income)}, ${pct(c.rentPct, 1)} of income`}
                  {...tooltip.markProps(
                    <>
                      <strong>{c.city}</strong>
                      <br />
                      2-bedroom rent {fmtMoney(c.rent)} a month
                      <br />
                      Median renter income {fmtMoney(c.income)}
                      <br />A year of rent = {pct(c.rentPct, 1)} of income
                    </>
                  )}
                />
                <text
                  x={cx + (right ? 14 : -14)}
                  y={cy + (c.city === "London" ? -12 : c.city === "Hamilton" ? 14 : 0)}
                  textAnchor={right ? "start" : "end"}
                  dominantBaseline="middle"
                  className={c.isWindsor ? "hl-label hl-label--windsor" : "hl-label"}
                >
                  {c.city}
                </text>
              </motion.g>
            );
          })}
        </svg>
      )}
      {tooltip.node}
    </div>
  );
}

// --- 3. line: ten years of rent -------------------------------------------------

const EVENTS = [
  { year: 2020, text: "COVID", short: "COVID", detail: "People leave Toronto for cheaper cities" },
  {
    year: 2022,
    text: "Vacancy 1.8%",
    short: "Vac. 1.8%",
    detail: "Reopening, record immigration and students",
  },
  {
    year: 2024,
    text: "Student cap",
    short: "Cap",
    detail: "Permit cap and new rentals; vacancy recovers",
  },
];

function RentHistoryLine() {
  const { years, series } = data.rentHistory;
  const [ref, width] = useWidth();
  const tooltip = useTooltip(ref);
  const [hoverYear, setHoverYear] = useState(null);
  const narrow = width < 520;
  const height = 360;
  const m = { top: 54, right: narrow ? 74 : 132, bottom: 34, left: 56 };
  const x = scale(years[0], years[years.length - 1], m.left, width - m.right);
  const y = scale(700, 1900, height - m.bottom, m.top);
  const ordered = [...series].sort((a, b) => a.isWindsor - b.isWindsor); // Windsor drawn last, on top
  const path = (s) => s.rent.map((v, i) => `${i ? "L" : "M"}${x(years[i])},${y(v)}`).join("");

  // End labels, nudged apart so close values (Hamilton/London) stay legible.
  const last = years.length - 1;
  const labels = [...series]
    .map((s) => ({ s, ty: y(s.rent[last]) }))
    .sort((a, b) => a.ty - b.ty)
    .reduce(
      (acc, l) => [
        ...acc,
        { ...l, ty: acc.length ? Math.max(l.ty, acc[acc.length - 1].ty + 15) : l.ty },
      ],
      []
    );
  const shortName = (c) => (narrow ? abbreviate(c) : c);
  const colW = x(years[1]) - x(years[0]) || 1;

  return (
    <div className="hl-chart hl-chart--wide" ref={ref}>
      {width > 0 && (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label="Average 2-bedroom rent each October, 2015 to 2025, Windsor and four comparison cities"
        >
          {[800, 1100, 1400, 1700].map((v) => (
            <g key={v}>
              <line x1={m.left} x2={width - m.right} y1={y(v)} y2={y(v)} className="hl-grid" />
              <text
                x={m.left - 8}
                y={y(v)}
                className="hl-axis"
                textAnchor="end"
                dominantBaseline="middle"
              >
                {fmtMoney(v)}
              </text>
            </g>
          ))}
          {years
            .filter((yr) => !narrow || yr % 2 === 1)
            .map((yr) => (
              <text key={yr} x={x(yr)} y={height - 10} className="hl-axis" textAnchor="middle">
                {yr}
              </text>
            ))}
          {/* The middle label sits a row higher so neighbouring labels never touch. */}
          {EVENTS.map((e, i) => (
            <g key={e.year}>
              <line
                x1={x(e.year)}
                x2={x(e.year)}
                y1={m.top - (i % 2 ? 24 : 10)}
                y2={height - m.bottom}
                className="hl-event"
              />
              <text
                x={x(e.year)}
                y={m.top - (i % 2 ? 30 : 16)}
                className="hl-event-label"
                textAnchor="middle"
              >
                {narrow ? e.short : e.text}
              </text>
            </g>
          ))}
          {hoverYear !== null && (
            <line
              x1={x(hoverYear)}
              x2={x(hoverYear)}
              y1={m.top}
              y2={height - m.bottom}
              className="hl-crosshair"
            />
          )}
          {ordered.map((s, i) => (
            <motion.path
              key={s.city}
              d={path(s)}
              className={s.isWindsor ? "hl-line hl-line--windsor" : "hl-line"}
              initial={{ pathLength: 0 }}
              whileInView={{ pathLength: 1 }}
              viewport={{ once: true }}
              transition={{
                duration: s.isWindsor ? 1.6 : 1.1,
                delay: s.isWindsor ? 0.5 : i * 0.08,
                ease: "easeInOut",
              }}
            />
          ))}
          {series
            .filter((s) => s.isWindsor)
            .flatMap((s) =>
              s.rent.map((v, i) => (
                <circle
                  key={i}
                  cx={x(years[i])}
                  cy={y(v)}
                  r={hoverYear === years[i] ? 6 : 3.5}
                  className="hl-fill-windsor hl-point"
                />
              ))
            )}
          {labels.map(({ s, ty }) => (
            <text
              key={s.city}
              x={width - m.right + 8}
              y={ty}
              dominantBaseline="middle"
              className={s.isWindsor ? "hl-label hl-label--windsor" : "hl-label"}
            >
              {shortName(s.city)} {narrow ? "" : fmtMoney(s.rent[last])}
            </text>
          ))}
          {years.map((yr, i) => (
            <rect
              key={yr}
              x={x(yr) - colW / 2}
              y={m.top}
              width={colW}
              height={height - m.top - m.bottom}
              className="hl-hit"
              aria-label={`${yr}: ${series.map((s) => `${s.city} ${fmtMoney(s.rent[i])}`).join(", ")}`}
              tabIndex={0}
              role="img"
              onMouseEnter={(e) => {
                setHoverYear(yr);
                showYear(e.currentTarget, i);
              }}
              onFocus={(e) => {
                setHoverYear(yr);
                showYear(e.currentTarget, i);
              }}
              onMouseLeave={() => {
                setHoverYear(null);
                tooltip.hide();
              }}
              onBlur={() => {
                setHoverYear(null);
                tooltip.hide();
              }}
            />
          ))}
        </svg>
      )}
      <ul className="hl-legend">
        <li>
          <span className="hl-swatch hl-swatch--line hl-fill-windsor" /> Windsor
        </li>
        <li>
          <span className="hl-swatch hl-swatch--line hl-fill-peer" /> The four comparison cities
        </li>
      </ul>
      {tooltip.node}
    </div>
  );

  function showYear(target, i) {
    const event = EVENTS.find((e) => e.year === years[i]);
    tooltip.show(
      target,
      <>
        <strong>October {years[i]}</strong>
        {[...series]
          .sort((a, b) => b.rent[i] - a.rent[i])
          .map((s) => (
            <span
              key={s.city}
              className={s.isWindsor ? "hl-tip-row hl-tip-row--windsor" : "hl-tip-row"}
            >
              <span>{s.city}</span>
              <span>{fmtMoney(s.rent[i])}</span>
            </span>
          ))}
        {event && <em className="hl-tip-note">{event.detail}</em>}
      </>,
      { y: m.top + 10 }
    );
  }
}

// --- 4. houses: homes built per home needed -----------------------------------

function HouseIcon({ x, y, size, fill, className }) {
  // A gable-roofed house in a size x size box; `fill` (0-1) clips it from the left.
  const id = `clip-${Math.round(x)}-${Math.round(y)}`;
  const shape = `M${x + size * 0.1},${y + size * 0.48} L${x + size / 2},${y + size * 0.1} L${x + size * 0.9},${y + size * 0.48} L${x + size * 0.82},${y + size * 0.48} L${x + size * 0.82},${y + size * 0.92} L${x + size * 0.18},${y + size * 0.92} L${x + size * 0.18},${y + size * 0.48} Z`;
  return (
    <g>
      <path d={shape} className="hl-house-empty" />
      {fill > 0 && (
        <>
          <clipPath id={id}>
            <rect x={x} y={y} width={size * fill} height={size} />
          </clipPath>
          <path d={shape} className={className} clipPath={`url(#${id})`} />
        </>
      )}
    </g>
  );
}

function HomesBuilt() {
  const [ref, width] = useWidth();
  const tooltip = useTooltip(ref);
  const labelW = width < 480 ? 92 : 156;
  const valueW = 48;
  const size = Math.max(16, Math.min(34, Math.floor((width - labelW - valueW) / 10)));
  const rowH = size + 14;
  const height = data.supply.length * rowH;

  return (
    <div className="hl-chart hl-chart--wide" ref={ref}>
      {width > 0 && (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label="Homes completed for every 10 homes population growth needed, 2016 to 2021, by city"
        >
          {data.supply.map((s, row) => {
            const top = row * rowH;
            const houses = s.ratio * 10;
            return (
              <motion.g
                key={s.city}
                {...reveal(fadeUp, "-40px")}
                transition={{ delay: row * 0.12 }}
                aria-label={`${s.city}: ${fmtInt(s.built)} homes completed for ${fmtInt(s.needed)} needed, ${pct(s.ratio * 100)}`}
                {...tooltip.markProps(
                  <>
                    <strong>{s.city}</strong>
                    <br />
                    Homes needed for growth: {fmtInt(s.needed)}
                    <br />
                    Homes completed: {fmtInt(s.built)}
                  </>
                )}
                className="hl-house-row"
              >
                <rect x={0} y={top} width={width} height={rowH} className="hl-hit" />
                <text
                  x={0}
                  y={top + size / 2 + 4}
                  dominantBaseline="middle"
                  className={s.isWindsor ? "hl-label hl-label--windsor" : "hl-label"}
                >
                  {width < 480 ? abbreviate(s.city) : s.city}
                </text>
                {Array.from({ length: 10 }, (_, i) => (
                  <HouseIcon
                    key={i}
                    x={labelW + i * size}
                    y={top + 4}
                    size={size}
                    fill={Math.max(0, Math.min(1, houses - i))}
                    className={s.isWindsor ? "hl-fill-windsor" : "hl-fill-peer"}
                  />
                ))}
                <text
                  x={labelW + 10 * size + 8}
                  y={top + size / 2 + 4}
                  dominantBaseline="middle"
                  className={s.isWindsor ? "hl-value hl-label--windsor" : "hl-value"}
                >
                  {pct(s.ratio * 100)}
                </text>
              </motion.g>
            );
          })}
        </svg>
      )}
      {tooltip.node}
    </div>
  );
}

// --- 5. slope: what Windsor starts, before and from 2020 -------------------------

const TYPE_LABEL = {
  "Apartment and Other": "Apartments",
  Singles: "Single-detached",
  Semis: "Semi-detached",
  Row: "Row houses",
};
const TYPE_SHORT = {
  "Apartment and Other": "Apts",
  Singles: "Singles",
  Semis: "Semis",
  Row: "Row",
};

function StartsMixSlope() {
  const types = data.startsMix.filter((m) => m.type !== "Total");
  const [ref, width] = useWidth();
  const tooltip = useTooltip(ref);
  const height = 320;
  const narrow = width < 480;
  const m = { top: 34, bottom: 20, side: narrow ? 104 : 150 };
  const x0 = m.side;
  const x1 = width - m.side;
  const y = scale(0, 60, height - m.bottom, m.top);
  // Nudge labels apart on each side so close shares (row/semis) stay legible.
  const spread = (key) =>
    types
      .map((t) => ({ t, ty: y(t[key].share) }))
      .sort((a, b) => a.ty - b.ty)
      .reduce(
        (acc, l) => [
          ...acc,
          { ...l, ty: acc.length ? Math.max(l.ty, acc[acc.length - 1].ty + 18) : l.ty },
        ],
        []
      );
  const left = Object.fromEntries(spread("before").map((l) => [l.t.type, l.ty]));
  const right = Object.fromEntries(spread("after").map((l) => [l.t.type, l.ty]));

  return (
    <div className="hl-chart hl-chart--wide" ref={ref}>
      {width > 0 && (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label="Share of homes started in Windsor by dwelling type, 2016 to 2020 against 2021 to 2025"
        >
          {[
            [x0, "2016-2020"],
            [x1, "2021-2025"],
          ].map(([xx, label]) => (
            <g key={label}>
              <line x1={xx} x2={xx} y1={m.top} y2={height - m.bottom} className="hl-grid" />
              <text x={xx} y={m.top - 14} textAnchor="middle" className="hl-event-label">
                {label}
              </text>
            </g>
          ))}
          {types.map((t, i) => {
            const isApt = t.type === "Apartment and Other";
            const cls = isApt ? "hl-label hl-label--windsor" : "hl-label";
            return (
              <g
                key={t.type}
                className="hl-slope"
                aria-label={`${TYPE_LABEL[t.type]}: ${pct(t.before.share)} of starts in 2016-2020, ${pct(t.after.share)} in 2021-2025`}
                {...tooltip.markProps(
                  <>
                    <strong>{TYPE_LABEL[t.type]}</strong>
                    <br />
                    2016-2020: {fmtInt(t.before.per_year)} a year ({pct(t.before.share, 1)})
                    <br />
                    2021-2025: {fmtInt(t.after.per_year)} a year ({pct(t.after.share, 1)})
                  </>
                )}
              >
                <motion.line
                  x1={x0}
                  y1={y(t.before.share)}
                  x2={x1}
                  y2={y(t.after.share)}
                  className={isApt ? "hl-line hl-line--windsor" : "hl-line"}
                  initial={{ pathLength: 0 }}
                  whileInView={{ pathLength: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 1, delay: 0.2 + i * 0.12, ease: "easeInOut" }}
                />
                <circle
                  cx={x0}
                  cy={y(t.before.share)}
                  r={5}
                  className={isApt ? "hl-fill-windsor hl-point" : "hl-fill-peer hl-point"}
                />
                <circle
                  cx={x1}
                  cy={y(t.after.share)}
                  r={5}
                  className={isApt ? "hl-fill-windsor hl-point" : "hl-fill-peer hl-point"}
                />
                <text
                  x={x0 - 12}
                  y={left[t.type]}
                  textAnchor="end"
                  dominantBaseline="middle"
                  className={cls}
                >
                  {narrow ? "" : `${TYPE_LABEL[t.type]} `}
                  {pct(t.before.share)}
                </text>
                <text x={x1 + 12} y={right[t.type]} dominantBaseline="middle" className={cls}>
                  {pct(t.after.share)} {(narrow ? TYPE_SHORT : TYPE_LABEL)[t.type]}
                </text>
              </g>
            );
          })}
        </svg>
      )}
      {tooltip.node}
    </div>
  );
}

// --- the findings ------------------------------------------------------------

function Finding({ number, title, children, chart, table, link, source, flip }) {
  return (
    <motion.article
      className={`hl-finding card${flip ? " hl-finding--flip" : ""}`}
      {...reveal(fadeUp)}
    >
      <div className="hl-text">
        <p className="hl-number">{number}</p>
        <h3>{title}</h3>
        {children}
        {link.to.startsWith("#") ? (
          <a className="hl-link" href={link.to}>
            {link.label}&nbsp;&darr;
          </a>
        ) : (
          <Link className="hl-link" to={link.to}>
            {link.label}&nbsp;&rarr;
          </Link>
        )}
      </div>
      <figure className="hl-figure">
        {chart}
        <figcaption>{source}</figcaption>
        {table}
      </figure>
    </motion.article>
  );
}

// Each finding: its chart, text and the story page whose dashboard explores it.
function buildFindings() {
  const a = data.affordability;
  const windsorCity = data.cities.find((c) => c.isWindsor);
  const peers = data.cities.filter((c) => !c.isWindsor);
  const sameShare = peers
    .filter((c) => Math.abs(c.rentPct - windsorCity.rentPct) < 0.05)
    .map((c) => c.city);

  const { years, series } = data.rentHistory;
  const w = series.find((s) => s.isWindsor).rent;
  const first = 0;
  const mid = years.indexOf(2020);
  const last = years.length - 1;
  const peerAvg = (i) => series.filter((s) => !s.isWindsor).reduce((t, s) => t + s.rent[i], 0) / 4;

  const windsorSupply = data.supply.find((s) => s.isWindsor);
  const peerRatios = data.supply.filter((s) => !s.isWindsor).map((s) => s.ratio * 100);

  const mix = Object.fromEntries(data.startsMix.map((m) => [m.type, m]));
  const apt = mix["Apartment and Other"];
  const total = mix.Total;

  return {
    afford: {
      story: "/stories/integrated-analysis",
      title: `${Math.round(a.pct / 10)} in 10 Windsor renters cannot afford an average 2-bedroom`,
      chart: <AffordWaffle />,
      linkLabel: "Explore affordability by unit size (Story 5)",
      source:
        "Each square is 1% of Windsor's renter households. Census 2021 incomes (2020) and CMHC October 2025 rents.",
      table: (
        <DataTable
          caption="Windsor renter households and a 2-bedroom"
          head={["Measure", "Value"]}
          rows={[
            ["Average 2-bedroom rent", fmtMoney(a.rent)],
            ["Income needed (rent = 30% of income)", fmtMoney(a.incomeNeeded)],
            ["Median renter household income", fmtMoney(a.medianIncome)],
            ["Renter households", fmtInt(a.renters)],
            ["Cannot afford it", `${fmtInt(a.cannot)} (${pct(a.pct, 1)})`],
          ]}
        />
      ),
      body: (
        <p>
          A 2-bedroom averages <strong>{fmtMoney(a.rent)}</strong> a month. Keeping rent to 30% of
          income takes <strong>{fmtMoney(a.incomeNeeded)}</strong> a year, but the typical renter
          household earns <strong>{fmtMoney(a.medianIncome)}</strong>. {fmtInt(a.cannot)} of{" "}
          {fmtInt(a.renters)} renter households fall short.
        </p>
      ),
    },
    cheap: {
      story: "/stories/integrated-analysis",
      title: "Windsor is cheaper, not more affordable",
      chart: <RentIncomeScatter />,
      linkLabel: "Compare the five cities (Story 5)",
      source:
        "2-bedroom apartment rent, CMHC October 2025; median renter household income, Census 2021 (2020 incomes).",
      table: (
        <DataTable
          caption="Rent and renter income by city"
          head={["City", "2-bed rent", "Median renter income", "Rent as % of income"]}
          rows={data.cities.map((c) => [
            c.city,
            fmtMoney(c.rent),
            fmtMoney(c.income),
            pct(c.rentPct, 1),
          ])}
        />
      ),
      body: (
        <p>
          Windsor has the lowest rent of the five cities, and its renters also have among the lowest
          incomes. A year of 2-bedroom rent takes <strong>{pct(windsorCity.rentPct)}</strong> of the
          median renter&rsquo;s income
          {sameShare.length ? `, the same as ${sameShare.join(" and ")}` : ""}. Every city sits
          above the 30% line.
        </p>
      ),
    },
    decade: {
      story: "/stories/comparison",
      title: `Ten years: Windsor rents up ${pct((w[last] / w[first] - 1) * 100)}`,
      chart: <RentHistoryLine />,
      linkLabel: "See ten years of rent and vacancy (Story 4)",
      source:
        "Average 2-bedroom rent each October, apartments and row houses. CMHC Rental Market Survey via StatCan 34-10-0133-01. Event labels are context, not measured in this data.",
      table: (
        <DataTable
          caption="2-bedroom rent each October"
          head={["City", ...years.filter((_, i) => i % 5 === 0 || i === last).map(String)]}
          rows={series.map((s) => [
            s.city,
            ...s.rent.filter((_, i) => i % 5 === 0 || i === last).map(fmtMoney),
          ])}
        />
      ),
      body: (
        <p>
          From <strong>{fmtMoney(w[first])}</strong> in {years[first]} to{" "}
          <strong>{fmtMoney(w[last])}</strong> in {years[last]}. Rents rose{" "}
          <strong>{pct(cagr(w[first], w[mid], mid - first), 1)}</strong> a year before the pandemic
          and <strong>{pct(cagr(w[mid], w[last], last - mid), 1)}</strong> a year from 2020. Windsor
          is still the cheapest city, but the gap is closing: its rent went from{" "}
          {pct((w[first] / peerAvg(first)) * 100)} to {pct((w[last] / peerAvg(last)) * 100)} of the
          other four cities&rsquo; average.
        </p>
      ),
    },
    supply: {
      story: "/stories/integrated-analysis",
      title: `Windsor built ${Math.round(windsorSupply.ratio * 10)} of every 10 homes its growth needed`,
      chart: <HomesBuilt />,
      linkLabel: "See supply against demand (Story 5)",
      source:
        "Homes completed 2016-2020 (StatCan 34-10-0154-01) against homes needed for 2016-2021 population growth at 2021 household sizes (Census).",
      table: (
        <DataTable
          caption="Homes needed and completed by city"
          head={["City", "Homes needed", "Homes completed", "Share built"]}
          rows={data.supply.map((s) => [
            s.city,
            fmtInt(s.needed),
            fmtInt(s.built),
            pct(s.ratio * 100),
          ])}
        />
      ),
      body: (
        <p>
          Between the 2016 and 2021 Censuses, Windsor&rsquo;s population growth needed about{" "}
          <strong>{fmtInt(windsorSupply.needed)}</strong> homes; it completed{" "}
          <strong>{fmtInt(windsorSupply.built)}</strong>. The other four cities built{" "}
          {pct(Math.min(...peerRatios))} to {pct(Math.max(...peerRatios))} of what they needed.
        </p>
      ),
    },
    mix: {
      story: "/stories/housing-supply",
      title: `Apartments went from ${pct(apt.before.share)} to ${pct(apt.after.share)} of what Windsor starts`,
      chart: <StartsMixSlope />,
      linkLabel: "Compare the two periods (Story 3)",
      source:
        "Share of homes started by dwelling type, five full years each. CMHC Starts and Completions Survey via StatCan 34-10-0154-01.",
      table: (
        <DataTable
          caption="Homes started a year by dwelling type"
          head={[
            "Dwelling type",
            "2016-2020 a year",
            "2021-2025 a year",
            "Share then",
            "Share now",
          ]}
          rows={data.startsMix.map((m) => [
            TYPE_LABEL[m.type] ?? "All homes",
            fmtInt(m.before.per_year),
            fmtInt(m.after.per_year),
            pct(m.before.share),
            pct(m.after.share),
          ])}
        />
      ),
      body: (
        <p>
          Windsor started <strong>{fmtInt(total.after.per_year)}</strong> homes a year in 2021-2025,
          up from <strong>{fmtInt(total.before.per_year)}</strong> in 2016-2020. What it builds
          changed more: apartments rose from <strong>{fmtInt(apt.before.per_year)}</strong> to{" "}
          <strong>{fmtInt(apt.after.per_year)}</strong> a year, while single-detached starts fell
          from {fmtInt(mix.Singles.before.per_year)} to {fmtInt(mix.Singles.after.per_year)}.
        </p>
      ),
    },
  };
}

// The home page shows the four headline findings, each linking to its story.
// A story page passes `only` (the findings that belong to it) and `here`
// (its own path): a finding explored on that same page links down to the
// page's dashboard instead of to itself.
const HOME_FINDINGS = ["afford", "cheap", "decade", "supply"];

export default function StoryHighlights({ only = HOME_FINDINGS, here = null }) {
  const findings = buildFindings();
  const onStoryPage = here !== null;
  return (
    <section
      className={`section hl-section${onStoryPage ? " hl-section--story" : ""}`}
      id="findings"
      aria-labelledby="findings-title"
    >
      <motion.div className="section-heading" {...reveal(fadeUp)}>
        <h2 id="findings-title">{onStoryPage ? "Key findings" : "The story in four charts"}</h2>
        <p className="section-note">
          Hover or tab through a chart for details; the dashboard has the full data
        </p>
      </motion.div>
      {only.map((key, i) => {
        const f = findings[key];
        const link =
          f.story === here
            ? { to: "#dashboard", label: "Explore it in the dashboard below" }
            : { to: f.story, label: f.linkLabel };
        return (
          <Finding
            key={key}
            flip={i % 2 === 1}
            number={String(i + 1).padStart(2, "0")}
            title={f.title}
            chart={f.chart}
            link={link}
            source={f.source}
            table={f.table}
          >
            {f.body}
          </Finding>
        );
      })}
    </section>
  );
}
