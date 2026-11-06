import { useEffect, useRef, useState } from "react";
import useNarrowScreen from "../lib/useNarrowScreen.js";
import { EmbedError, EmbedLoading, NarrowHint } from "./EmbedStatus.jsx";
import { LOAD_TIMEOUT_MS, SUPERSET_DOMAIN, dashboardUrl } from "../lib/embedConfig.js";

// Public-role iframe embed: the fallback used by SupersetGuestEmbed when the
// guest-token API is unavailable. Every dataset the dashboard queries must be
// in docker/superset_config.py's PUBLIC_DATASOURCE_NAMES.
//
// standalone=2 hides Superset's navbar and the dashboard's own title row.
// On phones the filter bar starts collapsed (expand_filters=0) and the
// dashboard is laid out at tablet width in a frame that scrolls sideways,
// because Superset 3.1's grid does not reflow for phone screens.
//
// States: loading (until the iframe's load event), loaded, and an error
// state with "Try again" if nothing loads within LOAD_TIMEOUT_MS.
export default function SupersetEmbed({ dashboardId, title, height = 1400 }) {
  const narrow = useNarrowScreen();
  const [status, setStatus] = useState("loading");
  const [attempt, setAttempt] = useState(0);
  const timer = useRef(null);

  const params = new URLSearchParams({ standalone: "2" });
  if (narrow) params.set("expand_filters", "0");
  const src = `${SUPERSET_DOMAIN}/superset/dashboard/${dashboardId}/?${params}`;
  const openUrl = dashboardUrl(dashboardId);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      setStatus((s) => (s === "loading" ? "error" : s));
    }, LOAD_TIMEOUT_MS);
    // An iframe fires "load" even when the server is unreachable (on the
    // browser's own error page), so check Superset first. A no-cors request
    // resolves (opaque) whenever the server answers and only rejects when it
    // cannot be reached at all.
    fetch(`${SUPERSET_DOMAIN}/health`, { mode: "no-cors", cache: "no-store" }).catch(() => {
      if (cancelled) return;
      clearTimeout(timer.current);
      setStatus("error");
    });
    return () => {
      cancelled = true;
      clearTimeout(timer.current);
    };
  }, [src, attempt]);

  return (
    <div className="superset-embed card">
      <div className="superset-embed-header">
        <span className="superset-embed-badge">Live dashboard</span>
        <a href={openUrl} target="_blank" rel="noreferrer" className="superset-embed-link">
          Open full dashboard ↗
        </a>
      </div>
      {narrow && <NarrowHint openUrl={openUrl} />}
      <div className="superset-embed-body" aria-busy={status === "loading"}>
        <div className="superset-embed-scroll">
          <iframe
            key={attempt}
            src={src}
            title={title}
            className="superset-embed-frame"
            style={{ height }}
            loading="lazy"
            onLoad={() => {
              clearTimeout(timer.current);
              // Keep an error set by the health check: the browser's own
              // error page also fires load.
              setStatus((s) => (s === "loading" ? "loaded" : s));
            }}
          />
        </div>
        {status === "loading" && <EmbedLoading />}
        {status === "error" && (
          <EmbedError onRetry={() => setAttempt((a) => a + 1)} openUrl={openUrl} />
        )}
      </div>
    </div>
  );
}
