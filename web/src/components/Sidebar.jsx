import { useState } from "react";
import { NavLink } from "react-router-dom";

// Small inline icon set -- one glyph per nav item, no icon-library
// dependency. Each is a plain 20x20 stroke icon so they read at the same
// visual weight as the sidebar's text.
const ICONS = {
  home: (
    <path d="M3 10.5 10 4l7 6.5M5 9v7a1 1 0 0 0 1 1h3v-5h2v5h3a1 1 0 0 0 1-1V9" />
  ),
  affordability: <path d="M10 2v16M14 5.5c0-1.4-1.6-2.5-4-2.5s-4 1.1-4 2.5 1.6 2.3 4 2.7c2.4.4 4 1.3 4 2.8s-1.6 2.5-4 2.5-4-1.1-4-2.5" />,
  rental: (
    <path d="M13 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8ZM2 17l5-5 2.5 2.5L15 9" />
  ),
  supply: <path d="M3 17V9l4-2v10M9 17V5l4-2v14M15 17V9l2-1v9M3 17h14" />,
  comparison: (
    <path d="M10 2v15M4 6l-2 5a3 3 0 0 0 6 0l-2-5Zm12 0-2 5a3 3 0 0 0 6 0l-2-5ZM3 6h4M13 6h4M6 17h8" />
  ),
  integrated: (
    <path d="m10 2 8 4-8 4-8-4 8-4ZM2 10l8 4 8-4M2 14l8 4 8-4" />
  ),
  methodology: <path d="M4 2h9l4 4v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1ZM13 2v4h4M6 11h8M6 14h8M6 8h4" />,
  sources: <path d="M3 5a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5Z" />,
};

function Icon({ name }) {
  return (
    <svg
      className="sidebar-icon"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name]}
    </svg>
  );
}

const NAV_SECTIONS = [
  {
    items: [{ to: "/", label: "Home", end: true, icon: "home" }],
  },
  {
    heading: "Explore the stories",
    items: [
      { to: "/stories/affordability", label: "Story 1 · Affordability", icon: "affordability", accent: "rose" },
      { to: "/stories/rental-market", label: "Story 2 · Rental Market", icon: "rental", accent: "blue" },
      { to: "/stories/housing-supply", label: "Story 3 · Housing Supply", icon: "supply", accent: "teal" },
      { to: "/stories/comparison", label: "Story 4 · CMA Comparison", icon: "comparison", accent: "violet" },
      { to: "/stories/integrated-analysis", label: "Story 5 · Integrated Analysis", icon: "integrated", accent: "blue" },
    ],
  },
  {
    heading: "Reference",
    items: [
      { to: "/methodology", label: "Methodology", icon: "methodology" },
      { to: "/sources", label: "Sources", icon: "sources" },
    ],
  },
];

export default function Sidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="sidebar-topbar">
        <NavLink to="/" className="brand" onClick={() => setOpen(false)}>
          <span className="brand-mark" aria-hidden="true">
            W
          </span>
          Windsor Housing Analytics
        </NavLink>
        <button
          type="button"
          className="menu-toggle"
          aria-expanded={open}
          aria-controls="primary-sidebar"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((v) => !v)}
        >
          <span className="menu-toggle-bar" />
          <span className="menu-toggle-bar" />
          <span className="menu-toggle-bar" />
        </button>
      </div>

      <aside id="primary-sidebar" className={`app-sidebar ${open ? "app-sidebar--open" : ""}`}>
        <NavLink to="/" className="brand sidebar-brand" onClick={() => setOpen(false)}>
          <span className="brand-mark" aria-hidden="true">
            W
          </span>
          <span>
            Windsor Housing
            <br />
            Analytics
          </span>
        </NavLink>

        <nav className="sidebar-nav">
          {NAV_SECTIONS.map((section, i) => (
            <div className="sidebar-nav-section" key={section.heading ?? `section-${i}`}>
              {section.heading && <p className="sidebar-nav-heading">{section.heading}</p>}
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) => `sidebar-nav-link${isActive ? " active" : ""}`}
                >
                  <Icon name={item.icon} />
                  <span>{item.label}</span>
                  {item.accent && (
                    <span
                      className={`sidebar-nav-dot kpi-tile-badge--${item.accent}`}
                      aria-hidden="true"
                    />
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <p className="sidebar-foot-note">COMP 8977 &middot; University of Windsor</p>
      </aside>

      {open && <div className="sidebar-scrim" onClick={() => setOpen(false)} aria-hidden="true" />}
    </>
  );
}
