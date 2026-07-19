#!/usr/bin/env python3
"""Generate a dark-themed GitHub contribution squares graph as an SVG.

Fetches the real contribution calendar via the GitHub GraphQL API and renders
it with GitHub's dark-mode palette so it matches the native profile graph.
Runs inside GitHub Actions (where the token can read the calendar).
"""
import datetime
import json
import os
import sys
import urllib.request

TOKEN = os.environ["GH_TOKEN"]
LOGIN = os.environ.get("GH_LOGIN", "PerinbaBuilds")

QUERY = """
query($login:String!){
  user(login:$login){
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{
          contributionDays{
            date
            weekday
            contributionLevel
          }
        }
      }
    }
  }
}
"""

# GitHub dark-mode contribution palette
COLORS = {
    "NONE": "#161b22",
    "FIRST_QUARTILE": "#0e4429",
    "SECOND_QUARTILE": "#006d32",
    "THIRD_QUARTILE": "#26a641",
    "FOURTH_QUARTILE": "#39d353",
}

CELL = 11          # square size
GAP = 3            # gap between squares
STEP = CELL + GAP  # 14
LEFT = 30          # room for weekday labels
TOP = 20           # room for month labels
PAD = 8
BG = "#0d1117"
TEXT = "#8b949e"
FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"


def graphql(query, variables):
    payload = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": "bearer " + TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "contribution-graph-generator",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main():
    res = graphql(QUERY, {"login": LOGIN})
    if res.get("errors"):
        print("GraphQL errors:", res["errors"], file=sys.stderr)
        sys.exit(1)
    cal = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    total = cal["totalContributions"]

    n_weeks = len(weeks)
    width = LEFT + n_weeks * STEP + PAD
    height = TOP + 7 * STEP + PAD

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}">',
        f'<rect width="{width}" height="{height}" rx="6" fill="{BG}"/>',
    ]

    # month labels (drawn at the first week a new month appears, with min spacing)
    seen = set()
    last_x = -999
    for wi, wk in enumerate(weeks):
        d = datetime.date.fromisoformat(wk["contributionDays"][0]["date"])
        key = (d.year, d.month)
        if key in seen:
            continue
        seen.add(key)
        x = LEFT + wi * STEP
        if x - last_x >= 2 * STEP:  # avoid crowding
            out.append(
                f'<text x="{x}" y="{TOP - 6}" fill="{TEXT}" font-size="10">'
                f'{d.strftime("%b")}</text>'
            )
            last_x = x

    # weekday labels: Mon / Wed / Fri
    for wd, lbl in {1: "Mon", 3: "Wed", 5: "Fri"}.items():
        y = TOP + wd * STEP + CELL - 1
        out.append(f'<text x="0" y="{y}" fill="{TEXT}" font-size="9">{lbl}</text>')

    # squares
    for wi, wk in enumerate(weeks):
        for day in wk["contributionDays"]:
            wd = day["weekday"]
            color = COLORS.get(day["contributionLevel"], COLORS["NONE"])
            x = LEFT + wi * STEP
            y = TOP + wd * STEP
            out.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2" ry="2" fill="{color}"/>'
            )

    out.append("</svg>")
    svg = "\n".join(out)

    os.makedirs("assets", exist_ok=True)
    with open("assets/contribution-graph.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Generated assets/contribution-graph.svg — {total} contributions across {n_weeks} weeks")


if __name__ == "__main__":
    main()
