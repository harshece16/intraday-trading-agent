"""
Generate today's Kite Connect access token from the command line.

Kite Connect sessions expire daily, so this (or the dashboard's "Connect
Kite" button, which does the same thing without leaving the browser — see
app.py's /kite/login and /kite/callback) needs to run each morning before
trading live. It writes the token via config.save_kite_session(), which
config.py reads automatically on next import — no manual export needed.

Before running this for the first time:
  1. Sign up at https://developers.kite.trade (needs your Zerodha login +
     the paid Kite Connect subscription).
  2. Create an app to get an API key + API secret. Set its "Redirect URL"
     to whatever config.KITE_REDIRECT_URL prints below if you also plan to
     use the in-app "Connect Kite" button.
  3. Whitelist a static IP under that app's settings — SEBI's retail algo
     rules require this, and live orders will be rejected without it.
  4. Export KITE_API_KEY and KITE_API_SECRET (only needed once, not daily —
     these don't expire, unlike the access token):
       export KITE_API_KEY="..."
       export KITE_API_SECRET="..."

Usage:
    python generate_access_token.py
"""

import sys
import webbrowser

import config


def main():
    if not config.KITE_API_KEY or not config.KITE_API_SECRET:
        print("Set KITE_API_KEY and KITE_API_SECRET first (see this file's docstring).")
        sys.exit(1)

    from kiteconnect import KiteConnect

    kite = KiteConnect(api_key=config.KITE_API_KEY)
    login_url = kite.login_url()

    print(f"Opening Kite login in your browser:\n  {login_url}\n")
    print("Log in, and after you're redirected, copy the FULL redirect URL")
    print("from your browser's address bar (it will contain request_token=...).")
    webbrowser.open(login_url)

    pasted = input("\nPaste the redirect URL (or just the request_token): ").strip()
    request_token = pasted
    if "request_token=" in pasted:
        request_token = pasted.split("request_token=")[1].split("&")[0]

    session = kite.generate_session(request_token, api_secret=config.KITE_API_SECRET)
    config.save_kite_session(session["access_token"])

    print(f"\nSaved to {config.SESSION_FILE}. Valid for today's session only — re-run this tomorrow.")


if __name__ == "__main__":
    main()
