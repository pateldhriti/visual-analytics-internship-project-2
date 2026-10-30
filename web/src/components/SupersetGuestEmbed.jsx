import { useEffect, useRef, useState } from "react";
import { embedDashboard } from "@superset-ui/embedded-sdk";
import SupersetEmbed from "./SupersetEmbed.jsx";

// Embeds a Superset dashboard with the Embedded SDK and a guest token from
// our own backend (api/guest_token_server.py, proxied at /api by
// vite.config.js) -- Option B from docs/superset_embedding_research.md, the
// route docs/embedding_spike.md proved works but had no backend for.
//
// `dashboard` is the backend's short name ("story1"), not a Superset id:
// the backend only issues tokens for dashboards on its own allowlist and
// returns the embedded UUID with the token, so nothing here hardcodes it.
//
// If the backend isn't reachable (it isn't part of the static build, so a
// deploy without it is a real case), this falls back to the public-role
// iframe (SupersetEmbed) for the same dashboard rather than showing an
// empty box.
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

// After the dashboard renders, grow the frame to the dashboard's own
// height so the page scrolls once instead of a scroll area inside a
// scroll area. Checked a few times because charts load asynchronously.
const RESIZE_CHECKS = 10;
const RESIZE_INTERVAL_MS = 1500;

export default function SupersetGuestEmbed({
  dashboard,
  fallbackDashboardId,
  title,
  height = 1400,
}) {
  const mountRef = useRef(null);
  const [failed, setFailed] = useState(false);
  const [frameHeight, setFrameHeight] = useState(height);

  useEffect(() => {
    let cancelled = false;
    let embedded = null;
    let resizeTimer = null;

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
          dashboardUiConfig: { hideTitle: true },
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
        let checks = 0;
        resizeTimer = setInterval(async () => {
          checks += 1;
          try {
            const size = await embedded.getScrollSize();
            if (!cancelled && size?.height) {
              setFrameHeight((current) => Math.max(current, Math.ceil(size.height)));
            }
          } catch {
            // Size isn't available until the dashboard has loaded; try again.
          }
          if (checks >= RESIZE_CHECKS) clearInterval(resizeTimer);
        }, RESIZE_INTERVAL_MS);
      })
      .catch((err) => {
        console.warn(`Guest-token embed unavailable, using public embed instead: ${err.message}`);
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
      clearInterval(resizeTimer);
      embedded?.unmount();
    };
  }, [dashboard, title]);

  if (failed) {
    return <SupersetEmbed dashboardId={fallbackDashboardId} title={title} height={height} />;
  }

  return (
    <div className="superset-embed card">
      <div className="superset-embed-header">
        <span className="superset-embed-badge">Live dashboard</span>
      </div>
      <div
        ref={mountRef}
        className="superset-embed-sdk"
        style={{ height: frameHeight }}
        aria-label={title}
      />
    </div>
  );
}
