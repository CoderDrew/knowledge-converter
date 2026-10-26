import type { KeyboardEvent } from "react";

/**
 * WAI-ARIA roving focus for tablists and radio groups: arrow keys move to the
 * previous or next item (wrapping), Home and End jump to the ends, and the
 * newly focused item is selected (automatic activation). Only the selected
 * item is in the Tab order (tabIndex 0); the rest get -1.
 */
export function rovingKeyDown<T extends string>(
  event: KeyboardEvent<HTMLElement>,
  ids: readonly T[],
  current: T,
  select: (id: T) => void,
  domId: (id: T) => string,
  orientation: "horizontal" | "both" = "both",
) {
  const index = ids.indexOf(current);
  const prevKeys = orientation === "horizontal" ? ["ArrowLeft"] : ["ArrowLeft", "ArrowUp"];
  const nextKeys = orientation === "horizontal" ? ["ArrowRight"] : ["ArrowRight", "ArrowDown"];
  let target: number;
  if (nextKeys.includes(event.key)) target = (index + 1) % ids.length;
  else if (prevKeys.includes(event.key)) target = (index - 1 + ids.length) % ids.length;
  else if (event.key === "Home") target = 0;
  else if (event.key === "End") target = ids.length - 1;
  else return;
  event.preventDefault();
  select(ids[target]);
  document.getElementById(domId(ids[target]))?.focus();
}
