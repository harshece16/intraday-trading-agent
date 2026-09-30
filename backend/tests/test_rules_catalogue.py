"""The rules catalogue (docs/architecture/rules.json) must stay true to the code.

Every rule names the code that enforces it and, where one exists, the test
that covers it. These tests fail when a rule points at a file, function or
test that no longer exists, and when the generated pages (RULES.md,
rules.html) are out of date with the catalogue.
"""
import importlib.util
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARCH = os.path.join(ROOT, "docs", "architecture")
STATUSES = {"active", "paper-only", "off-by-default", "pending", "retired"}
CODE_REF = re.compile(r"((?:backend|frontend|scripts|tools)/[\w./\-]+\.(?:py|jsx|js|sh)):([A-Za-z_][\w.]*)")
PATH_REF = re.compile(r"(?<![\w./\-])((?:backend|frontend|docs|scripts|tools|\.github|\.claude)/[\w./\-]+"
                      r"\.(?:json|jsx|yml|yaml|plist|py|js|md|sh|csv))(?![\w\-])")


def _catalogue():
    with open(os.path.join(ARCH, "rules.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


def _builder():
    spec = importlib.util.spec_from_file_location("build_rules_docs", os.path.join(ROOT, "tools", "build_rules_docs.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_rule_is_complete_and_uniquely_named():
    cat = _catalogue()
    prefix = {a["id"]: a["prefix"] for a in cat["areas"]}
    seen = set()
    for r in cat["rules"]:
        assert r["id"] not in seen, "duplicate rule id %s" % r["id"]
        seen.add(r["id"])
        assert r["area"] in prefix, "%s: unknown area %r" % (r["id"], r["area"])
        assert r["id"].startswith(prefix[r["area"]] + "-"), "%s does not carry its area's prefix" % r["id"]
        assert r["status"] in STATUSES, "%s: unknown status %r" % (r["id"], r["status"])
        for field in ("rule", "why", "enforced_in", "verify"):
            assert (r.get(field) or "").strip(), "%s has no %s" % (r["id"], field)
        for n in r.get("issues", []):
            assert isinstance(n, int) and n > 0, "%s: bad issue number %r" % (r["id"], n)
    assert len(seen) >= 200


def test_every_rule_points_at_code_that_exists():
    missing = []
    for r in _catalogue()["rules"]:
        where = r["enforced_in"]
        for path in PATH_REF.findall(where):
            if not os.path.exists(os.path.join(ROOT, path)):
                missing.append("%s: no file %s" % (r["id"], path))
        for path, symbol in CODE_REF.findall(where):
            if not os.path.exists(os.path.join(ROOT, path)):
                continue                                     # already reported above
            name = symbol.split(".")[-1]
            if name not in _read(path):
                missing.append("%s: %s has no %s" % (r["id"], path, name))
    assert not missing, "\n".join(missing)


def test_every_named_test_exists():
    missing = []
    for r in _catalogue()["rules"]:
        for part in re.split(r"[;,]\s*", r.get("test") or ""):
            part = part.strip()
            if not part:
                continue
            m = re.match(r"^([\w./\-]+\.py)(?:::(\w+))?", part)
            if not m:
                missing.append("%s: unreadable test reference %r" % (r["id"], part))
                continue
            path, name = m.group(1), m.group(2)
            if not os.path.exists(os.path.join(ROOT, path)):
                missing.append("%s: no test file %s" % (r["id"], path))
            elif name and ("def %s(" % name) not in _read(path):
                missing.append("%s: %s has no %s" % (r["id"], path, name))
    assert not missing, "\n".join(missing)


def test_generated_pages_match_the_catalogue():
    assert _builder().main(["--check"]) == 0, "run: python3 tools/build_rules_docs.py"


def test_design_documents_link_to_files_that_exist():
    broken = []
    for name in ("README.md", "HLD.md", "LLD.md", "RULES.md", "KNOWLEDGE_GRAPH.md"):
        text = _read(os.path.join("docs", "architecture", name))
        for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
            if re.match(r"^[a-z]+://", target):
                continue
            if not os.path.exists(os.path.normpath(os.path.join(ARCH, target))):
                broken.append("%s links to %s" % (name, target))
    assert not broken, "\n".join(broken)


def test_the_page_draws_every_diagram_in_the_high_level_design():
    mod = _builder()
    figures = mod.hld_figures(_read(os.path.join("docs", "architecture", "HLD.md")))
    assert len(figures) >= 6 and all(f["title"] and f["source"].strip() for f in figures)
    assert len(mod.hld_day_table(_read(os.path.join("docs", "architecture", "HLD.md")))) >= 10
    page = _read(os.path.join("docs", "architecture", "rules.html"))
    assert page.count('<pre class="mermaid">') == len(figures)
