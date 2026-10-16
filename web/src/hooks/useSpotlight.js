// Cursor-tracking glow: sets CSS custom properties the wrapped element's
// ::before (see .spotlight in index.css) reads to position a soft radial
// highlight under the pointer. Pure CSS-variable approach -- no re-render
// per mouse move, just a style mutation on the DOM node.
export default function useSpotlight() {
  function onMouseMove(e) {
    const el = e.currentTarget;
    const rect = el.getBoundingClientRect();
    el.style.setProperty("--spot-x", `${e.clientX - rect.left}px`);
    el.style.setProperty("--spot-y", `${e.clientY - rect.top}px`);
  }
  return { onMouseMove, className: "spotlight" };
}
