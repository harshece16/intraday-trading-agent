/* Run with: npm test  (node:test, no framework needed)
 *
 * These exist because of a real regression. `describeKite` did
 * `KITE_STATES[k.state] || KITE_STATES.disconnected`, so a backend older than
 * the frontend — which is every backend between a frontend deploy and a
 * backend restart — sent no `state` and the dashboard reported "Kite not
 * connected" over a live, working session. That is the same confidently-wrong
 * display this module was written to prevent, with the sign flipped.
 */

import assert from "node:assert/strict";
import test from "node:test";

import { describeKite, relativeDuration } from "./kiteStatus.js";

const REDIRECT = "http://127.0.0.1:8000/kite/callback";

test("legacy payload with no `state` and a live session reads as connected", () => {
  // Byte-for-byte what the pre-#52 backend returned while Kite was working.
  const k = describeKite({
    app_configured: true, connected: true, using_live_data: true,
    generated_at: "2026-09-21T03:46:11.127208+00:00", redirect_url: REDIRECT,
  });
  assert.equal(k.label, "Kite: live prices");
  assert.equal(k.tone, "ok");
  assert.equal(k.urgent, false);
  assert.match(k.detail, /Live prices/);
});

test("legacy payload, logged out, reads as disconnected rather than connected", () => {
  const k = describeKite({ app_configured: true, connected: false, using_live_data: false });
  assert.equal(k.label, "Kite not connected");
  assert.equal(k.tone, "idle");
});

test("legacy payload with no API key reads as not configured", () => {
  const k = describeKite({ app_configured: false, connected: false });
  assert.equal(k.label, "Delayed prices");
});

test("legacy payload connected but on the delayed feed is amber, not green", () => {
  const k = describeKite({ app_configured: true, connected: true, using_live_data: false });
  assert.equal(k.label, "Kite: delayed prices");
  assert.equal(k.tone, "warn");
});

test("an expired session is red and urgent", () => {
  const k = describeKite({
    state: "expired", connected: false, app_configured: true,
    reason: "This Kite session expired at the 06:00 IST daily cutoff.",
    generated_at: "2026-09-19T21:34:50.142346+00:00",
    expires_at: "2026-09-20T06:00:00+05:30", seconds_until_expiry: -92920,
    redirect_url: REDIRECT,
  });
  assert.equal(k.label, "Kite session expired");
  assert.equal(k.tone, "bad");
  assert.equal(k.urgent, true);
  assert.match(k.detail, /Expired/);
});

test("a stalled login is its own failure, not a plain disconnection", () => {
  const k = describeKite({
    state: "disconnected", connected: false, app_configured: true,
    login_stalled: true, reason: "A Kite login was started but Zerodha never came back.",
    redirect_url: REDIRECT,
  });
  assert.equal(k.label, "Kite login didn't return");
  assert.equal(k.tone, "bad");
  assert.equal(k.urgent, true);
  assert.equal(k.loginStalled, true);
});

test("the redirect URL is shown when disconnected and hidden when connected", () => {
  const off = describeKite({ state: "disconnected", app_configured: true, connected: false,
                             redirect_url: REDIRECT });
  assert.match(off.detail, /developers\.kite\.trade/);
  assert.ok(off.detail.includes(REDIRECT));

  const on = describeKite({ state: "connected", app_configured: true, connected: true,
                            using_live_data: true, redirect_url: REDIRECT });
  assert.ok(!on.detail.includes(REDIRECT), "a working session proves the redirect is fine");
});

test("a null payload is a loading state, never a failure", () => {
  const k = describeKite(null);
  assert.equal(k.loading, true);
  assert.equal(k.urgent, false);
  assert.equal(k.label, "Checking Kite…");
});

test("an unknown future state degrades to disconnected rather than throwing", () => {
  const k = describeKite({ state: "something_new", app_configured: true, connected: false });
  assert.equal(k.tone, "idle");
  assert.equal(k.loading, false);
});

test("relativeDuration reads forwards and backwards", () => {
  assert.equal(relativeDuration(3600 * 6 + 60 * 20), "in 6h 20m");
  assert.equal(relativeDuration(-92920), "25h 48m ago");
  assert.equal(relativeDuration(30), "in 1m");
  assert.equal(relativeDuration(null), null);
});
