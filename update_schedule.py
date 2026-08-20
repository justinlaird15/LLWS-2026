import json
import re
import time
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, Tag
from playwright.sync_api import sync_playwright


# ============================================================
# SETTINGS
# ============================================================

ROOT = Path(__file__).resolve().parent

EASTERN = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

BASE = json.loads(
    (ROOT / "base_schedule.json").read_text(
        encoding="utf-8"
    )
)

GC_BEFORE_MINUTES = 20
GC_AFTER_HOURS = 6


# ============================================================
# LITTLE LEAGUE URLS
# ============================================================

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
    "https://www.littleleague.org/world-series/2026/"
    "llbws/tournaments/world-series/"
)


HEADERS = {
    "User-Agent":
        "Mozilla/5.0 "
        "(compatible; personal LLWS schedule dashboard/10.0)"
}


# ============================================================
# TIME ZONES
# ============================================================

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


# ============================================================
# REGIONAL TEAM NAMES
# ============================================================

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

    "Southern California":
        "Southern California",

    "Southern Calif.":
        "Southern California",

    "Northern California":
        "Northern California",

    "Northern Calif.":
        "Northern California",

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


# ============================================================
# WORLD SERIES REGIONS
# ============================================================

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


# ============================================================
# WORLD SERIES TV BY GAME NUMBER
#
# IMPORTANT:
# TV is attached to the GAME NUMBER, not date/time.
# Therefore weather changes do not create duplicate games.
# ============================================================

WORLD_SERIES_TV = {
    1: "ESPN",
    2: "ESPN",
    3: "ESPN",
    4: "ESPN",

    # Official Aug. 20 update:
    # ESPN will not broadcast Games 5 and 6.
    5: "NO ESPN",
    6: "NO ESPN",

    # Network listings were still TBD after weather change.
    7: "TBD",
    8: "TBD",
    9: "TBD",
    10: "TBD",
    11: "TBD",
    12: "TBD",

    13: "ESPN",
    14: "ESPN",
    15: "ESPN",
    16: "ESPN",

    17: "ESPN",
    18: "ESPN",
    19: "ABC",
    20: "ESPN",

    21: "ESPN",
    22: "ESPN",
    23: "ESPN",
    24: "ESPN",

    25: "ESPN",
    26: "ESPN",
    27: "ESPN",
    28: "ESPN",

    29: "ESPN",
    30: "ESPN",
    31: "ESPN",
    32: "ESPN",

    33: "ESPN",
    34: "ESPN",

    35: "ABC",
    36: "ABC",

    37: "ESPN",
    38: "ABC",
}


# ============================================================
# OFFICIAL WEATHER-ADJUSTED SCHEDULE
#
# Little League announced all Aug. 20 games postponed.
# Games 5-12 now play Friday Aug. 21.
# ============================================================

WORLD_SERIES_SCHEDULE_OVERRIDES = {

    5: (
        "2026-08-21",
        "9:00 AM"
    ),

    6: (
        "2026-08-21",
        "9:00 AM"
    ),

    7: (
        "2026-08-21",
        "12:00 PM"
    ),

    8: (
        "2026-08-21",
        "12:00 PM"
    ),

    9: (
        "2026-08-21",
        "3:00 PM"
    ),

    10: (
        "2026-08-21",
        "3:00 PM"
    ),

    11: (
        "2026-08-21",
        "6:00 PM"
    ),

    12: (
        "2026-08-21",
        "7:00 PM"
    ),
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean(value):

    return re.sub(
        r"\s+",
        " ",
        value or ""
    ).strip()


def normalize_team(value):

    value = clean(
        value
    ).lower()

    value = value.replace(
        "washington, d.c.",
        "washington, dc"
    )

    value = value.replace(
        "southern california",
        "southern calif"
    )

    value = value.replace(
        "northern california",
        "northern calif"
    )

    value = value.replace(
        "little league",
        "ll"
    )

    return value


def team_matches(
    value,
    team
):

    value = normalize_team(
        value
    )

    team = normalize_team(
        team
    )

    return (
        value == team
        or team in value
        or value in team
    )


def valid_score(value):

    try:

        number = int(
            value
        )

    except (
        ValueError,
        TypeError
    ):

        return None


    if (
        0
        <= number
        <= 30
    ):

        return str(
            number
        )


    return None


def eastern_datetime(
    date_iso,
    time_text
):

    dt = datetime.strptime(
        f"{date_iso} {time_text}",
        "%Y-%m-%d %I:%M %p"
    )

    return dt.replace(
        tzinfo=EASTERN
    )


# ============================================================
# HTTP
# ============================================================

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

    soup = fetch_soup(
        url
    )

    return [

        clean(x)

        for x
        in soup.stripped_strings

        if clean(x)
    ]


# ============================================================
# GAMECHANGER LINK MAPPING
# ============================================================

def get_gamechanger_links(url):

    soup = fetch_soup(
        url
    )

    links = {}

    game_markers = []


    for tag in soup.find_all(
        string=re.compile(
            r"^\s*Game\s+\d+\b",
            re.I
        )
    ):

        text = clean(
            str(tag)
        )

        match = re.match(
            r"^Game\s+(\d+)\b",
            text,
            re.I
        )


        if not match:

            continue


        game_number = int(
            match.group(1)
        )


        parent = (
            tag.parent
            if isinstance(
                tag.parent,
                Tag
            )
            else None
        )


        if parent:

            game_markers.append(
                (
                    game_number,
                    parent
                )
            )


    for (
        game_number,
        marker
    ) in game_markers:

        node = marker

        found = None


        for _ in range(
            8
        ):

            if not isinstance(
                node,
                Tag
            ):

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

                a.get(
                    "href"
                )

                for a in node.find_all(
                    "a",
                    href=True
                )

                if (
                    "web.gc.com/"
                    in a.get(
                        "href",
                        ""
                    )
                )
            ]


            if (
                len(
                    set(
                        game_numbers
                    )
                )
                == 1
                and gc_links
            ):

                found = (
                    gc_links[
                        0
                    ]
                )

                break


            node = (
                node.parent
            )


        if found:

            links[
                game_number
            ] = found


    return links


# ============================================================
# SPLIT PAGE INTO GAME BLOCKS
# ============================================================

def split_into_game_blocks(
    tokens
):

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

                blocks.append(
                    current
                )


            current = {

                "game_number":
                    int(
                        match.group(
                            1
                        )
                    ),

                "tokens":
                    [token]
            }


            continue


        if current:

            current[
                "tokens"
            ].append(
                token
            )


    if current:

        blocks.append(
            current
        )


    return blocks


# ============================================================
# DATE / TIME
# ============================================================

def page_timezone(
    tokens
):

    text = " ".join(
        tokens
    )


    match = re.search(
        r"All game times are "
        r"(Eastern|Central|Mountain|Pacific) time",
        text,
        re.I
    )


    if match:

        return TZ_MAP[
            match.group(
                1
            ).title()
        ]


    return (
        "America/New_York"
    )


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

        r"(?:\s*\(?\s*"
        r"(ET|CT|MT|PT)"
        r"\s*\)?)?"

        r"\s*-\s*August\s+"

        r"(\d{1,2})",

        text,
        re.I
    )


    if not match:

        return (
            None,
            None,
            None
        )


    time_text = (
        match.group(
            1
        )
        + " "
        + match.group(
            2
        ).upper()
        + "M"
    )


    explicit_tz = (
        match.group(
            3
        )
    )


    day = int(
        match.group(
            4
        )
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

        tz_name = (
            source_timezone
        )


    dt = datetime.strptime(

        f"{source_date} "
        f"{time_text}",

        "%Y-%m-%d %I:%M %p"
    )


    dt = dt.replace(
        tzinfo=ZoneInfo(
            tz_name
        )
    )


    eastern = dt.astimezone(
        EASTERN
    )


    return (

        eastern.strftime(
            "%Y-%m-%d"
        ),

        eastern.strftime(
            "%-I:%M %p"
        ),

        eastern
    )


# ============================================================
# REGIONAL TEAM EXTRACTION
# ============================================================

def extract_region_teams(
    block_tokens
):

    teams = []

    raw_teams = []


    for token in block_tokens:

        if token in TEAM_ALIASES:

            normalized = (
                TEAM_ALIASES[
                    token
                ]
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

        start = (
            block_tokens.index(
                raw_team
            )
        )

    except ValueError:

        return None


    try:

        end = (
            block_tokens.index(
                other_raw_team,
                start + 1
            )
        )

    except ValueError:

        end = min(
            len(
                block_tokens
            ),
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
            "RECAP",

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


    if (
        "FINAL" in text
        or "GAME OVER" in text
        or "RECAP" in text
    ):

        return "FINAL"


    now = datetime.now(
        EASTERN
    )


    if now >= (
        scheduled_dt
        + timedelta(
            hours=3
        )
    ):

        return "FINAL"


    return "LIVE"


# ============================================================
# REGIONAL PAGE PARSER
# ============================================================

def parse_region_page(
    region,
    url
):

    tokens = fetch_tokens(
        url
    )


    gc_links = (
        get_gamechanger_links(
            url
        )
    )


    source_timezone = (
        page_timezone(
            tokens
        )
    )


    games = []


    for block in (
        split_into_game_blocks(
            tokens
        )
    ):

        (
            date_iso,
            game_time,
            scheduled_dt

        ) = find_date_and_time(

            block[
                "tokens"
            ],

            source_timezone
        )


        (
            teams,
            raw_teams

        ) = extract_region_teams(
            block[
                "tokens"
            ]
        )


        if (
            not date_iso
            or not game_time
            or scheduled_dt is None
            or len(
                teams
            ) < 2
            or len(
                raw_teams
            ) < 2
        ):

            continue


        score1 = score_for_team(

            block[
                "tokens"
            ],

            raw_teams[
                0
            ],

            raw_teams[
                1
            ]
        )


        score2 = score_for_team(

            block[
                "tokens"
            ],

            raw_teams[
                1
            ],

            "__END_OF_GAME__"
        )


        status = static_status(

            scheduled_dt,
            score1,
            score2,

            block[
                "tokens"
            ]
        )


        if status in {
            "LIVE",
            "FINAL"
        }:

            matchup = (

                f"{teams[0]} "
                f"{score1}"

                f" — "

                f"{teams[1]} "
                f"{score2}"
            )

        else:

            matchup = (

                f"{teams[0]}"

                f" vs "

                f"{teams[1]}"
            )


        games.append({

            "date":
                date_iso,

            "time":
                game_time,

            "region":
                region,

            "matchup":
                matchup,

            "status":
                status,

            "game_number":
                block[
                    "game_number"
                ],

            "scheduled_dt":
                scheduled_dt,

            "team1":
                teams[
                    0
                ],

            "team2":
                teams[
                    1
                ],

            "gc_team1":
                teams[
                    0
                ],

            "gc_team2":
                teams[
                    1
                ],

            "gc_url":
                gc_links.get(
                    block[
                        "game_number"
                    ]
                ),

            "tv":
                None
        })


    return games


# ============================================================
# WORLD SERIES PARTICIPANTS
# ============================================================

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


    for region in (
        PARTICIPANT_REGIONS
    ):

        try:

            index = prefix.index(
                region
            )

        except ValueError:

            continue


        if (
            index + 1
            >= len(
                prefix
            )
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

    if (
        label
        == "Europe & Africa Region"
    ):

        return (
            "Europe-Africa Region"
        )


    return label


def participant_key_from_region_label(
    label
):

    if not label.endswith(
        " Region"
    ):

        return None


    region = label[
        :-7
    ]


    if (
        region
        == "Europe-Africa"
    ):

        return (
            "Europe & Africa"
        )


    return region


def display_world_side(
    side,
    participants
):

    if side == "TBA":

        return (
            "TBA"
        )


    if not side.endswith(
        " Region"
    ):

        return side


    participant_key = (
        participant_key_from_region_label(
            side
        )
    )


    team = participants.get(
        participant_key
    )


    if team:

        region = side[
            :-7
        ]


        return (

            f"{team} "
            f"({region})"
        )


    return side


def gc_world_side_name(
    side,
    participants
):

    if side == "TBA":

        return "TBA"


    if not side.endswith(
        " Region"
    ):

        return side


    participant_key = (
        participant_key_from_region_label(
            side
        )
    )


    return participants.get(
        participant_key,
        side
    )


# ============================================================
# WORLD SERIES ROW PARSER
#
# This keeps W1/L3/etc. attached to the proper team row.
# ============================================================

def extract_world_rows(
    block_tokens
):

    row_markers = []


    for (
        index,
        token
    ) in enumerate(
        block_tokens
    ):

        normalized = (
            normalize_world_region(
                token
            )
        )


        if (
            normalized
            in WORLD_REGION_LABELS
            or token == "TBA"
        ):

            row_markers.append(
                (
                    index,

                    normalized
                    if normalized
                    in WORLD_REGION_LABELS

                    else "TBA"
                )
            )


    if len(
        row_markers
    ) < 2:

        return []


    rows = []


    for row_number in range(
        2
    ):

        (
            start_index,
            label
        ) = row_markers[
            row_number
        ]


        if row_number == 0:

            end_index = (
                row_markers[
                    1
                ][0]
            )

        else:

            end_index = min(

                len(
                    block_tokens
                ),

                start_index
                + 14
            )


        segment = block_tokens[
            start_index + 1:
            end_index
        ]


        bracket_ref = None

        score = None


        for token in segment:

            if (
                bracket_ref is None
                and re.fullmatch(
                    r"[WL]\d+",
                    token,
                    re.I
                )
            ):

                bracket_ref = (
                    token.upper()
                )

                continue


            if (
                score is None
                and re.fullmatch(
                    r"\d{1,2}",
                    token
                )
            ):

                possible = (
                    valid_score(
                        token
                    )
                )


                if possible is not None:

                    score = (
                        possible
                    )


        if label == "TBA":

            side = (
                bracket_ref
                or "TBA"
            )

        else:

            side = label


        rows.append({

            "side":
                side,

            "label":
                label,

            "bracket_ref":
                bracket_ref,

            "score":
                score
        })


    return rows


def world_game_status(
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


    # Little League adds a Recap link
    # after completed World Series games.
    if (
        "FINAL" in text
        or "GAME OVER" in text
        or "RECAP" in text
    ):

        return (
            "FINAL"
        )


    now = datetime.now(
        EASTERN
    )


    if now >= (
        scheduled_dt
        + timedelta(
            hours=3
        )
    ):

        return (
            "FINAL"
        )


    return (
        "LIVE"
    )


# ============================================================
# WORLD SERIES PARSER
# ============================================================

def parse_world_series_page():

    tokens = fetch_tokens(
        WORLD_SERIES_URL
    )


    participants = (
        participant_map_from_tokens(
            tokens
        )
    )


    gc_links = (
        get_gamechanger_links(
            WORLD_SERIES_URL
        )
    )


    games = []


    print(
        "\n"
        "--- WORLD SERIES RESULTS ---"
    )


    for block in (
        split_into_game_blocks(
            tokens
        )
    ):

        game_number = (
            block[
                "game_number"
            ]
        )


        if game_number > 38:

            continue


        (
            date_iso,
            game_time,
            scheduled_dt

        ) = find_date_and_time(

            block[
                "tokens"
            ],

            "America/New_York"
        )


        # ----------------------------------------------------
        # Weather/reschedule information takes priority.
        # ----------------------------------------------------

        if (
            game_number
            in WORLD_SERIES_SCHEDULE_OVERRIDES
        ):

            (
                date_iso,
                game_time

            ) = (
                WORLD_SERIES_SCHEDULE_OVERRIDES[
                    game_number
                ]
            )


            scheduled_dt = (
                eastern_datetime(
                    date_iso,
                    game_time
                )
            )


        if (
            not date_iso
            or not game_time
            or scheduled_dt is None
        ):

            print(
                "WS SKIP:",
                game_number,
                "no usable date/time"
            )

            continue


        rows = (
            extract_world_rows(
                block[
                    "tokens"
                ]
            )
        )


        if len(
            rows
        ) < 2:

            print(
                "WS SKIP:",
                game_number,
                "could not find two team rows"
            )

            continue


        side1 = (
            rows[
                0
            ][
                "side"
            ]
        )


        side2 = (
            rows[
                1
            ][
                "side"
            ]
        )


        score1 = (
            rows[
                0
            ][
                "score"
            ]
        )


        score2 = (
            rows[
                1
            ][
                "score"
            ]
        )


        display1 = (
            display_world_side(
                side1,
                participants
            )
        )


        display2 = (
            display_world_side(
                side2,
                participants
            )
        )


        gc_team1 = (
            gc_world_side_name(
                side1,
                participants
            )
        )


        gc_team2 = (
            gc_world_side_name(
                side2,
                participants
            )
        )


        status = (
            world_game_status(

                scheduled_dt,

                score1,
                score2,

                block[
                    "tokens"
                ]
            )
        )


        if (
            score1 is not None
            and score2 is not None
        ):

            matchup = (

                f"{display1} "
                f"{score1}"

                f" — "

                f"{display2} "
                f"{score2}"
            )

        else:

            matchup = (

                f"{display1}"

                f" vs "

                f"{display2}"
            )


        game = {

            "date":
                date_iso,

            "time":
                game_time,

            "region":
                "World Series",

            "matchup":
                matchup,

            "status":
                status,

            "game_number":
                game_number,

            "scheduled_dt":
                scheduled_dt,

            "team1":
                display1,

            "team2":
                display2,

            "gc_team1":
                gc_team1,

            "gc_team2":
                gc_team2,

            "gc_url":
                gc_links.get(
                    game_number
                ),

            "tv":
                WORLD_SERIES_TV.get(
                    game_number,
                    "TBD"
                )
        }


        games.append(
            game
        )


        print(
            "WS GAME",
            game_number,
            "|",
            date_iso,
            game_time,
            "|",
            matchup,
            "|",
            status
            or "SCHEDULED",
            "| TV:",
            game[
                "tv"
            ],
            "| GC:",
            bool(
                game[
                    "gc_url"
                ]
            )
        )


    return (
        games,
        participants
    )


# ============================================================
# GAMECHANGER JSON
# ============================================================

def find_score_fields(
    obj
):

    if not isinstance(
        obj,
        dict
    ):

        return None


    preferred = [

        "score",
        "runs",
        "points",
        "totalScore",
        "total_score",
        "teamScore",
        "team_score"

    ]


    for key in preferred:

        if key in obj:

            score = valid_score(
                obj[
                    key
                ]
            )


            if score is not None:

                return score


    for (
        key,
        value
    ) in obj.items():

        lower = str(
            key
        ).lower()


        if (
            "score" in lower
            or lower == "runs"
            or lower.endswith(
                "_runs"
            )
        ):

            score = valid_score(
                value
            )


            if score is not None:

                return score


    return None


def extract_team_records(
    obj,
    team1,
    team2,
    found=None
):

    if found is None:

        found = {
            "team1": [],
            "team2": []
        }


    if isinstance(
        obj,
        dict
    ):

        scalar_text = " ".join(

            str(
                value
            )

            for value
            in obj.values()

            if isinstance(
                value,
                (
                    str,
                    int,
                    float
                )
            )
        )


        score = (
            find_score_fields(
                obj
            )
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
                        scalar_text[
                            :250
                        ]
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
                        scalar_text[
                            :250
                        ]
                    )
                )


        for value in (
            obj.values()
        ):

            if isinstance(
                value,
                (
                    dict,
                    list
                )
            ):

                extract_team_records(

                    value,

                    team1,
                    team2,

                    found
                )


    elif isinstance(
        obj,
        list
    ):

        for value in obj:

            extract_team_records(

                value,

                team1,
                team2,

                found
            )


    return found


def choose_unique_score(
    records
):

    scores = []


    for (
        score,
        _
    ) in records:

        if score not in scores:

            scores.append(
                score
            )


    if len(
        scores
    ) == 1:

        return (
            scores[
                0
            ]
        )


    return None


def inspect_gc_json(
    captured_json,
    game
):

    team1 = game.get(
        "gc_team1",
        game[
            "team1"
        ]
    )


    team2 = game.get(
        "gc_team2",
        game[
            "team2"
        ]
    )


    combined = {
        "team1": [],
        "team2": []
    }


    for payload in (
        captured_json
    ):

        found = (
            extract_team_records(

                payload,

                team1,
                team2
            )
        )


        combined[
            "team1"
        ].extend(
            found[
                "team1"
            ]
        )


        combined[
            "team2"
        ].extend(
            found[
                "team2"
            ]
        )


    score1 = (
        choose_unique_score(
            combined[
                "team1"
            ]
        )
    )


    score2 = (
        choose_unique_score(
            combined[
                "team2"
            ]
        )
    )


    if (
        score1 is None
        or score2 is None
    ):

        return None


    print(
        "  GC JSON MATCH:",
        team1,
        score1,
        "—",
        team2,
        score2
    )


    return {

        "score1":
            score1,

        "score2":
            score2,

        "method":
            "JSON"
    }


# ============================================================
# GAMECHANGER DOM FALLBACK
# ============================================================

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
                    .toLowerCase()
                    .replace(/little league/g, "ll");
            }


            function validScore(value) {

                if (!/^\\d{1,2}$/.test(value)) {

                    return false;
                }


                const n =
                    Number(value);


                return (
                    n >= 0
                    &&
                    n <= 30
                );
            }


            const wanted =
                norm(teamName);


            const other =
                norm(otherTeam);


            const elements =
                Array.from(
                    document.querySelectorAll(
                        "body *"
                    )
                );


            const matches =
                elements.filter(
                    el => {

                        const txt =
                            norm(
                                el.innerText
                            );


                        if (!txt) {

                            return false;
                        }


                        return (
                            txt.includes(
                                wanted
                            )
                        );
                    }
                );


            for (
                const el
                of matches
            ) {

                let node =
                    el;


                for (
                    let depth = 0;
                    depth < 9 && node;
                    depth++
                ) {

                    const text =
                        (
                            node.innerText
                            || ""
                        )
                        .replace(
                            /\\s+/g,
                            " "
                        )
                        .trim();


                    const normalized =
                        norm(
                            text
                        );


                    if (
                        normalized.includes(
                            wanted
                        )
                        &&
                        !normalized.includes(
                            other
                        )
                    ) {

                        const nums =
                            text.match(
                                /(?:^|\\s)(\\d{1,2})(?=\\s|$)/g
                            );


                        if (nums) {

                            const cleanNums =
                                nums
                                .map(
                                    x => x.trim()
                                )
                                .filter(
                                    validScore
                                );


                            const unique =
                                [
                                    ...new Set(
                                        cleanNums
                                    )
                                ];


                            if (
                                unique.length
                                === 1
                            ) {

                                return {

                                    score:
                                        unique[
                                            0
                                        ],

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
            "teamName":
                team_name,

            "otherTeam":
                other_team
        }
    )


# ============================================================
# GAMECHANGER TEXT FALLBACK
# ============================================================

def score_from_visible_lines(
    body_text,
    team_name
):

    lines = [

        clean(
            line
        )

        for line
        in body_text.splitlines()

        if clean(
            line
        )
    ]


    wanted = (
        normalize_team(
            team_name
        )
    )


    candidates = []


    for (
        index,
        line
    ) in enumerate(
        lines
    ):

        if wanted not in normalize_team(
            line
        ):

            continue


        start = max(
            0,
            index - 2
        )


        end = min(
            len(
                lines
            ),
            index + 4
        )


        nearby = lines[
            start:
            end
        ]


        for (
            offset,
            nearby_line
        ) in enumerate(
            nearby
        ):

            if (
                normalize_team(
                    nearby_line
                )
                == wanted
            ):

                continue


            if not re.fullmatch(
                r"\d{1,2}",
                nearby_line
            ):

                continue


            score = valid_score(
                nearby_line
            )


            if score is None:

                continue


            distance = abs(

                (
                    start
                    + offset
                )

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
        key=lambda item:
            item[
                0
            ]
    )


    best_distance = (
        candidates[
            0
        ][0]
    )


    best = [

        item

        for item
        in candidates

        if item[
            0
        ] == best_distance
    ]


    unique_scores = []


    for (
        _,
        score,
        _
    ) in best:

        if score not in unique_scores:

            unique_scores.append(
                score
            )


    if len(
        unique_scores
    ) != 1:

        return None


    return {

        "score":
            unique_scores[
                0
            ],

        "context":
            " | ".join(
                best[
                    0
                ][2]
            )[:300]
    }


# ============================================================
# GAMECHANGER INSPECTION
# ============================================================

def inspect_gamechanger(
    page,
    game
):

    url = game.get(
        "gc_url"
    )


    if not url:

        return None


    team1 = game.get(
        "gc_team1",
        game[
            "team1"
        ]
    )


    team2 = game.get(
        "gc_team2",
        game[
            "team2"
        ]
    )


    # Unresolved bracket matchup.
    if (
        re.fullmatch(
            r"[WL]\d+|TBA",
            team1,
            re.I
        )
        or
        re.fullmatch(
            r"[WL]\d+|TBA",
            team2,
            re.I
        )
    ):

        return None


    print(
        "GC CHECK:",
        game[
            "region"
        ],
        "Game",
        game[
            "game_number"
        ],
        team1,
        "vs",
        team2
    )


    print(
        "  URL:",
        url
    )


    captured_json = []


    def capture_response(
        response
    ):

        try:

            content_type = (
                response.headers.get(
                    "content-type",
                    ""
                ).lower()
            )


            if (
                "json"
                not in content_type
            ):

                return


            payload = (
                response.json()
            )


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


        # ----------------------------------------------------
        # METHOD 1 - JSON
        # ----------------------------------------------------

        json_result = (
            inspect_gc_json(
                captured_json,
                game
            )
        )


        if json_result:

            score1 = (
                json_result[
                    "score1"
                ]
            )

            score2 = (
                json_result[
                    "score2"
                ]
            )

            method = (
                "JSON"
            )


        else:

            # ------------------------------------------------
            # METHOD 2 - DOM
            # ------------------------------------------------

            row1 = (
                find_score_in_team_row(
                    page,
                    team1,
                    team2
                )
            )


            row2 = (
                find_score_in_team_row(
                    page,
                    team2,
                    team1
                )
            )


            if (
                row1
                and row2
            ):

                score1 = (
                    row1[
                        "score"
                    ]
                )

                score2 = (
                    row2[
                        "score"
                    ]
                )

                method = (
                    "DOM"
                )


            else:

                # --------------------------------------------
                # METHOD 3 - visible text
                # --------------------------------------------

                text1 = (
                    score_from_visible_lines(
                        body_text,
                        team1
                    )
                )


                text2 = (
                    score_from_visible_lines(
                        body_text,
                        team2
                    )
                )


                if (
                    not text1
                    or not text2
                ):

                    print(
                        "  GC SKIP: "
                        "no reliable score pair"
                    )

                    return None


                score1 = (
                    text1[
                        "score"
                    ]
                )

                score2 = (
                    text2[
                        "score"
                    ]
                )

                method = (
                    "TEXT"
                )


        score1 = (
            valid_score(
                score1
            )
        )


        score2 = (
            valid_score(
                score2
            )
        )


        if (
            score1 is None
            or score2 is None
        ):

            return None


        upper = (
            body_text.upper()
        )


        if (
            "FINAL" in upper
            or "GAME OVER" in upper
        ):

            status = (
                "FINAL"
            )

        else:

            status = (
                "LIVE"
            )


        print(
            "  GC RESULT:",
            team1,
            score1,
            "—",
            team2,
            score2,
            status,
            f"({method})"
        )


        return {

            "score1":
                score1,

            "score2":
                score2,

            "status":
                status,

            "method":
                method
        }


    except Exception as exc:

        print(
            "  GC ERROR:",
            type(
                exc
            ).__name__,
            exc
        )


        return None


    finally:

        page.remove_listener(
            "response",
            capture_response
        )


# ============================================================
# SHOULD GAMECHANGER BE CHECKED?
# ============================================================

def should_check_gc(
    game
):

    if not game.get(
        "gc_url"
    ):

        return False


    if (
        game.get(
            "status"
        )
        == "FINAL"
    ):

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


# ============================================================
# APPLY GAMECHANGER
#
# This now works for BOTH regional and World Series games.
# ============================================================

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
        "\n"
        "--- GAMECHANGER LIVE CHECK ---"
    )


    if not candidates:

        print(
            "No GameChanger live candidates."
        )

        return scraped


    with sync_playwright() as p:

        browser = (
            p.chromium.launch(
                headless=True
            )
        )


        context = (
            browser.new_context(

                viewport={

                    "width":
                        1280,

                    "height":
                        1200
                }
            )
        )


        page = (
            context.new_page()
        )


        for game in candidates:

            result = (
                inspect_gamechanger(
                    page,
                    game
                )
            )


            if not result:

                continue


            game[
                "matchup"
            ] = (

                f"{game['team1']} "
                f"{result['score1']}"

                f" — "

                f"{game['team2']} "
                f"{result['score2']}"
            )


            game[
                "status"
            ] = (
                result[
                    "status"
                ]
            )


        browser.close()


    return scraped


# ============================================================
# SCRAPE REGIONAL GAMES
# ============================================================

scraped = []

errors = []


for (
    region,
    url
) in URLS.items():

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


# ============================================================
# SCRAPE WORLD SERIES
# ============================================================

participants = {}

world_games = []


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


# ============================================================
# GAMECHANGER PASS
# ============================================================

scraped = (
    apply_gamechanger_live(
        scraped
    )
)


# ============================================================
# BUILD OUTPUT
#
# CRITICAL CHANGE:
#
# We DO NOT carry old World Series rows forward from
# base_schedule.json anymore.
#
# World Series rows come from the CURRENT official schedule.
# ============================================================

regional_lookup = {

    (
        game[
            "date"
        ],
        game[
            "time"
        ],
        game[
            "region"
        ]
    ):
        game

    for game in scraped

    if (
        game[
            "region"
        ]
        != "World Series"
    )
}


output = []

matched = 0


# ------------------------------------------------------------
# Existing REGIONAL schedule
# ------------------------------------------------------------

for base_game in BASE:

    # Do NOT keep stale World Series rows.
    if (
        base_game.get(
            "region"
        )
        == "World Series"
    ):

        continue


    row = dict(
        base_game
    )


    official = (
        regional_lookup.get(
            (
                row[
                    "date"
                ],
                row[
                    "time"
                ],
                row[
                    "region"
                ]
            )
        )
    )


    if official:

        row[
            "matchup"
        ] = (
            official[
                "matchup"
            ]
        )


        row[
            "status"
        ] = (
            official[
                "status"
            ]
        )


        matched += 1


    output.append(
        row
    )


# ------------------------------------------------------------
# CURRENT WORLD SERIES schedule
# ------------------------------------------------------------

for game in scraped:

    if (
        game[
            "region"
        ]
        != "World Series"
    ):

        continue


    output.append({

        "date":
            game[
                "date"
            ],

        "time":
            game[
                "time"
            ],

        "region":
            "World Series",

        "matchup":
            game[
                "matchup"
            ],

        "tv":
            game.get(
                "tv",
                "TBD"
            ),

        "status":
            game[
                "status"
            ],

        "game_number":
            game[
                "game_number"
            ]
    })


    matched += 1


# ============================================================
# SORT
# ============================================================

def sort_time(
    game
):

    try:

        return datetime.strptime(
            game[
                "time"
            ],
            "%I:%M %p"
        ).time()


    except ValueError:

        return datetime.strptime(
            "11:59 PM",
            "%I:%M %p"
        ).time()


output.sort(

    key=lambda game: (

        game[
            "date"
        ],

        sort_time(
            game
        )
    )
)


# ============================================================
# WRITE LATEST.JSON
# ============================================================

payload = {

    "updated":
        datetime.now(
            UTC
        ).strftime(
            "%Y-%m-%d %H:%M UTC"
        ),

    "source":
        (
            "Official LittleLeague.org schedules "
            "+ official World Series weather adjustment "
            "+ GameChanger live scoring"
        ),

    "scraped_games":
        len(
            scraped
        ),

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


# ============================================================
# DEBUG
# ============================================================

print(
    "\nScraped games:",
    len(
        scraped
    )
)


print(
    "Matched games:",
    matched
)


print(
    "\n"
    "--- WORLD SERIES SCHEDULE WRITTEN ---"
)


for game in scraped:

    if (
        game[
            "region"
        ]
        == "World Series"
    ):

        print(

            "Game",
            game[
                "game_number"
            ],

            "|",
            game[
                "date"
            ],

            game[
                "time"
            ],

            "|",
            game[
                "matchup"
            ],

            "|",
            game[
                "status"
            ]
            or "SCHEDULED",

            "|",
            game.get(
                "tv",
                "TBD"
            )
        )


print(
    "\n"
    "--- LIVE GAMES WRITTEN ---"
)


live_games = [

    game

    for game in scraped

    if (
        game.get(
            "status"
        )
        == "LIVE"
    )
]


if not live_games:

    print(
        "No live games."
    )


for game in live_games:

    print(

        game[
            "region"
        ],

        game[
            "date"
        ],

        game[
            "time"
        ],

        game[
            "matchup"
        ],

        "LIVE"
    )


print(
    "\n"
    "--- FINAL GAMES WRITTEN ---"
)


for game in scraped:

    if (
        game.get(
            "status"
        )
        == "FINAL"
    ):

        print(

            game[
                "region"
            ],

            game[
                "date"
            ],

            game[
                "time"
            ],

            game[
                "matchup"
            ],

            "FINAL"
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
