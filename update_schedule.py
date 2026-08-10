import json
import re
import time
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, Tag
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent

EASTERN = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

BASE = json.loads(
    (ROOT / "base_schedule.json").read_text(encoding="utf-8")
)

GC_BEFORE_MINUTES = 20
GC_AFTER_HOURS = 4


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
        "(compatible; personal LLWS schedule dashboard/8.0)"
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
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_team(value):
    value = clean(value).lower()

    value = value.replace("washington, d.c.", "washington, dc")
    value = value.replace("southern california", "southern calif")
    value = value.replace("northern california", "northern calif")

    return value


def team_matches(value, team):
    value = normalize_team(value)
    team = normalize_team(team)

    return (
        value == team
        or team in value
        or value in team
    )


def fetch_soup(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser"
    )


def fetch_tokens(url):
    soup = fetch_soup(url)

    return [
        clean(x)
        for x in soup.stripped_strings
        if clean(x)
    ]


def get_gamechanger_links(url):
    soup = fetch_soup(url)

    links = {}
    game_markers = []

    for tag in soup.find_all(
        string=re.compile(r"^\s*Game\s+\d+\b", re.I)
    ):

        text = clean(str(tag))

        match = re.match(
            r"^Game\s+(\d+)\b",
            text,
            re.I
        )

        if not match:
            continue

        game_number = int(match.group(1))

        parent = (
            tag.parent
            if isinstance(tag.parent, Tag)
            else None
        )

        if parent:
            game_markers.append(
                (game_number, parent)
            )

    for game_number, marker in game_markers:

        node = marker
        found = None

        for _ in range(8):

            if not isinstance(node, Tag):
                break

            text = clean(
                node.get_text(
                    " ",
                    strip=True
                )
            )

            game_numbers = re.findall(
                r"\bGame\s+(\d+)\b",
                text,
                re.I
            )

            gc_links = [
                a.get("href")
                for a in node.find_all(
                    "a",
                    href=True
                )
                if "web.gc.com/" in a.get("href", "")
            ]

            if (
                len(set(game_numbers)) == 1
                and gc_links
            ):
                found = gc_links[0]
                break

            node = node.parent

        if found:
            links[game_number] = found

    return links


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

    text = " ".join(block_tokens)

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

    day = int(match.group(4))

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

    return (
        eastern.strftime("%Y-%m-%d"),
        eastern.strftime("%-I:%M %p"),
        eastern
    )


def extract_region_teams(block_tokens):
    teams = []
    raw_teams = []

    for token in block_tokens:

        if token in TEAM_ALIASES:

            normalized = TEAM_ALIASES[token]

            if normalized not in teams:
                teams.append(normalized)
                raw_teams.append(token)

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
        start = block_tokens.index(raw_team)

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


def static_status(
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

    text = " ".join(
        block_tokens
    ).upper()

    if "FINAL" in text:
        return "FINAL"

    now = datetime.now(
        EASTERN
    )

    if now >= (
        scheduled_dt
        + timedelta(hours=3)
    ):
        return "FINAL"

    return "LIVE"


def parse_region_page(
    region,
    url
):

    tokens = fetch_tokens(url)

    gc_links = get_gamechanger_links(
        url
    )

    source_timezone = page_timezone(
        tokens
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

        status = static_status(
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
            "game_number": block["game_number"],
            "scheduled_dt": scheduled_dt,
            "team1": teams[0],
            "team2": teams[1],
            "gc_url": gc_links.get(
                block["game_number"]
            )
        })

    return games


def participant_map_from_tokens(tokens):
    try:
        end_index = tokens.index(
            "Tournament Schedule"
        )

        prefix = tokens[:end_index]

    except ValueError:
        prefix = tokens

    mapping = {}

    for region in PARTICIPANT_REGIONS:

        try:
            index = prefix.index(region)

        except ValueError:
            continue

        if index + 1 >= len(prefix):
            continue

        team = prefix[index + 1]

        if team not in {
            "TBA",
            "Team",
            "City/State",
            "City/Country",
            "Record"
        }:
            mapping[region] = team

    return mapping


def normalize_world_region(label):
    if label == "Europe & Africa Region":
        return "Europe-Africa Region"

    return label


def world_side_candidates(block_tokens):
    sides = []

    for token in block_tokens:

        normalized = normalize_world_region(
            token
        )

        if normalized in WORLD_REGION_LABELS:

            if normalized not in sides:
                sides.append(normalized)

        elif re.fullmatch(
            r"[WL]\d+",
            token
        ):

            if token not in sides:
                sides.append(token)

    return sides[:2]


def display_world_side(
    side,
    participants
):

    if not side.endswith(" Region"):
        return side

    region = side[:-7]

    if region == "Europe-Africa":
        participant_key = "Europe & Africa"
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

    participants = participant_map_from_tokens(
        tokens
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

        games.append({
            "date": date_iso,
            "time": game_time,
            "region": "World Series",
            "matchup":
                f"{display_sides[0]}"
                f" vs "
                f"{display_sides[1]}",
            "status": "",
            "game_number": block["game_number"],
            "scheduled_dt": scheduled_dt,
            "team1": display_sides[0],
            "team2": display_sides[1],
            "gc_url": None
        })

    return games, participants


# =====================================================
# GAMECHANGER LIVE SCORE HELPERS
# =====================================================


def valid_score(value):
    try:
        number = int(value)
    except (ValueError, TypeError):
        return None

    if 0 <= number <= 30:
        return str(number)

    return None


def find_score_fields(obj):
    """
    Search one JSON dictionary for likely score fields.
    """

    if not isinstance(obj, dict):
        return None

    preferred = [
        "score",
        "runs",
        "points",
        "totalScore",
        "total_score",
        "teamScore",
        "team_score",
    ]

    for key in preferred:

        if key in obj:

            score = valid_score(
                obj[key]
            )

            if score is not None:
                return score

    for key, value in obj.items():

        lower = str(key).lower()

        if (
            "score" in lower
            or lower == "runs"
            or lower.endswith("_runs")
        ):

            score = valid_score(value)

            if score is not None:
                return score

    return None


def extract_team_records(
    obj,
    team1,
    team2,
    found=None
):

    """
    Recursively search GameChanger JSON data for dictionaries
    that contain a team name and a nearby score field.
    """

    if found is None:
        found = {
            "team1": [],
            "team2": []
        }

    if isinstance(obj, dict):

        scalar_text = " ".join(
            str(value)
            for value in obj.values()
            if isinstance(
                value,
                (
                    str,
                    int,
                    float
                )
            )
        )

        score = find_score_fields(
            obj
        )

        if score is not None:

            if team_matches(
                scalar_text,
                team1
            ):
                found[
                    "team1"
                ].append(
                    (
                        score,
                        scalar_text[:250]
                    )
                )

            if team_matches(
                scalar_text,
                team2
            ):
                found[
                    "team2"
                ].append(
                    (
                        score,
                        scalar_text[:250]
                    )
                )

        for value in obj.values():

            if isinstance(
                value,
                (dict, list)
            ):

                extract_team_records(
                    value,
                    team1,
                    team2,
                    found
                )

    elif isinstance(obj, list):

        for value in obj:

            extract_team_records(
                value,
                team1,
                team2,
                found
            )

    return found


def choose_unique_score(records):
    scores = []

    for score, _ in records:

        if score not in scores:
            scores.append(score)

    if len(scores) == 1:
        return scores[0]

    return None


def inspect_gc_json(
    captured_json,
    game
):

    combined = {
        "team1": [],
        "team2": []
    }

    for payload in captured_json:

        found = extract_team_records(
            payload,
            game["team1"],
            game["team2"]
        )

        combined[
            "team1"
        ].extend(
            found["team1"]
        )

        combined[
            "team2"
        ].extend(
            found["team2"]
        )

    score1 = choose_unique_score(
        combined["team1"]
    )

    score2 = choose_unique_score(
        combined["team2"]
    )

    if (
        score1 is None
        or score2 is None
    ):
        return None

    print(
        "  GC JSON MATCH:",
        game["team1"],
        score1,
        "—",
        game["team2"],
        score2
    )

    return {
        "score1": score1,
        "score2": score2,
        "method": "JSON"
    }


def find_score_in_team_row(
    page,
    team_name,
    other_team
):

    return page.evaluate(
        """
        ({teamName, otherTeam}) => {

            function norm(value) {
                return (value || "")
                    .replace(/\\s+/g, " ")
                    .trim()
                    .toLowerCase();
            }

            function validScore(value) {
                if (!/^\\d{1,2}$/.test(value)) {
                    return false;
                }

                const n = Number(value);

                return n >= 0 && n <= 30;
            }

            const wanted = norm(teamName);
            const other = norm(otherTeam);

            const elements =
                Array.from(
                    document.querySelectorAll("body *")
                );

            const matches =
                elements.filter(el => {

                    const txt =
                        norm(el.innerText);

                    if (!txt) {
                        return false;
                    }

                    return txt.includes(
                        wanted
                    );
                });

            for (const el of matches) {

                let node = el;

                for (
                    let depth = 0;
                    depth < 9 && node;
                    depth++
                ) {

                    const text =
                        (node.innerText || "")
                        .replace(/\\s+/g, " ")
                        .trim();

                    const normalized =
                        norm(text);

                    if (
                        normalized.includes(wanted)
                        &&
                        !normalized.includes(other)
                    ) {

                        const nums =
                            text.match(
                                /(?:^|\\s)(\\d{1,2})(?=\\s|$)/g
                            );

                        if (nums) {

                            const cleanNums =
                                nums
                                .map(x => x.trim())
                                .filter(validScore);

                            const unique =
                                [...new Set(cleanNums)];

                            if (
                                unique.length === 1
                            ) {

                                return {
                                    score:
                                        unique[0],

                                    rowText:
                                        text
                                };
                            }
                        }
                    }

                    node =
                        node.parentElement;
                }
            }

            return null;
        }
        """,
        {
            "teamName": team_name,
            "otherTeam": other_team
        }
    )


def score_from_visible_lines(
    body_text,
    team_name
):

    """
    Last-resort parser.

    Finds the team name in the visible page text and looks
    immediately around it for a reasonable baseball score.
    """

    lines = [
        clean(line)
        for line in body_text.splitlines()
        if clean(line)
    ]

    wanted = normalize_team(
        team_name
    )

    candidates = []

    for index, line in enumerate(lines):

        if wanted not in normalize_team(
            line
        ):
            continue

        start = max(
            0,
            index - 2
        )

        end = min(
            len(lines),
            index + 4
        )

        nearby = lines[
            start:end
        ]

        for offset, nearby_line in enumerate(
            nearby
        ):

            if normalize_team(
                nearby_line
            ) == wanted:

                continue

            match = re.fullmatch(
                r"\d{1,2}",
                nearby_line
            )

            if not match:
                continue

            score = valid_score(
                nearby_line
            )

            if score is None:
                continue

            distance = abs(
                (start + offset)
                - index
            )

            candidates.append(
                (
                    distance,
                    score,
                    nearby
                )
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0]
    )

    best_distance = candidates[0][0]

    best = [
        item
        for item in candidates
        if item[0] == best_distance
    ]

    unique_scores = []

    for _, score, _ in best:

        if score not in unique_scores:
            unique_scores.append(score)

    if len(unique_scores) != 1:
        return None

    return {
        "score": unique_scores[0],
        "context":
            " | ".join(
                best[0][2]
            )[:300]
    }


def inspect_gamechanger(
    page,
    game
):

    url = game.get(
        "gc_url"
    )

    if not url:
        return None

    print(
        "GC CHECK:",
        game["region"],
        "Game",
        game["game_number"],
        game["team1"],
        "vs",
        game["team2"]
    )

    print(
        "  URL:",
        url
    )

    captured_json = []

    def capture_response(response):

        try:

            content_type = (
                response.headers.get(
                    "content-type",
                    ""
                ).lower()
            )

            if "json" not in content_type:
                return

            payload = response.json()

            captured_json.append(
                payload
            )

        except Exception:
            pass

    page.on(
        "response",
        capture_response
    )

    try:

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=45000
        )

        page.wait_for_timeout(
            5000
        )

        body_text = (
            page.locator(
                "body"
            ).inner_text()
        )

        if not body_text:

            print(
                "  GC SKIP: empty page"
            )

            return None

        # ---------------------------------------------
        # METHOD 1:
        # GameChanger JSON / API responses
        # ---------------------------------------------

        json_result = inspect_gc_json(
            captured_json,
            game
        )

        if json_result:

            score1 = json_result[
                "score1"
            ]

            score2 = json_result[
                "score2"
            ]

            method = "JSON"

        else:

            # -----------------------------------------
            # METHOD 2:
            # rendered team rows/cards
            # -----------------------------------------

            row1 = find_score_in_team_row(
                page,
                game["team1"],
                game["team2"]
            )

            row2 = find_score_in_team_row(
                page,
                game["team2"],
                game["team1"]
            )

            if (
                row1
                and row2
            ):

                score1 = row1[
                    "score"
                ]

                score2 = row2[
                    "score"
                ]

                method = "DOM"

                print(
                    "  GC DOM ROW 1:",
                    row1["rowText"][:250]
                )

                print(
                    "  GC DOM ROW 2:",
                    row2["rowText"][:250]
                )

            else:

                # -------------------------------------
                # METHOD 3:
                # visible text around team names
                # -------------------------------------

                text1 = score_from_visible_lines(
                    body_text,
                    game["team1"]
                )

                text2 = score_from_visible_lines(
                    body_text,
                    game["team2"]
                )

                if (
                    not text1
                    or not text2
                ):

                    print(
                        "  GC SKIP: no reliable "
                        "score pair found by JSON, "
                        "DOM, or visible-text methods"
                    )

                    return None

                score1 = text1[
                    "score"
                ]

                score2 = text2[
                    "score"
                ]

                method = "TEXT"

                print(
                    "  GC TEXT 1:",
                    text1["context"]
                )

                print(
                    "  GC TEXT 2:",
                    text2["context"]
                )

        score1 = valid_score(
            score1
        )

        score2 = valid_score(
            score2
        )

        if (
            score1 is None
            or score2 is None
        ):

            print(
                "  GC SKIP: invalid score pair"
            )

            return None

        upper = body_text.upper()

        if (
            "FINAL" in upper
            or "GAME OVER" in upper
        ):
            status = "FINAL"

        else:
            status = "LIVE"

        print(
            "  GC RESULT:",
            game["team1"],
            score1,
            "—",
            game["team2"],
            score2,
            status,
            f"({method})"
        )

        return {
            "score1": score1,
            "score2": score2,
            "status": status,
            "method": method
        }

    except Exception as exc:

        print(
            "  GC ERROR:",
            type(exc).__name__,
            exc
        )

        return None

    finally:

        page.remove_listener(
            "response",
            capture_response
        )


def should_check_gc(game):

    if not game.get(
        "gc_url"
    ):
        return False

    if game.get(
        "status"
    ) == "FINAL":
        return False

    scheduled = game.get(
        "scheduled_dt"
    )

    if scheduled is None:
        return False

    now = datetime.now(
        EASTERN
    )

    start = (
        scheduled
        - timedelta(
            minutes=
                GC_BEFORE_MINUTES
        )
    )

    end = (
        scheduled
        + timedelta(
            hours=
                GC_AFTER_HOURS
        )
    )

    return (
        start
        <= now
        <= end
    )


def apply_gamechanger_live(
    scraped
):

    candidates = [
        game
        for game in scraped
        if should_check_gc(
            game
        )
    ]

    print(
        "\n--- GAMECHANGER LIVE CHECK ---"
    )

    if not candidates:

        print(
            "No GameChanger live candidates."
        )

        return scraped

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        context = browser.new_context(
            viewport={
                "width": 1280,
                "height": 1200
            }
        )

        page = context.new_page()

        for game in candidates:

            result = inspect_gamechanger(
                page,
                game
            )

            if not result:
                continue

            game["matchup"] = (
                f"{game['team1']} "
                f"{result['score1']}"
                f" — "
                f"{game['team2']} "
                f"{result['score2']}"
            )

            game["status"] = (
                result["status"]
            )

        browser.close()

    return scraped


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

        region_games = (
            parse_region_page(
                region,
                url
            )
        )

        scraped.extend(
            region_games
        )

        if not region_games:

            errors.append(
                f"{region}: "
                f"no games parsed"
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

except Exception as exc:

    errors.append(
        "World Series: "
        f"{type(exc).__name__}: "
        f"{exc}"
    )


scraped = apply_gamechanger_live(
    scraped
)


lookup = {
    (
        game["date"],
        game["time"],
        game["region"]
    ):
        game
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
        "schedules + GameChanger "
        "live scoring",

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
    "\nScraped games:",
    len(scraped)
)

print(
    "Matched games:",
    matched
)

print(
    "\n--- LIVE GAMES WRITTEN ---"
)


live_games = [
    game
    for game in scraped
    if game.get(
        "status"
    ) == "LIVE"
]


if not live_games:

    print(
        "No live scores written."
    )


for game in live_games:

    print(
        game["region"],
        game["date"],
        game["time"],
        game["matchup"],
        "LIVE"
    )


print(
    "\n--- TODAY'S GAMECHANGER STATUS ---"
)


for game in scraped:

    if game["date"] == "2026-08-10":

        scheduled = game.get(
            "scheduled_dt"
        )

        if not scheduled:
            continue

        if (
            scheduled
            - timedelta(
                minutes=GC_BEFORE_MINUTES
            )
            <= datetime.now(EASTERN)
            <= scheduled
            + timedelta(
                hours=GC_AFTER_HOURS
            )
        ):

            print(
                game["region"],
                "Game",
                game["game_number"],
                game["time"],
                game["matchup"],
                game["status"],
                "GC:",
                game.get("gc_url")
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
