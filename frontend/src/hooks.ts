import { useEffect, useState } from "react";

/** Value that settles `delay` ms after the last change.
 *  Use for search boxes so typing does not fire a request per keystroke. */
export function useDebouncedValue<T>(value: T, delay = 280): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setSettled(value), delay);
    return () => window.clearTimeout(t);
  }, [value, delay]);
  return settled;
}
