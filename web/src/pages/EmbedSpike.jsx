import { useEffect, useRef } from "react";
import { embedDashboard } from "@superset-ui/embedded-sdk";
import PageContainer from "../components/PageContainer.jsx";

// Embedding spike (docs/embedding_spike.md) -- not linked from the site nav,
// a throwaway test route to prove the Embedded SDK mechanism, not a page
// meant for real visitors. Superseded by the real implementation:
// api/guest_token_server.py and components/SupersetGuestEmbed.jsx, used by
// the Story 1 page (docs/embedding_prototype.md). This route still targets
// the spike's test dashboard, which the backend doesn't allow, so it fails
// by design.
//
// SUPERSET_DASHBOARD_UUID is this spike's one test dashboard (see
// docs/embedding_spike.md for how it was created) -- not a real story
// dashboard.
const SUPERSET_DOMAIN = "http://localhost:8088";
const SUPERSET_DASHBOARD_UUID = "a37bce16-3fee-4097-9827-210061979192";

// The real blocker this spike exists to surface: this project has no
// backend server to mint guest tokens from. Superset's own docs are
// explicit that /api/v1/security/guest_token/ must never be called from
// client-side code (it needs an admin-level service account credential) --
// so fetchGuestToken here correctly calls OUR OWN origin instead of
// Superset directly, same as a real implementation would. That endpoint
// doesn't exist yet -- this fetch 404s until one does. See
// docs/embedding_spike.md for exactly what minting one manually (bypassing
// this gap for verification only) proved works.
async function fetchGuestToken() {
  const resp = await fetch("/api/guest-token", { method: "POST" });
  if (!resp.ok) {
    throw new Error(
      `/api/guest-token returned ${resp.status} -- no backend token-minting endpoint exists yet`
    );
  }
  const { token } = await resp.json();
  return token;
}

export default function EmbedSpike() {
  const mountRef = useRef(null);

  useEffect(() => {
    if (!mountRef.current) return;
    embedDashboard({
      id: SUPERSET_DASHBOARD_UUID,
      supersetDomain: SUPERSET_DOMAIN,
      mountPoint: mountRef.current,
      fetchGuestToken,
      dashboardUiConfig: { hideTitle: true },
    }).catch((err) => {
      console.error("Embed failed:", err);
    });
  }, []);

  return (
    <PageContainer>
      <h1>Embedding spike (not a real page)</h1>
      <p className="placeholder-note">
        Test route for the Embedded SDK spike -- see docs/embedding_spike.md. Will fail until a real
        /api/guest-token backend endpoint exists.
      </p>
      <div ref={mountRef} style={{ minHeight: 400 }} />
    </PageContainer>
  );
}
