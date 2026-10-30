// Shared Framer Motion variants -- one definition reused across Home and
// every story page instead of each file redefining the same curves.
// `fadeUp` moves on the y-axis, so it's only used where nothing else
// (a CSS :hover rule, a flex layout) also owns that element's `transform`.
// `fadeIn` is opacity-only, for elements whose hover/lift is handled by
// plain CSS already.

export const staggerParent = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12, delayChildren: 0.05 } },
};

export const fadeUp = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 160, damping: 18 } },
};

export const fadeIn = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.5, ease: "easeOut" } },
};

export const slideFromLeft = {
  hidden: { opacity: 0, x: -28 },
  show: { opacity: 1, x: 0, transition: { type: "spring", stiffness: 140, damping: 18 } },
};

export const slideFromRight = {
  hidden: { opacity: 0, x: 28 },
  show: { opacity: 1, x: 0, transition: { type: "spring", stiffness: 140, damping: 18 } },
};

export const scaleIn = {
  hidden: { opacity: 0, scale: 0.92 },
  show: { opacity: 1, scale: 1, transition: { type: "spring", stiffness: 170, damping: 16 } },
};

// Standard viewport-triggered reveal props -- spread onto a motion.*
// element: `<motion.div {...reveal(staggerParent)}>`. `once: true` so a
// section doesn't re-animate every time it scrolls back into view.
export function reveal(variants, margin = "-80px") {
  return {
    variants,
    initial: "hidden",
    whileInView: "show",
    viewport: { once: true, margin },
  };
}
