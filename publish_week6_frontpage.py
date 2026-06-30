#!/usr/bin/env python3
"""
Publish COU 507 Week 6 Front Page to Canvas.

Usage:
    CANVAS_TOKEN=your_token python3 publish_week6_frontpage.py

The script will:
  1. Fetch quiz details from Canvas to fill in the quiz pill.
  2. Fetch the VoiceThread assignment due date to confirm.
  3. Build the page HTML.
  4. Create the page (published, set as front page).
  5. Set the course default view to wiki.
  6. Verify and print the html_url.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TOKEN = os.environ.get("CANVAS_TOKEN", "")
if not TOKEN:
    sys.exit("ERROR: CANVAS_TOKEN environment variable is not set.")

BASE = "https://wmcarey.instructure.com/api/v1"
COURSE_ID = 78693
QUIZ_ID = 236627
VT_ASSIGNMENT_ID = 752629
VT_LINK = f"https://wmcarey.instructure.com/courses/{COURSE_ID}/assignments/{VT_ASSIGNMENT_ID}"
QUIZ_LINK = f"https://wmcarey.instructure.com/courses/{COURSE_ID}/quizzes/{QUIZ_ID}"


def api(method, path, data=None):
    """Make a Canvas API request. Returns parsed JSON."""
    url = BASE + path
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        sys.exit(f"HTTP {e.code} on {method} {path}:\n{body_text}")


def fmt_due(iso_str):
    """Format an ISO 8601 due-date string to a readable local label."""
    if not iso_str:
        return "No due date"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        # Display in Central Time (UTC-5 summer / UTC-6 standard).
        # Canvas stores UTC; shift for display only.
        from datetime import timedelta
        central = dt - timedelta(hours=5)  # CDT
        return central.strftime("%A, %B %-d, %Y, %-I:%M %p") + " CDT"
    except Exception:
        return iso_str


# ---------------------------------------------------------------------------
# Step 1 – Fetch live data
# ---------------------------------------------------------------------------
print("Fetching quiz details...")
quiz = api("GET", f"/courses/{COURSE_ID}/quizzes/{QUIZ_ID}")
quiz_title = quiz.get("title", "Quiz")
quiz_points = int(quiz.get("points_possible", 0))
quiz_due_raw = quiz.get("due_at") or quiz.get("lock_at")
quiz_due_label = fmt_due(quiz_due_raw)

print(f"  Quiz title : {quiz_title}")
print(f"  Points     : {quiz_points}")
print(f"  Due        : {quiz_due_label}")

print("\nFetching VoiceThread assignment details...")
vt = api("GET", f"/courses/{COURSE_ID}/assignments/{VT_ASSIGNMENT_ID}")
vt_title = vt.get("name", "VoiceThread Discussion")
vt_due_raw = vt.get("due_at")
vt_due_label = fmt_due(vt_due_raw)

print(f"  VT title   : {vt_title}")
print(f"  VT due     : {vt_due_label}")

# Due-date labels used in the HTML
# Override with the faculty-confirmed dates if Canvas shows something different.
VT_DUE_DISPLAY = "Sunday, July 6, 2026, 11:59 PM CDT"
QUIZ_DUE_DISPLAY = quiz_due_label

print(f"\nVoiceThread due date will display as: {VT_DUE_DISPLAY}")
print(f"Quiz due date will display as:        {QUIZ_DUE_DISPLAY}")
confirm = input("\nContinue and publish? [y/N] ").strip().lower()
if confirm != "y":
    sys.exit("Aborted by user.")

# ---------------------------------------------------------------------------
# Step 2 – Build HTML
# ---------------------------------------------------------------------------
HTML = f"""<div style="font-family:Arial,sans-serif;max-width:780px;margin:0 auto;padding:16pt 8pt;">

  <!-- ===== HEADER ===== -->
  <div style="background:#185FA5;border-radius:12px;padding:1.5rem 1rem;text-align:center;margin-bottom:1.25rem;">
    <div style="font-size:16pt;color:#E6F1FB;margin-bottom:4px;"><strong>Week 6</strong></div>
    <div style="font-size:24pt;color:#ffffff;margin-bottom:6px;"><strong>Week 6 Update Summer</strong></div>
    <div style="font-size:14pt;color:#B5D4F4;">COU 507 &middot; Human Growth and Development</div>
  </div>

  <!-- ===== ANNOUNCEMENT CARD ===== -->
  <div style="background:#ffffff;border:1px solid #e0e0e0;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1rem;">

    <!-- Card header row -->
    <div style="display:table;width:100%;border-bottom:1px solid #e8e8e8;padding-bottom:0.75rem;margin-bottom:1rem;">
      <div style="display:table-cell;vertical-align:middle;width:46px;">
        <span style="display:inline-block;width:36px;height:36px;border-radius:50%;background:#E6F1FB;text-align:center;line-height:36px;font-size:18pt;">&#128226;</span>
      </div>
      <div style="display:table-cell;vertical-align:middle;">
        <span style="font-size:18pt;"><strong>Class Update &ndash; Week 6</strong></span>
      </div>
    </div>

    <!-- Body -->
    <p style="font-size:18pt;margin:0 0 0.75rem 0;">Tonight&rsquo;s in-person class is canceled. We are meeting asynchronously this week instead.</p>

    <p style="font-size:18pt;margin:0 0 1rem 0;">
      In place of our class meeting, you will complete a <strong>VoiceThread case discussion</strong> worth <strong>20 points</strong>.
      This discussion centers on early and middle adulthood through a couples case study (Daniel and Renee).
      You will respond to four discussion questions from the perspective of the counselor.
    </p>

    <!-- VoiceThread button -->
    <div style="margin-bottom:0.75rem;">
      <span style="display:inline-block;background:#EAF3DE;padding:8px 18px;border-radius:8px;">
        <a href="{VT_LINK}" target="_blank" rel="noopener"
           style="color:#3B6D11;text-decoration:none;font-size:13pt;">
          <strong>&#128221; Open VoiceThread Case Discussion</strong>
        </a>
      </span>
    </div>

    <!-- Due-date tile -->
    <div style="background:#FAEEDA;border-radius:8px;padding:10px 14px;font-size:13pt;display:inline-block;">
      <strong>Due:</strong> {VT_DUE_DISPLAY}
    </div>

  </div>

  <!-- ===== QUIZ PILL ===== -->
  <div style="background:#ffffff;border:1px solid #e0e0e0;border-radius:12px;padding:0.75rem 1.25rem;margin-bottom:1.25rem;">
    <span style="font-size:14pt;"><strong>&#128203; Quiz:</strong></span>
    <span style="font-size:14pt;"> {quiz_title} &middot; {quiz_points} pts</span>
    <span style="font-size:13pt;color:#666;"> &mdash; Due: {QUIZ_DUE_DISPLAY}</span>
    <span style="margin-left:12px;">
      <span style="display:inline-block;background:#E6F1FB;padding:4px 12px;border-radius:8px;">
        <a href="{QUIZ_LINK}" target="_blank" rel="noopener"
           style="color:#185FA5;text-decoration:none;font-size:12pt;"><strong>Take Quiz</strong></a>
      </span>
    </span>
  </div>

  <!-- ===== FOOTER ===== -->
  <div style="text-align:center;border-top:1px solid #e0e0e0;padding-top:1rem;">
    <div style="font-size:14pt;"><strong>COU 507 &middot; Human Growth and Development</strong></div>
    <div style="font-size:12pt;color:#888;margin-top:4px;">Richard Strebeck, PhD, LPC-S, NCC, CSAT, BC-TMH</div>
  </div>

</div>"""

print("\n" + "=" * 60)
print("PREVIEW – HTML to be published")
print("=" * 60)
print(HTML)
print("=" * 60)
approve = input("\nApprove this HTML and publish to Canvas? [y/N] ").strip().lower()
if approve != "y":
    sys.exit("Aborted by user.")

# ---------------------------------------------------------------------------
# Step 3 – Create the page
# ---------------------------------------------------------------------------
print("\nCreating Canvas page...")
page_data = {
    "wiki_page": {
        "title": "Week 6 Update Summer",
        "body": HTML,
        "published": True,
        "front_page": True,
    }
}
try:
    page = api("POST", f"/courses/{COURSE_ID}/pages", page_data)
    page_url = page.get("url")
    print(f"  Page created. Slug: {page_url}")
except SystemExit as e:
    msg = str(e)
    if "front_page" in msg.lower() or "400" in msg:
        # Fall back: create without front_page, then promote
        print("  Front page conflict -- creating without front_page flag, then promoting...")
        page_data["wiki_page"].pop("front_page")
        page = api("POST", f"/courses/{COURSE_ID}/pages", page_data)
        page_url = page.get("url")
        print(f"  Page created. Slug: {page_url}")
        print("  Promoting to front page...")
        api("PUT", f"/courses/{COURSE_ID}/pages/{page_url}",
            {"wiki_page": {"front_page": True}})
    else:
        raise

# ---------------------------------------------------------------------------
# Step 4 – Set default view to wiki
# ---------------------------------------------------------------------------
print("Setting course default view to wiki...")
api("PUT", f"/courses/{COURSE_ID}", {"course": {"default_view": "wiki"}})
print("  Done.")

# ---------------------------------------------------------------------------
# Step 5 – Verify
# ---------------------------------------------------------------------------
print("Verifying front page...")
front = api("GET", f"/courses/{COURSE_ID}/front_page")
assert front.get("title") == "Week 6 Update Summer", f"Unexpected title: {front.get('title')}"
assert front.get("front_page") is True, "front_page flag not set"
html_url = front.get("html_url")

print("\n" + "=" * 60)
print("SUCCESS")
print(f"Front page URL: {html_url}")
print("=" * 60)
