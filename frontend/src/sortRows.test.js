/* Run with: npm test  (node:test, no framework needed)
 *
 * The rule-lab table sorts on every column (README section 129). The parts
 * that can go quietly wrong are pure, so they are tested here: numbers must
 * sort as numbers (not "9" after "10"), a "—" cell must sit at the bottom in
 * both directions, ties must keep the registry's order, and the URL round
 * trip must not drop the dashboard's other query parameters.
 */

import assert from "node:assert/strict";
import test from "node:test";
import { nextSort, readSort, sortRows, writeSort } from "./sortRows.js";

const MEAN = { key: "mean", get: (r) => r.mean, kind: "num" };
const NAME = { key: "name", get: (r) => r.name, kind: "text" };
const COLUMNS = [MEAN, NAME];
const rows = [
  { rule: "R01", name: "beta", mean: 9 },
  { rule: "R02", name: "Alpha", mean: null },
  { rule: "R03", name: "gamma", mean: 10 },
  { rule: "R04", name: "delta", mean: -2.5 },
  { rule: "R05", name: "beta", mean: undefined },
];

test("numbers sort numerically, nulls last in both directions", () => {
  assert.deepEqual(sortRows(rows, MEAN, "desc").map((r) => r.rule), ["R03", "R01", "R04", "R02", "R05"]);
  assert.deepEqual(sortRows(rows, MEAN, "asc").map((r) => r.rule), ["R04", "R01", "R03", "R02", "R05"]);
});

test("text sorts case-insensitively and ties keep the registry order", () => {
  assert.deepEqual(sortRows(rows, NAME, "asc").map((r) => r.rule), ["R02", "R01", "R05", "R04", "R03"]);
  assert.deepEqual(sortRows(rows, NAME, "desc").map((r) => r.rule), ["R03", "R04", "R01", "R05", "R02"]);
});

test("no sort returns a copy in the original order", () => {
  const out = sortRows(rows, null, null);
  assert.deepEqual(out.map((r) => r.rule), ["R01", "R02", "R03", "R04", "R05"]);
  assert.notEqual(out, rows);
});

test("a header click starts at the natural direction, flips, then clears", () => {
  assert.deepEqual(nextSort(null, MEAN), { key: "mean", dir: "desc" });
  assert.deepEqual(nextSort({ key: "mean", dir: "desc" }, MEAN), { key: "mean", dir: "asc" });
  assert.equal(nextSort({ key: "mean", dir: "asc" }, MEAN), null);
  assert.deepEqual(nextSort({ key: "mean", dir: "asc" }, NAME), { key: "name", dir: "asc" });
});

test("the URL round trip keeps other query parameters and rejects unknown columns", () => {
  const search = "?api=http%3A%2F%2F127.0.0.1%3A8001&sort=mean&dir=asc";
  assert.deepEqual(readSort(search, COLUMNS), { key: "mean", dir: "asc" });
  assert.equal(readSort("?sort=bogus&dir=asc", COLUMNS), null);
  assert.deepEqual(readSort("?sort=name&dir=sideways", COLUMNS), { key: "name", dir: "desc" });
  const written = writeSort(search, { key: "name", dir: "desc" });
  assert.deepEqual(readSort(written, COLUMNS), { key: "name", dir: "desc" });
  assert.equal(new URLSearchParams(written).get("api"), "http://127.0.0.1:8001");
  const cleared = writeSort(written, null);
  assert.equal(readSort(cleared, COLUMNS), null);
  assert.equal(cleared, "?api=http%3A%2F%2F127.0.0.1%3A8001");
  assert.equal(writeSort("?sort=mean&dir=desc", null), "");
});
