/**
 * Browser push notifications for trade fills, risk warnings, and price moves
 * — entirely client-side, off the same WebSocket-streamed state every page
 * already reads. Nothing here invents a signal: a trade/risk notification
 * just surfaces an activity-log line the engine already wrote for a real
 * action it actually took, and a price-move notification only fires off a
 * real ltp change against a real ATR%-derived threshold.
 */

const ENABLED_KEY = "sahab_notify_enabled";

export function supported() {
  return typeof window !== "undefined" && "Notification" in window;
}

// Storage can be blocked (privacy settings, some embedded views); reading it
// unguarded on every state push white-screened the page (#240).
let flagInMemory = null; // the choice, for this tab, when storage is blocked
function readFlag() {
  try { return localStorage.getItem(ENABLED_KEY) ?? flagInMemory; } catch { return flagInMemory; }
}
function writeFlag(v) {
  flagInMemory = v;
  try { localStorage.setItem(ENABLED_KEY, v); } catch { /* storage blocked: kept in memory */ }
}

export function enabled() {
  return supported() && readFlag() === "1" && Notification.permission === "granted";
}

export async function enable() {
  if (!supported()) return false;
  const perm = await Notification.requestPermission();
  if (perm === "granted") {
    writeFlag("1");
    return true;
  }
  return false;
}

export function disable() {
  writeFlag("0");
}

export function fire(title, body, tag) {
  if (!enabled()) return;
  try {
    new Notification(title, { body, tag });
  } catch (e) {
    /* some browsers restrict constructing Notification directly; safe to skip */
  }
}
