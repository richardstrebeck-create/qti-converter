#!/usr/bin/env python3
"""
Check whether Microsoft Teams Assignments LTI / Microsoft Education
is enabled in a Canvas course.

Usage:
    CANVAS_TOKEN=your_token python3 check_lti_tools.py

Or point it at a token file:
    python3 check_lti_tools.py --token-file "C:/Users/richa/OneDrive - WCU/Claude/canvas_token.txt"
"""

import os
import sys
import json
import urllib.request
import urllib.error
import argparse

COURSE_ID = 78621
BASE = "https://wmcarey.instructure.com/api/v1"

# Keywords that identify Microsoft Teams / Education LTI tools
MS_KEYWORDS = [
    "microsoft", "teams", "education", "office 365", "o365", "msteams",
    "assignments lti",
]


def get_token(token_file=None):
    if token_file:
        try:
            with open(token_file) as f:
                return f.read().strip()
        except FileNotFoundError:
            sys.exit(f"ERROR: Token file not found: {token_file}")
    token = os.environ.get("CANVAS_TOKEN", "")
    if not token:
        sys.exit("ERROR: Set CANVAS_TOKEN env var or pass --token-file.")
    return token


def api_get(path, token):
    url = BASE + path
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), resp.getheader("Link", "")
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on GET {path}:\n{e.read().decode(errors='replace')}")


def get_all_pages(path, token):
    results = []
    while path:
        data, link_header = api_get(path, token)
        if isinstance(data, list):
            results.extend(data)
        else:
            results.append(data)
        # Follow Canvas pagination
        next_url = None
        for part in link_header.split(","):
            part = part.strip()
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
                # Strip base URL to get just the path+query
                next_url = next_url.replace("https://wmcarey.instructure.com/api/v1", "")
                break
        path = next_url
    return results


def is_microsoft_tool(tool):
    searchable = " ".join([
        tool.get("name", ""),
        tool.get("description", ""),
        tool.get("domain", ""),
        tool.get("url", ""),
        tool.get("consumer_key", ""),
    ]).lower()
    return any(kw in searchable for kw in MS_KEYWORDS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-file", help="Path to a file containing your Canvas token")
    args = parser.parse_args()

    token = get_token(args.token_file)

    print(f"Checking course {COURSE_ID} for Microsoft Teams / Education LTI tools...\n")

    # Course-level external tools
    tools = get_all_pages(f"/courses/{COURSE_ID}/external_tools", token)

    print(f"Found {len(tools)} external tool(s) on this course.\n")

    ms_tools = [t for t in tools if is_microsoft_tool(t)]
    other_tools = [t for t in tools if not is_microsoft_tool(t)]

    if ms_tools:
        print("MICROSOFT / TEAMS / EDUCATION TOOLS FOUND:")
        print("=" * 55)
        for t in ms_tools:
            print(f"  Name        : {t.get('name')}")
            print(f"  ID          : {t.get('id')}")
            print(f"  Domain      : {t.get('domain', 'n/a')}")
            print(f"  URL         : {t.get('url', 'n/a')}")
            print(f"  Description : {t.get('description', 'n/a')}")
            print(f"  Workflow    : {t.get('workflow_state', 'n/a')}")
            print()
    else:
        print("No Microsoft / Teams / Education LTI tool found on this course.")
        print()

    if other_tools:
        print("Other tools installed on this course:")
        print("-" * 40)
        for t in other_tools:
            print(f"  [{t.get('id')}] {t.get('name')}  ({t.get('domain', t.get('url', 'n/a'))})")

    # Also check account-level tools (inherited by the course)
    print("\nChecking account-level tools (these apply to all courses)...")
    # Get the course to find its account
    course_data, _ = api_get(f"/courses/{COURSE_ID}", token)
    account_id = course_data.get("account_id")
    if account_id:
        acct_tools = get_all_pages(f"/accounts/{account_id}/external_tools", token)
        ms_acct = [t for t in acct_tools if is_microsoft_tool(t)]
        print(f"  Account {account_id}: {len(acct_tools)} total tool(s), "
              f"{len(ms_acct)} Microsoft-related.\n")
        if ms_acct:
            print("  MICROSOFT TOOLS AT ACCOUNT LEVEL:")
            for t in ms_acct:
                print(f"    [{t.get('id')}] {t.get('name')}  state={t.get('workflow_state')}")
        else:
            print("  No Microsoft tools found at the account level.")
    else:
        print("  Could not determine account ID.")


if __name__ == "__main__":
    main()
