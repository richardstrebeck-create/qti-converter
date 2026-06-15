#!/usr/bin/env python3
"""Upload the PSY 3510 Midterm Quiz to Canvas via the Classic Quizzes API.

Creates a quiz in course 78684 at wmcarey.instructure.com and posts eight
multiple-choice questions, marking the correct answer on each via answer weights
(100 for correct, 0 for incorrect).

Usage:
    python upload_psy3510_quiz.py

The Canvas API token is read from the file referenced by TOKEN_PATH below
(override with the CANVAS_TOKEN_FILE environment variable, or set the token
directly with the CANVAS_TOKEN environment variable).
"""

import os
import sys
import json
import urllib.request
import urllib.error

# --- Configuration -----------------------------------------------------------

CANVAS_BASE_URL = "https://wmcarey.instructure.com"
COURSE_ID = 78684
QUIZ_TITLE = "PSY 3510 Midterm Quiz"

# Default location of the API token (one token string in a plain text file).
TOKEN_PATH = r"C:\Users\rstrebeck\OneDrive - WCU\Claude\Canvas_token.txt"

# --- Quiz content ------------------------------------------------------------
# Each question lists its answers as (text, is_correct) tuples.

QUESTIONS = [
    {
        "name": "Q1 - Mean from frequency table",
        "points": 3,
        "text": (
            "Use the frequency table below to calculate the mean "
            "(round to 2 decimal places).<br>"
            "X (frequency): 14 = 21, 13 = 20, 12 = 13, 11 = 8, 10 = 3, 122 = 3."
        ),
        "answers": [
            ("17.56", True),
            ("13.00", False),
            ("12.53", False),
            ("19.74", False),
        ],
    },
    {
        "name": "Q2 - Median from frequency table",
        "points": 3,
        "text": "Use the frequency table above to calculate the median.",
        "answers": [
            ("14", False),
            ("12", False),
            ("13", True),
            ("122", False),
        ],
    },
    {
        "name": "Q3 - Mode from frequency table",
        "points": 3,
        "text": "Use the frequency table above to identify the mode.",
        "answers": [
            ("21", False),
            ("13", False),
            ("122", False),
            ("14", True),
        ],
    },
    {
        "name": "Q4 - Mean for PHU",
        "points": 3,
        "text": (
            "Calculate the mean for PoDunk Holler University (PHU): "
            "scores are 85, 73, 70, 80."
        ),
        "answers": [
            ("77.00", True),
            ("79.33", False),
            ("308.00", False),
            ("75.50", False),
        ],
    },
    {
        "name": "Q5 - Mean for SSS",
        "points": 3,
        "text": (
            "Calculate the mean for Strebeck's Satanic Stats (SSS): "
            "scores are 95, 81, 82, 91, 70, 85."
        ),
        "answers": [
            ("100.80", False),
            ("82.50", False),
            ("84.00", True),
            ("504.00", False),
        ],
    },
    {
        "name": "Q6 - Standard deviation for PHU",
        "points": 4,
        "text": (
            "Using the sample formula (n-1), calculate the standard deviation "
            "for PHU (scores: 85, 73, 70, 80)."
        ),
        "answers": [
            ("11.40", False),
            ("6.78", True),
            ("46.00", False),
            ("34.50", False),
        ],
    },
    {
        "name": "Q7 - Standard deviation for SSS",
        "points": 4,
        "text": (
            "Using the sample formula (n-1), calculate the standard deviation "
            "for SSS (scores: 95, 81, 82, 91, 70, 85)."
        ),
        "answers": [
            ("8.72", True),
            ("7.94", False),
            ("76.00", False),
            ("63.33", False),
        ],
    },
    {
        "name": "Q8 - Which class performed better",
        "points": 6,
        "text": (
            "Based on mean and standard deviation for both classes, which "
            "statement best describes which class performed better?"
        ),
        "answers": [
            (
                "PHU performed better; mean=77.00, SD=6.78 indicating stronger "
                "consistency outweighs SSS mean=84.00, SD=8.72",
                False,
            ),
            (
                "SSS performed better; mean=84.00, SD=6.78 indicating higher "
                "performance and consistency over PHU mean=77.00, SD=8.72",
                False,
            ),
            (
                "SSS performed better; mean=84.00, SD=8.72 indicating higher "
                "performance despite less consistency than PHU mean=77.00, "
                "SD=6.78",
                True,
            ),
            (
                "Both classes performed equally; PHU mean=77.00, SD=6.78 and "
                "SSS mean=84.00, SD=8.72 show no meaningful difference",
                False,
            ),
        ],
    },
]


# --- Helpers -----------------------------------------------------------------

def read_token():
    """Return the Canvas API token from env vars or the token file."""
    token = os.environ.get("CANVAS_TOKEN")
    if token:
        return token.strip()

    token_path = os.environ.get("CANVAS_TOKEN_FILE", TOKEN_PATH)
    try:
        with open(token_path, "r", encoding="utf-8-sig") as handle:
            token = handle.read().strip()
    except OSError as exc:
        sys.exit(
            f"ERROR: could not read token from {token_path!r}: {exc}\n"
            "Set CANVAS_TOKEN_FILE or CANVAS_TOKEN to override."
        )

    if not token:
        sys.exit(f"ERROR: token file {token_path!r} is empty.")
    return token


def api_request(method, path, token, payload=None):
    """Make a JSON Canvas API request and return the parsed response."""
    url = f"{CANVAS_BASE_URL}{path}"
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        sys.exit(f"ERROR: {method} {path} failed ({exc.code}): {detail}")
    except urllib.error.URLError as exc:
        sys.exit(f"ERROR: {method} {path} failed: {exc.reason}")


def create_quiz(token):
    """Create the classic quiz and return its JSON representation."""
    payload = {
        "quiz": {
            "title": QUIZ_TITLE,
            "quiz_type": "assignment",
            "show_correct_answers": True,
            "description": "Midterm quiz covering measures of central tendency "
            "and variability for PSY 3510.",
            "published": False,
        }
    }
    return api_request("POST", f"/api/v1/courses/{COURSE_ID}/quizzes", token, payload)


def add_question(token, quiz_id, question):
    """Post a single multiple-choice question to the quiz."""
    answers = [
        {
            "answer_text": text,
            "answer_weight": 100 if is_correct else 0,
        }
        for text, is_correct in question["answers"]
    ]
    payload = {
        "question": {
            "question_name": question["name"],
            "question_text": question["text"],
            "question_type": "multiple_choice_question",
            "points_possible": question["points"],
            "answers": answers,
        }
    }
    return api_request(
        "POST",
        f"/api/v1/courses/{COURSE_ID}/quizzes/{quiz_id}/questions",
        token,
        payload,
    )


# --- Main --------------------------------------------------------------------

def main():
    token = read_token()

    print(f"Creating quiz '{QUIZ_TITLE}' in course {COURSE_ID}...")
    quiz = create_quiz(token)
    quiz_id = quiz["id"]
    print(f"  Created quiz id {quiz_id}")

    for index, question in enumerate(QUESTIONS, start=1):
        result = add_question(token, quiz_id, question)
        print(f"  Added question {index}/{len(QUESTIONS)}: "
              f"{question['name']} (id {result.get('id', '?')})")

    quiz_url = f"{CANVAS_BASE_URL}/courses/{COURSE_ID}/quizzes/{quiz_id}"
    total_points = sum(q["points"] for q in QUESTIONS)
    print()
    print("Done! Quiz created successfully.")
    print(f"  Questions: {len(QUESTIONS)}  |  Total points: {total_points}")
    print(f"  Quiz URL: {quiz_url}")
    print("  (The quiz is unpublished; review it in Canvas and publish when ready.)")


if __name__ == "__main__":
    main()
