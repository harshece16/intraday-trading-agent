import { openKiteLogin, useAction } from "../api";

/** Connect / Reconnect Kite. Says "Opening Kite…" while the backend opens its
 *  tunnel, and says why when the login can't start, e.g. a blocked pop-up (#241). */
export default function KiteConnectButton({ label, className = "btn", title }) {
  const login = useAction(openKiteLogin);
  return (
    <span className="kite-connect">
      <button className={className} title={title} disabled={login.busy} onClick={login.run}>
        {login.busy ? "Opening Kite…" : label}
      </button>
      {login.error && <span className="kite-connect-error down" role="alert">{login.error}</span>}
    </span>
  );
}
