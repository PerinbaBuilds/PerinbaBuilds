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


GITHUB_MARK = (
    "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 "
    "0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 "
    "1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 "
    "0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 "
    "1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 "
    "3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 "
    "8.013 0 0016 8c0-4.42-3.58-8-8-8z"
)


def rest(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Authorization": "bearer " + TOKEN,
            "User-Agent": "badge-generator",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def _text_w(s):
    return int(round(len(s) * 6.5))


def make_followers_badge(count):
    """Render a flat-square 'Followers' badge SVG (no shields.io dependency)."""
    label, value = "Followers", str(count)
    label_bg, value_bg = "#181717", "#181717"
    logo, h = 14, 20
    label_w = 5 + logo + 4 + _text_w(label) + 8
    value_w = 8 + _text_w(value) + 8
    total = label_w + value_w
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{h}" '
        f'role="img" aria-label="Followers: {value}">\n'
        f'<rect width="{label_w}" height="{h}" fill="{label_bg}"/>\n'
        f'<rect x="{label_w}" width="{value_w}" height="{h}" fill="{value_bg}"/>\n'
        f'<g transform="translate(5,3)"><path transform="scale(0.875)" fill="#ffffff" d="{GITHUB_MARK}"/></g>\n'
        f'<g fill="#ffffff" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" '
        f'font-size="11">\n'
        f'<text x="{5 + logo + 4}" y="14">{label}</text>\n'
        f'<text x="{label_w + 8}" y="14">{value}</text>\n'
        f'</g>\n</svg>\n'
    )
    with open("assets/followers.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Generated assets/followers.svg — {count} followers")


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

    followers = rest("/users/" + LOGIN)["followers"]
    make_followers_badge(followers)


if __name__ == "__main__":
    main()
