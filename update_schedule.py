import json
import re
import time
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent

EASTERN = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

# A scored game stays LIVE for this long after scheduled start.
# Little League games are normally completed well inside this window.
LIVE_WINDOW_HOURS = 3


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


WORLD_SERIES_URL = (
    "https://www.littleleague.org/world-series/2026/llbws/tournaments/world-series/"
)


HEADERS = {
    "User-Agent":
        "Mozilla/5.0 "
        "(compatible; personal LLWS schedule dashboard/6.0)"
}


TZ_MAP = {
    "Eastern": "America/New_York",
    "Central": "America/Chicago",
    "Mountain": "America/Denver",
    "Pacific": "America/Los_Angeles",

    "ET": "America/New_York",
    "CT": "America/Chicago",
    "MT": "America/Denver",
    "PT": "America/Los_Angeles",
}


TEAM_ALIASES = {
    "Alabama": "Alabama",
    "Alaska": "Alaska",
    "Arizona": "Arizona",
    "Arkansas": "Arkansas",
    "Colorado": "Colorado",
    "Connecticut": "Connecticut",
    "Delaware": "Delaware",
    "Florida": "Florida",
    "Georgia": "Georgia",
    "Hawaii": "Hawaii",
    "Idaho": "Idaho",
    "Illinois": "Illinois",
    "Indiana": "Indiana",
    "Iowa": "Iowa",
    "Kansas": "Kansas",
    "Kentucky": "Kentucky",
    "Louisiana": "Louisiana",
    "Maine": "Maine",
    "Maryland": "Maryland",
    "Massachusetts": "Massachusetts",
    "Michigan": "Michigan",
    "Minnesota": "Minnesota",
    "Mississippi": "Mississippi",
    "Missouri": "Missouri",
    "Montana": "Montana",
    "Nebraska": "Nebraska",
    "Nevada": "Nevada",
    "New Hampshire": "New Hampshire",
    "New Jersey": "New Jersey",
    "New York": "New York",
    "North Dakota": "North Dakota",
    "Ohio": "Ohio",
    "Oklahoma": "Oklahoma",
    "Oregon": "Oregon",
    "Pennsylvania": "Pennsylvania",
    "Rhode Island": "Rhode Island",
    "South Carolina": "South Carolina",
    "South Dakota": "South Dakota",

    "Southern California": "Southern California",
    "Southern Calif.": "Southern California",

    "Northern California": "Northern California",
    "Northern Calif.": "Northern California",

    "Tennessee": "Tennessee",
    "Texas East": "Texas East",
    "Texas West": "Texas West",
    "Utah": "Utah",
    "Vermont": "Vermont",
    "Virginia": "Virginia",
    "Washington": "Washington",
    "Washington, DC": "Washington, DC",
    "Washington, D.C.": "Washington, DC",
    "West Virginia": "West Virginia",
    "Wisconsin": "Wisconsin",
    "Wyoming": "Wyoming",
}


WORLD_REGION_LABELS = [
    "Asia-Pacific Region",
    "Australia Region",
    "Canada Region",
    "Caribbean Region",
    "Curaçao Region",
    "Europe-Africa Region",
    "Europe & Africa Region",
    "Japan Region",
    "Latin America Region",
    "Mexico Region",
    "Panama Region",
    "Great Lakes Region",
    "Metro Region",
    "Mid-Atlantic Region",
    "Midwest Region",
    "Mountain Region",
    "New England Region",
    "Northwest Region",
    "Southeast Region",
    "Southwest Region",
    "West Region",
]


PARTICIPANT_REGIONS = [
    "Great Lakes",
    "Metro",
    "Mid-Atlantic",
    "Midwest",
    "Mountain",
    "New England",
    "Northwest",
    "Southeast",
    "Southwest",
    "West",
    "Asia-Pacific",
    "Australia",
    "Canada",
    "Caribbean",
    "Curaçao",
    "Europe & Africa",
    "Japan",
    "Latin America",
    "Mexico",
    "Panama",
]


WORLD_SERIES_GAMES = [
    ("2026-08-19", "1:00 PM", "Latin America Region vs Caribbean Region", "ESPN"),
    ("2026-08-19", "3:00 PM", "Southeast Region vs Northwest Region", "ESPN"),
    ("2026-08-19", "5:00 PM", "Canada Region vs Asia-Pacific Region", "ESPN"),
    ("2026-08-19", "7:00 PM", "Metro Region vs New England Region", "ESPN"),

    ("2026-08-20", "12:00 PM", "Australia Region vs Mexico Region", "ESPN"),
    ("2026-08-20", "2:00 PM", "Great Lakes Region vs Mountain Region", "ESPN"),
    ("2026-08-20", "4:00 PM", "Curaçao Region vs Japan Region", "ESPN"),
    ("2026-08-20", "6:00 PM", "West Region vs Midwest Region", "ESPN2"),

    ("2026-08-21", "1:00 PM", "Panama Region vs W1", "ESPN"),
    ("2026-08-21", "3:00 PM", "Southwest Region vs W2", "ESPN"),
    ("2026-08-21", "5:00 PM", "Europe-Africa Region vs W3", "ESPN"),
    ("2026-08-21", "7:00 PM", "Mid-Atlantic Region vs W4", "ESPN"),

    ("2026-08-22", "1:00 PM", "L3 vs L5", "ESPN"),
    ("2026-08-22", "3:00 PM", "L4 vs L6", "ESPN"),
    ("2026-08-22", "5:00 PM", "L1 vs L7", "ESPN"),
    ("2026-08-22", "7:00 PM", "L2 vs L8", "ESPN"),

    ("2026-08-23", "9:00 AM", "W6 vs W10", "ESPN"),
    ("2026-08-23", "11:00 AM", "W5 vs W9", "ESPN"),
    ("2026-08-23", "1:00 PM", "W8 vs W12", "ABC"),
    ("2026-08-23", "2:00 PM", "W7 vs W11", "ESPN"),

    ("2026-08-24", "1:00 PM", "L9 vs W13", "ESPN"),
    ("2026-08-24", "3:00 PM", "L10 vs W14", "ESPN"),
    ("2026-08-24", "5:00 PM", "L11 vs W15", "ESPN"),
    ("2026-08-24", "7:00 PM", "L12 vs W16", "ESPN"),

    ("2026-08-25", "1:00 PM", "L18 vs W23", "ESPN"),
    ("2026-08-25", "3:00 PM", "L17 vs W24", "ESPN"),
    ("2026-08-25", "5:00 PM", "L20 vs W21", "ESPN"),
    ("2026-08-25", "7:00 PM", "L19 vs W22", "ESPN"),

    ("2026-08-26", "1:00 PM", "W18 vs W20", "ESPN"),
    ("2026-08-26", "3:00 PM", "W17 vs W19", "ESPN"),
    ("2026-08-26", "5:00 PM", "W25 vs W27", "ESPN"),
    ("2026-08-26", "7:00 PM", "W26 vs W28", "ESPN"),

    ("2026-08-27", "3:00 PM", "L29 vs W31", "ESPN"),
    ("2026-08-27", "7:00 PM", "L30 vs W32", "ESPN"),

    ("2026-08-29", "12:30 PM", "W29 vs W33 — International Championship", "ABC"),
    ("2026-08-29", "3:30 PM", "W30 vs W34 — United States Championship", "ABC"),

    ("2026-08-30", "10:00 AM", "L35 vs L36 — Third-Place Game", "ESPN"),
    ("2026-08-30", "3:00 PM", "W35 vs W36 — LLWS World Championship", "ABC"),
]


def clean(value):
    return re.sub(
        r"\s+",
        " ",
        value or ""
    ).strip()


def fetch_tokens(url):

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

        match = re.match(
            r"^Game\s+(\d+)\b",
            token,
            re.I
        )

        if match:

            if current:
                blocks.append(current)

            current = {
                "game_number": int(match.group(1)),
                "tokens": [token]
            }

            continue

        if current:
            current["tokens"].append(token)

    if current:
        blocks.append(current)

    return blocks


def page_timezone(tokens):

    text = " ".join(tokens)

    match = re.search(
        r"All game times are "
        r"(Eastern|Central|Mountain|Pacific) time",
        text,
        re.I
    )

    if match:
        return TZ_MAP[
            match.group(1).title()
        ]

    return "America/New_York"


def find_date_and_time(
    block_tokens,
    source_timezone
):

    text = " ".join(
        block_tokens
    )

    match = re.search(
        r"(\d{1,2}:\d{2})\s*"
        r"([ap])\.?m\.?"
        r"(?:\s*\(?\s*(ET|CT|MT|PT)\s*\)?)?"
        r"\s*-\s*August\s+"
        r"(\d{1,2})",
        text,
        re.I
    )

    if not match:
        return None, None, None

    time_text = (
        match.group(1)
        + " "
        + match.group(2).upper()
        + "M"
    )

    explicit_tz = match.group(3)

    day = int(
        match.group(4)
    )

    source_date = (
        f"2026-08-{day:02d}"
    )

    if explicit_tz:

        tz_name = TZ_MAP.get(
            explicit_tz.upper(),
            source_timezone
        )

    else:

        tz_name = source_timezone

    dt = datetime.strptime(
        f"{source_date} {time_text}",
        "%Y-%m-%d %I:%M %p"
    )

    dt = dt.replace(
        tzinfo=ZoneInfo(tz_name)
    )

    eastern = dt.astimezone(
        EASTERN
    )

    date_iso = eastern.strftime(
        "%Y-%m-%d"
    )

    display_time = eastern.strftime(
        "%-I:%M %p"
    )

    return (
        date_iso,
        display_time,
        eastern
    )


def extract_region_teams(
    block_tokens
):

    teams = []
    raw_teams = []

    for token in block_tokens:

        if token in TEAM_ALIASES:

            normalized = (
                TEAM_ALIASES[token]
            )

            if normalized not in teams:

                teams.append(
                    normalized
                )

                raw_teams.append(
                    token
                )

    return (
        teams[:2],
        raw_teams[:2]
    )


def score_for_team(
    block_tokens,
    raw_team,
    other_raw_team
):

    try:

        start = block_tokens.index(
            raw_team
        )

    except ValueError:

        return None


    try:

        end = block_tokens.index(
            other_raw_team,
            start + 1
        )

    except ValueError:

        end = min(
            len(block_tokens),
            start + 12
        )


    segment = block_tokens[
        start + 1:
        end
    ]


    for token in segment:

        # Ignore bracket advancement labels such as W1 or L4.
        if re.fullmatch(
            r"[WL]\d+",
            token,
            re.I
        ):
            continue


        if token.upper() in {
            "FINAL",
            "LIVE",
            "WATCH",
            "BOX SCORE",
            "ESPN",
            "ESPN2",
            "ESPN+",
            "ABC",
        }:
            continue


        if re.fullmatch(
            r"\d{1,2}",
            token
        ):
            return token


    return None


def determine_game_status(
    scheduled_dt,
    score1,
    score2,
    block_tokens
):

    if (
        score1 is None
        or score2 is None
    ):
        return ""


    now = datetime.now(
        EASTERN
    )


    text = " ".join(
        block_tokens
    ).upper()


    # Use an explicit FINAL label if Little League supplies one.
    if "FINAL" in text:
        return "FINAL"


    # If a numeric score is published near the scheduled game time,
    # treat it as an in-progress score.
    live_until = (
        scheduled_dt
        + timedelta(
            hours=LIVE_WINDOW_HOURS
        )
    )


    if (
        scheduled_dt
        <= now
        < live_until
    ):
        return "LIVE"


    # Any scored game outside the live window is treated as complete.
    return "FINAL"


def parse_region_page(
    region,
    url
):

    tokens = fetch_tokens(
        url
    )

    source_timezone = (
        page_timezone(tokens)
    )

    games = []


    for block in split_into_game_blocks(
        tokens
    ):

        (
            date_iso,
            game_time,
            scheduled_dt

        ) = find_date_and_time(
            block["tokens"],
            source_timezone
        )


        (
            teams,
            raw_teams

        ) = extract_region_teams(
            block["tokens"]
        )


        if (
            not date_iso
            or not game_time
            or scheduled_dt is None
            or len(teams) < 2
            or len(raw_teams) < 2
        ):
            continue


        score1 = score_for_team(
            block["tokens"],
            raw_teams[0],
            raw_teams[1]
        )


        score2 = score_for_team(
            block["tokens"],
            raw_teams[1],
            "__END_OF_GAME__"
        )


        status = determine_game_status(
            scheduled_dt,
            score1,
            score2,
            block["tokens"]
        )


        if status in {
            "LIVE",
            "FINAL"
        }:

            matchup = (
                f"{teams[0]} {score1}"
                f" — "
                f"{teams[1]} {score2}"
            )

        else:

            matchup = (
                f"{teams[0]}"
                f" vs "
                f"{teams[1]}"
            )


        games.append({
            "date": date_iso,
            "time": game_time,
            "region": region,
            "matchup": matchup,
            "status": status,
            "game_number": block["game_number"]
        })


    return games


def participant_map_from_tokens(
    tokens
):

    try:

        end_index = tokens.index(
            "Tournament Schedule"
        )

        prefix = tokens[
            :end_index
        ]

    except ValueError:

        prefix = tokens


    mapping = {}


    for region in PARTICIPANT_REGIONS:

        try:

            index = prefix.index(
                region
            )

        except ValueError:

            continue


        if (
            index + 1
            >= len(prefix)
        ):
            continue


        team = prefix[
            index + 1
        ]


        if team not in {
            "TBA",
            "Team",
            "City/State",
            "City/Country",
            "Record"
        }:

            mapping[
                region
            ] = team


    return mapping


def normalize_world_region(
    label
):

    if label == "Europe & Africa Region":

        return "Europe-Africa Region"

    return label


def world_side_candidates(
    block_tokens
):

    sides = []


    for token in block_tokens:

        normalized = (
            normalize_world_region(
                token
            )
        )


        if normalized in WORLD_REGION_LABELS:

            if normalized not in sides:

                sides.append(
                    normalized
                )


        elif re.fullmatch(
            r"[WL]\d+",
            token
        ):

            if token not in sides:

                sides.append(
                    token
                )


    return sides[:2]


def display_world_side(
    side,
    participants
):

    if not side.endswith(
        " Region"
    ):

        return side


    region = side[:-7]


    if region == "Europe-Africa":

        participant_key = (
            "Europe & Africa"
        )

    else:

        participant_key = region


    team = participants.get(
        participant_key
    )


    if team:

        return (
            f"{team} "
            f"({region})"
        )


    return side


def parse_world_series_page():

    tokens = fetch_tokens(
        WORLD_SERIES_URL
    )


    participants = (
        participant_map_from_tokens(
            tokens
        )
    )


    games = []


    for block in split_into_game_blocks(
        tokens
    ):

        if block["game_number"] > 38:
            continue


        (
            date_iso,
            game_time,
            scheduled_dt

        ) = find_date_and_time(
            block["tokens"],
            "America/New_York"
        )


        sides = world_side_candidates(
            block["tokens"]
        )


        if (
            not date_iso
            or not game_time
            or scheduled_dt is None
            or len(sides) < 2
        ):
            continue


        display_sides = [
            display_world_side(
                side,
                participants
            )
            for side in sides
        ]


        # World Series score parsing will use the same general
        # numeric logic once games begin.
        score1 = score_for_team(
            block["tokens"],
            sides[0],
            sides[1]
        )

        score2 = score_for_team(
            block["tokens"],
            sides[1],
            "__END_OF_GAME__"
        )


        status = determine_game_status(
            scheduled_dt,
            score1,
            score2,
            block["tokens"]
        )


        if (
            status in {"LIVE", "FINAL"}
            and score1 is not None
            and score2 is not None
        ):

            matchup = (
                f"{display_sides[0]} {score1}"
                f" — "
                f"{display_sides[1]} {score2}"
            )

        else:

            matchup = (
                f"{display_sides[0]}"
                f" vs "
                f"{display_sides[1]}"
            )


        games.append({
            "date": date_iso,
            "time": game_time,
            "region": "World Series",
            "matchup": matchup,
            "status": status,
            "game_number": block["game_number"]
        })


    return (
        games,
        participants
    )


def add_world_series_base_games():

    existing = {
        (
            game["date"],
            game["time"],
            game["region"]
        )
        for game in BASE
    }


    for (
        date_iso,
        game_time,
        matchup,
        tv

    ) in WORLD_SERIES_GAMES:

        key = (
            date_iso,
            game_time,
            "World Series"
        )


        if key in existing:
            continue


        BASE.append({
            "date": date_iso,
            "time": game_time,
            "region": "World Series",
            "matchup": matchup,
            "tv": tv,
            "status": ""
        })


add_world_series_base_games()


scraped = []
errors = []


for region, url in URLS.items():

    try:

        region_games = parse_region_page(
            region,
            url
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


    time.sleep(
        0.15
    )


participants = {}


try:

    (
        world_games,
        participants

    ) = parse_world_series_page()


    scraped.extend(
        world_games
    )


    if not world_games:

        errors.append(
            "World Series: no games parsed"
        )


except Exception as exc:

    errors.append(
        "World Series: "
        f"{type(exc).__name__}: "
        f"{exc}"
    )


lookup = {
    (
        game["date"],
        game["time"],
        game["region"]
    ): game

    for game in scraped
}


output = []

matched = 0


for base_game in BASE:

    row = dict(
        base_game
    )


    official = lookup.get(
        (
            row["date"],
            row["time"],
            row["region"]
        )
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


output.sort(
    key=lambda game: (
        game["date"],
        datetime.strptime(
            game["time"],
            "%I:%M %p"
        ).time()
    )
)


payload = {
    "updated":
        datetime.now(
            UTC
        ).strftime(
            "%Y-%m-%d %H:%M UTC"
        ),

    "source":
        "Official LittleLeague.org "
        "region and World Series schedules",

    "scraped_games":
        len(scraped),

    "matched_games":
        matched,

    "world_series_participants":
        participants,

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
    "\n--- LIVE GAMES ---"
)

live_count = 0

for game in scraped:

    if game["status"] == "LIVE":

        live_count += 1

        print(
            game["region"],
            game["date"],
            game["time"],
            game["matchup"],
            "LIVE"
        )


if live_count == 0:

    print(
        "No live games detected."
    )


print(
    "\n--- GREAT LAKES RESULTS ---"
)

for game in scraped:

    if game["region"] == "Great Lakes":

        print(
            game["date"],
            game["time"],
            game["matchup"],
            game["status"]
        )


print(
    "\n--- SOUTHWEST RESULTS ---"
)

for game in scraped:

    if game["region"] == "Southwest":

        print(
            game["date"],
            game["time"],
            game["matchup"],
            game["status"]
        )


print(
    "\n--- WEST RESULTS ---"
)

for game in scraped:

    if game["region"] == "West":

        print(
            game["date"],
            game["time"],
            game["matchup"],
            game["status"]
        )


print(
    "\n--- MID-ATLANTIC RESULTS ---"
)

for game in scraped:

    if game["region"] == "Mid-Atlantic":

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
