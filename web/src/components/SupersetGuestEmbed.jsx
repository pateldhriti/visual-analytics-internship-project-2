import { useEffect, useRef, useState } from "react";
import { embedDashboard } from "@superset-ui/embedded-sdk";
import SupersetEmbed from "./SupersetEmbed.jsx";
import useNarrowScreen from "../lib/useNarrowScreen.js";
import { EmbedError, EmbedLoading, NarrowHint } from "./EmbedStatus.jsx";
import { LOAD_TIMEOUT_MS, dashboardUrl } from "../lib/embedConfig.js";

// Embeds a Superset dashboard with the Embedded SDK and a short-lived guest
// token from our own backend (api/guest_token_server.py, proxied at /api by
// vite.config.js and by docker/Caddyfile in production).
//
// `dashboard` is the backend's short name ("story1" ... "story4"), not a
// Superset id: the backend only issues tokens for its allow-list, checks the
// request comes from this site, and returns the embedded UUID with the token.
//
// States:
//   loading  -- token requested / dashboard drawing (spinner over the frame)
//   ready    -- the SDK reports the dashboard's size, so it has rendered
//   fallback -- the token API is unreachable or refused: the public-role
//               iframe (SupersetEmbed) is shown instead, if a dashboard id
//               is given, with its own loading and error states
//   error    -- nothing to fall back to, or the dashboard never rendered
//               within LOAD_TIMEOUT_MS: a message with "Try again"
async function requestGuestToken(dashboard) {
  const resp = await fetch("/api/guest-token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dashboard }),
  });
  if (!resp.ok) {
    throw new Error(`/api/guest-token returned ${resp.status}`);
  }
  return resp.json();
}

// Keep the frame the height of the dashboard tab being shown, so the page
// scrolls once instead of a scroll area inside a scroll area. Checked
// repeatedly because charts load asynchronously and each tab has its own
// height; `height` is the minimum, so switching tabs does not make the
// page jump by more than the difference between tabs.
const RESIZE_INTERVAL_MS = 1500;

export default function SupersetGuestEmbed({
  dashboard,
  fallbackDashboardId,
  title,
  height = 1100,
}) {
  const narrow = useNarrowScreen();
  const mountRef = useRef(null);
  const [status, setStatus] = useState("loading");
  const [attempt, setAttempt] = useState(0);
  const [frameHeight, setFrameHeight] = useState(height);
  const openUrl = fallbackDashboardId ? dashboardUrl(fallbackDashboardId) : null;

  useEffect(() => {
    let cancelled = false;
    let embedded = null;
    let resizeTimer = null;
    setStatus("loading");
    const timeout = setTimeout(() => {
      if (!cancelled) setStatus((s) => (s === "loading" ? "error" : s));
    }, LOAD_TIMEOUT_MS);

    requestGuestToken(dashboard)
      .then(({ token, dashboardUuid, supersetDomain }) => {
        if (cancelled || !mountRef.current) return null;
        // The first token is already in hand; the SDK asks again only when
        // it needs a refresh.
        let firstToken = token;
        return embedDashboard({
          id: dashboardUuid,
          supersetDomain,
          mountPoint: mountRef.current,
          fetchGuestToken: async () => {
            if (firstToken) {
              const t = firstToken;
              firstToken = null;
              return t;
            }
            return (await requestGuestToken(dashboard)).token;
          },
          // Phones: start with Superset's filter bar collapsed.
          dashboardUiConfig: { hideTitle: true, filters: { expanded: !narrow } },
        });
      })
      .then((result) => {
        if (!result) return;
        embedded = result;
        if (cancelled) {
          embedded.unmount();
          return;
        }
        // The SDK creates the iframe without a title; screen readers need one.
        mountRef.current?.querySelector("iframe")?.setAttribute("title", title);
        resizeTimer = setInterval(async () => {
          try {
            const size = await embedded.getScrollSize();
            if (!cancelled && size?.height) {
              setStatus("ready");
              clearTimeout(timeout);
              setFrameHeight(Math.max(height, Math.ceil(size.height)));
            }
          } catch {
            // Size isn't available until the dashboard has loaded; try again.
          }
        }, RESIZE_INTERVAL_MS);
      })
      .catch((err) => {
        console.warn(`Guest-token embed unavailable: ${err.message}`);
        if (cancelled) return;
        clearTimeout(timeout);
        setStatus(fallbackDashboardId ? "fallback" : "error");
      });

    return () => {
      cancelled = true;
      clearTimeout(timeout);
      clearInterval(resizeTimer);
      embedded?.unmount();
    };
  }, [dashboard, title, narrow, attempt, fallbackDashboardId, height]);

  if (status === "fallback") {
    return <SupersetEmbed dashboardId={fallbackDashboardId} title={title} height={height} />;
  }

  return (
    <div className="superset-embed card">
      <div className="superset-embed-header">
        <span className="superset-embed-badge">Live dashboard</span>
        {openUrl && (
          <a href={openUrl} target="_blank" rel="noreferrer" className="superset-embed-link">
            Open full dashboard ↗
          </a>
        )}
      </div>
      {narrow && <NarrowHint openUrl={openUrl} />}
      <div className="superset-embed-body" aria-busy={status === "loading"}>
        {/* On phones this frame scrolls sideways; focusable so keyboard users
            can scroll it with the arrow keys. */}
        <div
          className="superset-embed-scroll"
          {...(narrow
            ? { tabIndex: 0, role: "region", "aria-label": `${title}, scrolls sideways` }
            : {})}
        >
          <div
            key={attempt}
            ref={mountRef}
            className="superset-embed-sdk"
            style={{ height: frameHeight }}
            aria-label={title}
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
