#!/usr/bin/env python3
"""
probe.py - verify the state board disciplinary-action registry from a machine
with real network access.

WHY THIS EXISTS
---------------
registry.json was compiled from web search results only. The environment it was
compiled in blocks outbound HTTPS to state government hosts, so not one of those
URLs was actually fetched. This script does the fetching, and turns each entry
from "a lead" into "confirmed / moved / gone".

It is deliberately read-only and polite: it checks robots.txt before every fetch,
identifies itself honestly, sleeps between requests, and never follows a form or
submits a query. It collects NO case data - it only characterises each page so
you can decide which states are worth writing an extractor for.

USAGE
    python3 probe.py                      # probe every jurisdiction
    python3 probe.py --states FL TX VA    # probe a subset
    python3 probe.py --include-hints      # also test the INFERRED probe_hint URLs
    python3 probe.py --delay 3            # be slower (default 2s between hosts)

OUTPUT
    probe_results.json   full detail per URL
    probe_results.csv    one row per URL, for eyeballing in Excel

Stdlib only - no pip install required.
"""

import argparse
import csv
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "registry.json")

# Identify honestly. A real contact address makes it far more likely that a
# board webmaster emails you instead of silently blocking you.
UA = (
    "LPC-Board-Research-Probe/1.0 "
    "(academic research on published counselor board orders; "
    "contact: richard.strebeck@gmail.com)"
)

TIMEOUT = 30


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------

_robots_cache = {}


def robots_allows(url):
    """Check robots.txt. Returns (allowed, note). Fails OPEN with a note if
    robots.txt itself is unreachable, which is the conventional reading."""
    parts = urllib.parse.urlsplit(url)
    root = f"{parts.scheme}://{parts.netloc}"
    if root not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{root}/robots.txt")
        try:
            rp.read()
            _robots_cache[root] = (rp, "robots.txt read")
        except Exception as exc:  # noqa: BLE001
            _robots_cache[root] = (None, f"robots.txt unreachable: {type(exc).__name__}")
    rp, note = _robots_cache[root]
    if rp is None:
        return True, note
    try:
        return rp.can_fetch(UA, url), note
    except Exception:  # noqa: BLE001
        return True, note + " (can_fetch errored)"


def fetch(url):
    """GET a URL. Returns a dict describing what came back."""
    out = {
        "url": url,
        "status": None,
        "final_url": None,
        "content_type": None,
        "bytes": 0,
        "error": None,
        "body": b"",
        "headers_blob": "",
    }
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            body = resp.read(3_000_000)  # cap at 3MB; we only need to characterise
            out.update(
                status=resp.status,
                final_url=resp.geturl(),
                content_type=resp.headers.get("Content-Type", ""),
                bytes=len(body),
                body=body,
                headers_blob="\n".join(f"{k}: {v}" for k, v in resp.headers.items()),
            )
    except urllib.error.HTTPError as exc:
        # A CAPTCHA/bot wall often arrives AS the error page, so keep the body.
        try:
            body = exc.read(500_000)
        except Exception:  # noqa: BLE001
            body = b""
        out.update(
            status=exc.code,
            error=f"HTTPError {exc.code} {exc.reason}",
            body=body,
            content_type=exc.headers.get("Content-Type", "") if exc.headers else "",
            headers_blob="\n".join(f"{k}: {v}" for k, v in (exc.headers or {}).items()),
        )
    except Exception as exc:  # noqa: BLE001
        out.update(error=f"{type(exc).__name__}: {exc}")
    return out


# --------------------------------------------------------------------------
# characterising a page
# --------------------------------------------------------------------------

NAMEY = re.compile(r"[A-Z][a-z]+,\s+[A-Z][a-z]+")          # "Smith, John"
DATEY = re.compile(r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}-\d{2}-\d{2})\b")
SANCTIONY = re.compile(
    r"\b(revocation|revoked|surrender|suspension|suspended|probation|reprimand|"
    r"censure|consent (?:order|agreement)|stipulation|cease and desist|"
    r"voluntar\w+ surrender|final order)\b",
    re.I,
)
JS_SHELL = re.compile(r"(__NEXT_DATA__|ng-app|data-reactroot|window\.__|require\.js|"
                      r"Salesforce|aura_|lightning)", re.I)

# ---- CAPTCHA / bot-wall detection -------------------------------------------
# This is the primary go/no-go filter: a page behind a CAPTCHA is off the table.
CAPTCHA_SIGS = [
    ("recaptcha",      re.compile(r"(recaptcha|g-recaptcha|google\.com/recaptcha)", re.I)),
    ("hcaptcha",       re.compile(r"(hcaptcha|h-captcha)", re.I)),
    ("turnstile",      re.compile(r"(cf-turnstile|challenges\.cloudflare\.com)", re.I)),
    ("cloudflare-jsc", re.compile(r"(cf_chl_|__cf_chl|Checking your browser|cf-browser-verification)", re.I)),
    ("incapsula",      re.compile(r"(_Incapsula_|incap_ses|visid_incap)", re.I)),
    ("akamai",         re.compile(r"(ak_bmsc|_abck|bm_sz)", re.I)),
    ("perimeterx",     re.compile(r"(_px[0-9A-Za-z]*|perimeterx)", re.I)),
    ("datadome",       re.compile(r"datadome", re.I)),
    ("generic-captcha", re.compile(r"(enter the (?:characters|code) (?:you see|below)|"
                                   r"captcha|human verification|verify you are (?:a )?human|"
                                   r"i'?m not a robot)", re.I)),
]

# Not CAPTCHAs, but real friction worth flagging separately.
FRICTION_SIGS = [
    ("aspnet-postback", re.compile(r"__VIEWSTATE|__EVENTVALIDATION|__doPostBack", re.I)),
    ("disclaimer-gate", re.compile(r"(I (?:have read and )?(?:agree|accept)|disclaimer\.jsp|"
                                   r"accept the (?:terms|disclaimer))", re.I)),
    ("session-required", re.compile(r"(session (?:has )?expired|please enable cookies)", re.I)),
]


def detect_walls(text, headers_blob=""):
    """Return (captchas, frictions) found in the page body/headers."""
    blob = text + "\n" + headers_blob
    caps = [name for name, rx in CAPTCHA_SIGS if rx.search(blob)]
    fric = [name for name, rx in FRICTION_SIGS if rx.search(blob)]
    return caps, fric


def characterise(res):
    """Turn a fetched response into scrapability signals."""
    sig = {
        "kind": "unknown",
        "captcha": "",
        "friction": "",
        "pdf_links": 0,
        "total_links": 0,
        "tables": 0,
        "name_like": 0,
        "date_like": 0,
        "sanction_words": 0,
        "js_rendered_suspect": False,
        "year_links": [],
        "verdict": "",
    }
    ctype = (res.get("content_type") or "").lower()
    body = res.get("body") or b""

    if "pdf" in ctype or body[:5] == b"%PDF-":
        sig["kind"] = "pdf"
        sig["verdict"] = "EASY: PDF document - parse with pdfplumber/PyMuPDF"
        return sig

    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        text = ""

    if not text.strip():
        sig["kind"] = "empty"
        sig["verdict"] = "empty body"
        return sig

    # CAPTCHA check happens FIRST - it overrides every other signal.
    caps, fric = detect_walls(text, res.get("headers_blob", ""))
    sig["captcha"] = ",".join(caps)
    sig["friction"] = ",".join(fric)

    sig["kind"] = "html" if "<" in text[:2000] else "text"
    sig["pdf_links"] = len(re.findall(r'href="[^"]+\.pdf', text, re.I))
    sig["total_links"] = len(re.findall(r"<a\s[^>]*href=", text, re.I))
    sig["tables"] = len(re.findall(r"<table\b", text, re.I))

    # strip tags before counting content signals, so nav markup doesn't inflate
    visible = re.sub(r"<script\b.*?</script>", " ", text, flags=re.S | re.I)
    visible = re.sub(r"<style\b.*?</style>", " ", visible, flags=re.S | re.I)
    visible = re.sub(r"<[^>]+>", " ", visible)

    sig["name_like"] = len(NAMEY.findall(visible))
    sig["date_like"] = len(DATEY.findall(visible))
    sig["sanction_words"] = len(SANCTIONY.findall(visible))
    sig["js_rendered_suspect"] = bool(JS_SHELL.search(text)) and len(visible.split()) < 400

    # year-partitioned sibling pages (the NH pattern) are gold for enumeration
    sig["year_links"] = sorted(set(re.findall(r"href=\"[^\"]*?(20\d{2})[^\"]*?\"", text)))[:15]

    # Verdict, easiest-first. CAPTCHA is an absolute veto.
    if caps:
        sig["verdict"] = f"CAPTCHA/BOT-WALL ({','.join(caps)}) - EXCLUDE"
    elif sig["js_rendered_suspect"]:
        sig["verdict"] = "HARD: JS-rendered shell - needs headless browser"
    elif sig["pdf_links"] >= 5 and sig["sanction_words"] >= 1:
        sig["verdict"] = "EASY: index of linked order PDFs"
    elif sig["tables"] >= 1 and sig["name_like"] >= 5:
        sig["verdict"] = "EASY: HTML table of cases"
    elif sig["name_like"] >= 5 and sig["date_like"] >= 5:
        sig["verdict"] = "MODERATE: name+date listing, check layout"
    elif sig["sanction_words"] >= 3:
        sig["verdict"] = "MODERATE: sanction language present"
    elif "aspnet-postback" in fric or "disclaimer-gate" in fric:
        sig["verdict"] = f"MODERATE: form/gate friction ({','.join(fric)}), no CAPTCHA"
    elif sig["pdf_links"] >= 1:
        sig["verdict"] = "WEAK: few PDF links - may be forms not orders"
    else:
        sig["verdict"] = "WEAK: no case-like content detected"
    return sig


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--states", nargs="*", help="state names or 2-letter-ish prefixes to filter")
    ap.add_argument("--include-hints", action="store_true",
                    help="also probe the INFERRED probe_hint URLs (Idaho, NJ, SC)")
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between requests to same host")
    ap.add_argument("--registry", default=REGISTRY)
    args = ap.parse_args()

    with open(args.registry, encoding="utf-8") as fh:
        reg = json.load(fh)

    jurisdictions = reg["jurisdictions"]
    if args.states:
        wanted = [s.lower() for s in args.states]
        jurisdictions = [
            j for j in jurisdictions
            if any(j["state"].lower().startswith(w) or w in j["state"].lower() for w in wanted)
        ]

    # build the work list
    work = []
    for j in jurisdictions:
        if j.get("status", "").startswith("ALREADY IN DATASET"):
            continue
        for url in j.get("discipline_urls", []):
            work.append((j["state"], url, "registry"))
        if args.include_hints and j.get("probe_hint"):
            m = re.match(r"(https?://\S+?)\s", j["probe_hint"] + " ")
            if m:
                work.append((j["state"], m.group(1), "INFERRED-hint"))

    if not work:
        print("nothing to probe", file=sys.stderr)
        return 1

    print(f"probing {len(work)} URLs across "
          f"{len({w[0] for w in work})} jurisdictions\n", file=sys.stderr)

    last_hit = defaultdict(float)
    results = []

    for i, (state, url, source) in enumerate(work, 1):
        host = urllib.parse.urlsplit(url).netloc
        wait = args.delay - (time.time() - last_hit[host])
        if wait > 0:
            time.sleep(wait)

        allowed, robots_note = robots_allows(url)
        row = {
            "state": state,
            "url": url,
            "source": source,
            "robots_allowed": allowed,
            "robots_note": robots_note,
        }

        if not allowed:
            row.update(status="SKIPPED", verdict="robots.txt disallows - DO NOT SCRAPE")
            results.append(row)
            print(f"[{i}/{len(work)}] {state:22} ROBOTS-DISALLOW {url}", file=sys.stderr)
            continue

        res = fetch(url)
        last_hit[host] = time.time()
        sig = characterise(res)

        row.update(
            status=res["status"],
            final_url=res["final_url"],
            content_type=res["content_type"],
            bytes=res["bytes"],
            error=res["error"],
            **{k: v for k, v in sig.items() if k != "year_links"},
        )
        row["year_links"] = ",".join(sig["year_links"])
        results.append(row)

        flag = "OK " if res["status"] == 200 else f"{res['status'] or 'ERR'}"
        print(f"[{i}/{len(work)}] {state:22} {flag:4} {sig['verdict'][:52]:54} {url}",
              file=sys.stderr)

    # write outputs
    with open(os.path.join(HERE, "probe_results.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    cols = ["state", "source", "status", "verdict", "captcha", "friction", "kind",
            "pdf_links", "tables", "name_like", "date_like", "sanction_words",
            "js_rendered_suspect", "year_links", "robots_allowed", "robots_note",
            "bytes", "content_type", "error", "url", "final_url"]
    with open(os.path.join(HERE, "probe_results.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)

    # summary - CAPTCHA first, since that is the go/no-go the project cares about
    captcha_hits = [r for r in results if r.get("captcha")]
    easy = [r for r in results if str(r.get("verdict", "")).startswith("EASY")]
    moderate = [r for r in results if str(r.get("verdict", "")).startswith("MODERATE")]
    hard = [r for r in results if str(r.get("verdict", "")).startswith("HARD")]
    dead = [r for r in results if r.get("status") not in (200, "SKIPPED")]
    blocked = [r for r in results if r.get("robots_allowed") is False]

    def states(rows):
        return ", ".join(sorted({r["state"] for r in rows})) or "-"

    print("\n" + "=" * 74, file=sys.stderr)
    print(f"probed          : {len(results)} URLs", file=sys.stderr)
    print(f"CAPTCHA/BOT-WALL: {len(captcha_hits):3}  -> {states(captcha_hits)}", file=sys.stderr)
    print(f"EASY            : {len(easy):3}  -> {states(easy)}", file=sys.stderr)
    print(f"MODERATE        : {len(moderate):3}  -> {states(moderate)}", file=sys.stderr)
    print(f"HARD (JS)       : {len(hard):3}  -> {states(hard)}", file=sys.stderr)
    print(f"non-200/error   : {len(dead):3}  -> {states(dead)}", file=sys.stderr)
    print(f"robots-blocked  : {len(blocked):3}  -> {states(blocked)}", file=sys.stderr)

    print("\nSCRAPE ORDER (states with at least one EASY, no CAPTCHA on that URL):",
          file=sys.stderr)
    clean = sorted({r["state"] for r in easy if not r.get("captcha")})
    for s in clean:
        print(f"  - {s}", file=sys.stderr)

    print("\nwrote probe_results.json and probe_results.csv", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
