#!/usr/bin/env python3
"""
Generate a GitHub streak stats SVG using the authenticated GITHUB_TOKEN.
This avoids the rate-limiting issues of shared third-party streak services.
"""
import os
import json
import sys
import urllib.request
from datetime import date, timedelta

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
USERNAME = "Aniket886"

QUERY = """
query($username: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $username) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""


def gql(variables):
    payload = json.dumps({"query": QUERY, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    if "errors" in result:
        raise RuntimeError(result["errors"])
    cal = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = {}
    for week in cal["weeks"]:
        for day in week["contributionDays"]:
            days[date.fromisoformat(day["date"])] = day["contributionCount"]
    return days, cal["totalContributions"]


def fetch_all_days():
    today = date.today()
    all_days = {}
    total_this_year = 0
    for yr in [today.year - 1, today.year]:
        from_dt = f"{yr}-01-01T00:00:00Z"
        to_dt = f"{yr}-12-31T23:59:59Z"
        try:
            days, total = gql({"username": USERNAME, "from": from_dt, "to": to_dt})
            all_days.update(days)
            if yr == today.year:
                total_this_year = total
        except Exception as exc:
            print(f"Warning: could not fetch {yr}: {exc}", file=sys.stderr)
    return all_days, total_this_year


def calc_current_streak(days, today):
    check = today
    # if today has no commit yet, allow starting from yesterday
    if days.get(check, 0) == 0:
        check = today - timedelta(days=1)
    streak = 0
    streak_start = check
    while days.get(check, 0) > 0:
        streak += 1
        streak_start = check
        check -= timedelta(days=1)
    streak_end = today if days.get(today, 0) > 0 else today - timedelta(days=1)
    return streak, streak_start, streak_end


def calc_longest_streak(days, today):
    if not days:
        return 0, None, None
    sorted_dates = sorted(d for d in days.keys() if d <= today)
    longest = current = 0
    longest_start = longest_end = current_start = None
    for d in sorted_dates:
        if days[d] > 0:
            if current == 0:
                current_start = d
            current += 1
            if current > longest:
                longest = current
                longest_start = current_start
                longest_end = d
        else:
            current = 0
            current_start = None
    return longest, longest_start, longest_end


def fmt_date(d):
    if d is None:
        return "N/A"
    return d.strftime("%b %-d, %Y") if sys.platform != "win32" else d.strftime("%b %#d, %Y")


def fmt_range(start, end):
    """Short date range: 'Apr 3 - Apr 28, 2026' when same year."""
    if start is None or end is None:
        return "-"
    if sys.platform != "win32":
        s = start.strftime("%b %-d") if start.year == end.year else start.strftime("%b %-d, %Y")
        e = end.strftime("%b %-d, %Y")
    else:
        s = start.strftime("%b %#d") if start.year == end.year else start.strftime("%b %#d, %Y")
        e = end.strftime("%b %#d, %Y")
    return f"{s} - {e}"


def generate_svg(total, cur_streak, cur_start, cur_end, lng_streak, lng_start, lng_end):
    bg      = "#151515"
    border  = "#555555"
    ring    = "#FF9500"
    fire    = "#FF9500"
    num_col = "#FFFFFF"
    lbl_col = "#FFFFFF"
    dt_col  = "#A8A8A8"
    divider = "#8A8A8A"

    today = date.today()
    if sys.platform != "win32":
        total_range = f"Jan 1, {today.year} - {today.strftime('%b %-d, %Y')}"
    else:
        total_range = f"Jan 1, {today.year} - {today.strftime('%b %#d, %Y')}"

    cur_range = fmt_range(cur_start, cur_end) if cur_streak > 0 else "No active streak"
    lng_range = fmt_range(lng_start, lng_end) if lng_streak > 0 else "-"

    # Flame shape sits into the ring, matching the reference badge style.
    flame_outer = "M0-22C8-14 10-7 5 0C10-2 13-8 9-16C20-6 16 9 4 12C-8 15-15 5-10-6C-8-12-4-17 0-22Z"
    flame_cutout = "M1-9C5-4 5 2 1 5C-4 1-4-5 1-9Z"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  style="isolation:isolate" viewBox="0 0 495 195" width="495px" height="195px">
  <rect x="0.5" y="0.5" width="494" height="194" fill="{bg}" stroke="{border}" rx="3.5"/>

  <!-- Section dividers -->
  <line x1="165" y1="27" x2="165" y2="170" stroke="{divider}" stroke-width="1.5"/>
  <line x1="330" y1="27" x2="330" y2="170" stroke="{divider}" stroke-width="1.5"/>

  <!-- LEFT: Total Contributions -->
  <g transform="translate(82.5,80)">
    <text y="0" text-anchor="middle" fill="{num_col}"
      font-family="Segoe UI,Ubuntu,sans-serif" font-size="29" font-weight="700">{total}</text>
    <text y="36" text-anchor="middle" fill="{lbl_col}"
      font-family="Segoe UI,Ubuntu,sans-serif" font-size="14">Total Contributions</text>
    <text y="67" text-anchor="middle" fill="{dt_col}"
      font-family="Segoe UI,Ubuntu,sans-serif" font-size="12">{total_range}</text>
  </g>

  <!-- CENTER: Current Streak -->
  <g transform="translate(247.5,75)">
    <g transform="translate(0,-39) scale(0.78)">
      <path fill="{fire}" d="{flame_outer}"/>
      <path fill="{bg}" d="{flame_cutout}"/>
    </g>
    <circle cx="0" cy="0" r="37" fill="none" stroke="{ring}" stroke-width="5"/>
    <text y="10" text-anchor="middle" fill="{num_col}"
      font-family="Segoe UI,Ubuntu,sans-serif" font-size="28" font-weight="700">{cur_streak}</text>
    <text y="62" text-anchor="middle" fill="{fire}"
      font-family="Segoe UI,Ubuntu,sans-serif" font-size="14" font-weight="600">Current Streak</text>
    <text y="88" text-anchor="middle" fill="{dt_col}"
      font-family="Segoe UI,Ubuntu,sans-serif" font-size="12">{cur_range}</text>
  </g>

  <!-- RIGHT: Longest Streak -->
  <g transform="translate(412.5,80)">
    <text y="0" text-anchor="middle" fill="{num_col}"
      font-family="Segoe UI,Ubuntu,sans-serif" font-size="29" font-weight="700">{lng_streak}</text>
    <text y="36" text-anchor="middle" fill="{lbl_col}"
      font-family="Segoe UI,Ubuntu,sans-serif" font-size="14">Longest Streak</text>
    <text y="67" text-anchor="middle" fill="{dt_col}"
      font-family="Segoe UI,Ubuntu,sans-serif" font-size="12">{lng_range}</text>
  </g>
</svg>"""


def main():
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    print("Fetching contribution data...", file=sys.stderr)
    days, total = fetch_all_days()
    today = date.today()

    cur_streak, cur_start, cur_end = calc_current_streak(days, today)
    lng_streak, lng_start, lng_end = calc_longest_streak(days, today)

    print(f"Total: {total}, Current: {cur_streak}, Longest: {lng_streak}", file=sys.stderr)

    svg = generate_svg(total, cur_streak, cur_start, cur_end, lng_streak, lng_start, lng_end)

    out_path = os.path.join(os.path.dirname(__file__), "../../assets/github-streak.svg")
    with open(os.path.normpath(out_path), "w", encoding="utf-8") as f:
        f.write(svg)
    print("Wrote assets/github-streak.svg", file=sys.stderr)


if __name__ == "__main__":
    main()
