// Shared loading / error / phone-width pieces for the two dashboard embeds
// (SupersetGuestEmbed and SupersetEmbed).

export function EmbedLoading() {
  return (
    <div className="embed-overlay" role="status" aria-live="polite">
      <span className="embed-spinner" aria-hidden="true" />
      <span>Loading the live dashboard…</span>
    </div>
  );
}

export function EmbedError({ onRetry, openUrl }) {
  return (
    <div className="embed-overlay embed-overlay--error" role="alert">
      <p className="embed-error-title">The live dashboard could not be loaded.</p>
      <p className="embed-error-text">
        The dashboard server may be starting up or unavailable. The figures and text on this page do
        not depend on it.
      </p>
      <div className="embed-error-actions">
        {onRetry && (
          <button type="button" className="embed-button" onClick={onRetry}>
            Try again
          </button>
        )}
        {openUrl && (
          <a
            className="embed-button embed-button--ghost"
            href={openUrl}
            target="_blank"
            rel="noreferrer"
          >
            Open the dashboard in a new tab ↗
          </a>
        )}
      </div>
    </div>
  );
}

// Shown above the embed on phones, where the dashboard is laid out at
// tablet width inside a frame that scrolls sideways.
export function NarrowHint({ openUrl }) {
  return (
    <p className="embed-narrow-hint">
      Swipe sideways inside the frame to see the whole dashboard
      {openUrl ? (
        <>
          , or{" "}
          <a href={openUrl} target="_blank" rel="noreferrer">
            open it full screen ↗
          </a>
        </>
      ) : null}
      .
    </p>
  );
}
