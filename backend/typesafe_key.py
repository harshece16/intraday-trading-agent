"""
Store the TypeSafe API key for the Jev book (README section 86) without it
appearing in shell history, process arguments or logs.

    pbpaste | backend/.venv/bin/python backend/typesafe_key.py set    # key copied to the clipboard
    backend/.venv/bin/python backend/typesafe_key.py set              # hidden prompt, in a real terminal
    backend/.venv/bin/python backend/typesafe_key.py status           # stored or not; never prints the key
    backend/.venv/bin/python backend/typesafe_key.py test             # one tiny request to TypeSafe

The key is written to backend/.typesafe_key.json with mode 0600 (git-ignored).
TYPESAFE_API_KEY in the environment takes precedence.
"""

import getpass
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import jev_book  # noqa: E402


def set_key(stream=None, path=None):
    stream = stream or sys.stdin
    path = path or jev_book.KEY_PATH
    raw = getpass.getpass("TypeSafe API key (hidden): ") if stream.isatty() else stream.read()
    key = (raw or "").strip()
    if not key or any(c.isspace() for c in key):
        print("No usable key read; nothing stored.")
        return 1
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump({"key": key}, fh)
    os.replace(tmp, path)
    os.chmod(path, 0o600)
    print(f"Stored a {len(key)}-character key in {path} (readable only by you).")
    return 0


def status():
    if os.environ.get("TYPESAFE_API_KEY"):
        src = "TYPESAFE_API_KEY"
    elif os.path.exists(jev_book.KEY_PATH):
        src = jev_book.KEY_PATH
    else:
        src = None
    print(json.dumps({"stored": bool(jev_book.api_key()), "source": src}))
    return 0 if src else 1


def test():
    resp, err = jev_book.system_one("This is a connectivity test for Trader Sahab's Jev book.",
                                    {"test": {"type": "noul", "instructions": "Is this a connectivity test?"}},
                                    jev_book.cfg())
    if err:
        print(json.dumps({"ok": False, "error": err}))
        return 1
    print(json.dumps({"ok": True, "model": resp.get("model"), "answer": (resp.get("answers") or {}).get("test"),
                      "usage": resp.get("usage")}))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    sys.exit({"set": set_key, "status": status, "test": test}.get(cmd, status)())
