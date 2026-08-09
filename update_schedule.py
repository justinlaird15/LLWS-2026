import json
import re
import time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent

BASE = json.loads(
    (ROOT / "base_schedule.json").read_text(encoding="utf-8")
)


URLS = {
    "Great Lakes":
        "https://www.littleleague.org/world-series/2026/llbws/tournaments/great-lakes-region/",

    "Metro":
        "https://www.littleleague.org/world-series/2026/llbws/tournaments/metro-region/",

    "Mid-Atlantic":
        "https://www.littleleague.org/world-series/2026/llbws/tournaments/mid-atlantic-region/",

    "Midwest":
        "https://www.littleleague.org/world-series/2026/llbws/tournaments/midwest-region/",

    "Mountain":
        "https://www.littleleague.org/world-series/2026/llbws/tournaments/mountain-region/",

    "New England":
        "https://www.littleleague.org/world-series/2026/llbws/tournaments/new-england-region/",

    "Northwest":
        "https://www.littleleague.org/world-series/2026/llbws/tournaments/northwest-region/",

    "Southeast":
        "https://www.littleleague.org/world-series/2026/llbws/tournaments/southeast-region/",

    "Southwest":
        "https://www.littleleague.org/world-series/2026/llbws/tournaments/southwest-region/",

    "West":
        "https://www.littleleague.org/world-series/2026/llbws/tournaments/west-region/",
}


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# State/region names that can appear as teams.
TEAM_NAMES = [
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New York",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Southern California",
    "Northern California",
    "Tennessee",
    "Texas East",
    "Texas West",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "Washington, DC",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
]


def clean(value):
    return re.sub(
        r"\s+",
        " ",
        value or ""
    ).strip()


def get_region_tokens(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    return [
        clean(x)
        for x in soup.stripped_strings
        if clean(x)
    ]


def split_into_game_blocks(tokens):

    blocks = []

    current = None

    for token in tokens:

        game_match = re.match(
            r"^Game\s+(\d+)",
            token,
            re.I
        )

        if game_match:

            if current:
                blocks.append(current)

            current = {
                "game_number":
                    int(game_match.group(1)),

                "tokens": [
                    token
                ]
            }

            continue

        if current:

            current["tokens"].append(
                token
            )

    if current:
        blocks.append(current)

    return blocks


def find_game_date(block_text):

    match = re.search(
        r"August\s+(\d{1,2})",
        block_text,
        re.I
    )

    if not match:
        return None

    day = int(
        match.group(1)
    )

    return f"2026-08-{day:02d}"


def find_game_time(block_text):

    match = re.search(
        r"(\d{1,2}:\d{2})\s*"
        r"([ap])\.?m\.?",
        block_text,
        re.I
    )

    if not match:
        return None

    hour_minute = (
        match.group(1)
    )

    am_pm = (
        match.group(2).upper()
        + "M"
    )

    dt = datetime.strptime(
        hour_minute + " " + am_pm,
        "%I:%M %p"
    )

    return dt.strftime(
        "%-I:%M %p"
    )


def extract_teams(tokens):

    found = []

    for token in tokens:

        for team in TEAM_NAMES:

            if token == team:

                if team not in found:

                    found.append(team)

    return found[:2]


def extract_scores(tokens, team1, team2):

    try:
        index1 = tokens.index(team1)
        index2 = tokens.index(team2)

    except ValueError:
        return None

    score1 = None
    score2 = None

    # Look immediately after Team 1
    # until reaching Team 2.
    for token in tokens[
        index1 + 1:index2
    ]:

        if re.fullmatch(
            r"\d{1,2}",
            token
        ):

            score1 = token
            break

    # Look immediately after Team 2.
    for token in tokens[
        index2 + 1:index2 + 8
    ]:

        if re.fullmatch(
            r"\d{1,2}",
            token
        ):

            score2 = token
            break

    if (
        score1 is not None
        and score2 is not None
    ):

        return (
            score1,
            score2
        )

    return None


def parse_region(region, url):

    tokens = get_region_tokens(
        url
    )

    blocks = split_into_game_blocks(
        tokens
    )

    games = []

    for block in blocks:

        block_tokens = (
            block["tokens"]
        )

        block_text = " ".join(
            block_tokens
        )

        date = find_game_date(
            block_text
        )

        time_text = find_game_time(
            block_text
        )

        teams = extract_teams(
            block_tokens
        )

        if (
            not date
            or not time_text
            or len(teams) < 2
        ):
            continue

        team1 = teams[0]
        team2 = teams[1]

        scores = extract_scores(
            block_tokens,
            team1,
            team2
        )

        if scores:

            matchup = (
                f"{team1} {scores[0]}"
                f" — "
                f"{team2} {scores[1]}"
            )

            status = "FINAL"

        else:

            matchup = (
                f"{team1}"
                f" vs "
                f"{team2}"
            )

            status = ""

        games.append({
            "date":
                date,

            "time":
                time_text,

            "region":
                region,

            "matchup":
                matchup,

            "status":
                status,

            "game_number":
                block["game_number"]
        })

    return games


scraped = []

errors = []


for region, url in URLS.items():

    try:

        region_games = (
            parse_region(
                region,
                url
            )
        )

        scraped.extend(
            region_games
        )

        if not region_games:

            errors.append(
                f"{region}: no games parsed"
            )

    except Exception as exc:

        errors.append(
            f"{region}: "
            f"{type(exc).__name__}: "
            f"{exc}"
        )

    time.sleep(0.15)


# Match the official game to the
# schedule already used by the app.
lookup = {}

for game in scraped:

    key = (
        game["date"],
        game["time"],
        game["region"]
    )

    lookup[key] = game


output = []

matched = 0


for base_game in BASE:

    row = dict(
        base_game
    )

    key = (
        row["date"],
        row["time"],
        row["region"]
    )

    official = lookup.get(
        key
    )

    if official:

        row["matchup"] = (
            official["matchup"]
        )

        row["status"] = (
            official["status"]
        )

        matched += 1

    output.append(
        row
    )


payload = {

    "updated":
        datetime.now(
            ZoneInfo("UTC")
        ).strftime(
            "%Y-%m-%d %H:%M UTC"
        ),

    "source":
        "Official LittleLeague.org "
        "tournament schedules",

    "scraped_games":
        len(scraped),

    "matched_games":
        matched,

    "errors":
        errors,

    "games":
        output
}


(
    ROOT / "latest.json"
).write_text(

    json.dumps(
        payload,
        indent=2,
        ensure_ascii=False
    ),

    encoding="utf-8"
)


print(
    "Scraped games:",
    len(scraped)
)

print(
    "Matched games:",
    matched
)

print(
    "\n--- MID-ATLANTIC RESULTS ---"
)

for game in scraped:

    if (
        game["region"]
        == "Mid-Atlantic"
    ):

        print(
            game["date"],
            game["time"],
            game["matchup"],
            game["status"]
        )


if errors:

    print(
        "\nWarnings:"
    )

    for error in errors:

        print(
            " -",
            error
        )
