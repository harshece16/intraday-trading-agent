/** Column sorting for the rule-lab table (README section 129). Pure: no React,
 *  no DOM, so `npm test` covers it.
 *
 *  A column is {key, get, kind}: `get(row)` returns the value to sort on and
 *  `kind` is "num" or "text". A null, undefined or NaN value (shown as "—") is
 *  last in both directions, so a column of mostly-empty cells still reads
 *  top-down. Ties keep the original order (the registry's), which is also
 *  what an unsorted table shows. */

export function sortRows(rows, column, dir) {
  if (!column || !dir) return rows.slice();
  const sign = dir === "asc" ? 1 : -1;
  const keyed = rows.map((row, i) => ({ row, i, v: norm(column.get(row), column.kind) }));
  keyed.sort((a, b) => {
    const an = a.v === null, bn = b.v === null;
    if (an && bn) return a.i - b.i;
    if (an) return 1;
    if (bn) return -1;
    let c;
    if (column.kind === "num") c = a.v - b.v;
    else c = a.v < b.v ? -1 : a.v > b.v ? 1 : 0;
    return c === 0 ? a.i - b.i : c * sign;
  });
  return keyed.map((k) => k.row);
}

function norm(v, kind) {
  if (v === null || v === undefined || v === "") return null;
  if (kind === "num") {
    const n = Number(v);
    return Number.isNaN(n) ? null : n;
  }
  return String(v).toLowerCase();
}

/** The next state when a header is clicked: a new column starts at its natural
 *  direction (numbers high-to-low, text A-to-Z); the same column flips; a third
 *  click clears the sort (the table returns to its registry order). */
export function nextSort(current, column) {
  const natural = column.kind === "num" ? "desc" : "asc";
  if (!current || current.key !== column.key) return { key: column.key, dir: natural };
  if (current.dir === natural) return { key: column.key, dir: natural === "asc" ? "desc" : "asc" };
  return null;
}

/** Sort state <-> the URL query (`?sort=mean&dir=desc`), so a reload keeps it.
 *  Unknown columns and directions read as "no sort"; every other query
 *  parameter (the dashboard's `?api=` among them) is left alone. */
export function readSort(search, columns) {
  const q = new URLSearchParams(search);
  const key = q.get("sort");
  const dir = q.get("dir");
  if (!key || !columns.some((c) => c.key === key)) return null;
  return { key, dir: dir === "asc" ? "asc" : "desc" };
}

export function writeSort(search, sort) {
  const q = new URLSearchParams(search);
  if (sort) {
    q.set("sort", sort.key);
    q.set("dir", sort.dir);
  } else {
    q.delete("sort");
    q.delete("dir");
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}
