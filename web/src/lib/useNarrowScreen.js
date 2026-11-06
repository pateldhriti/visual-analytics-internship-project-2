import { useEffect, useState } from "react";

// True below `maxWidth` px (phones). Used by the dashboard embeds, which
// lay Superset out at tablet width inside a swipeable frame on phones and
// start with Superset's filter bar collapsed.
export const NARROW_QUERY = "(max-width: 760px)";

export default function useNarrowScreen(query = NARROW_QUERY) {
  const get = () => typeof window !== "undefined" && window.matchMedia(query).matches;
  const [narrow, setNarrow] = useState(get);

  useEffect(() => {
    const media = window.matchMedia(query);
    const update = () => setNarrow(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [query]);

  return narrow;
}
