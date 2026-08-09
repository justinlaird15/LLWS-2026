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


REGION_URLS = {
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
        "(compatible; personal LLWS schedule dashboard/2.0)"
}


TZ_MAP = {
    "ET": "America/New_York",
    "CT": "America/Chicago",
    "MT": "America/Denver",
    "PT": "America/Los_Angeles",

    "Eastern": "America/New_York",
    "Central": "America/Chicago",
    "Mountain": "America/Denver",
    "Pacific": "America/Los_Angeles",
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


PARTICIPANT_REGION_NAMES = [

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

    (
        "2026-08-19",
        "1:00 PM",
        "Latin America Region vs Caribbean Region",
        "ESPN"
    ),

    (
        "2026-08-19",
        "3:00 PM",
        "Southeast Region vs Northwest Region",
        "ESPN"
    ),

    (
        "2026-08-19",
        "5:00 PM",
        "Canada Region vs Asia-Pacific Region",
        "ESPN"
    ),

    (
        "2026-08-19",
        "7:00 PM",
        "Metro Region vs New England Region",
        "ESPN"
    ),


    (
        "2026-08-20",
        "12:00 PM",
        "Australia Region vs Mexico Region",
        "ESPN"
    ),

    (
        "2026-08-20",
        "2:00 PM",
        "Great Lakes Region vs Mountain Region",
        "ESPN"
    ),

    (
        "2026-08-20",
        "4:00 PM",
        "Curaçao Region vs Japan Region",
        "ESPN"
    ),

    (
        "2026-08-20",
        "6:00 PM",
        "West Region vs Midwest Region",
        "ESPN2"
    ),


    (
        "2026-08-21",
        "1:00 PM",
        "Panama Region vs W1",
        "ESPN"
    ),

    (
        "2026-08-21",
        "3:00 PM",
        "Southwest Region vs W2",
        "ESPN"
    ),

    (
        "2026-08-21",
        "5:00 PM",
        "Europe-Africa Region vs W3",
        "ESPN"
    ),

    (
        "2026-08-21",
        "7:00 PM",
        "Mid-Atlantic Region vs W4",
        "ESPN"
    ),


    (
        "2026-08-22",
        "1:00 PM",
        "L3 vs L5",
        "ESPN"
    ),

    (
        "2026-08-22",
        "3:00 PM",
        "L4 vs L6",
        "ESPN"
    ),

    (
        "2026-08-22",
        "5:00 PM",
        "L1 vs L7",
        "ESPN"
    ),

    (
        "2026-08-22",
        "7:00 PM",
        "L2 vs L8",
        "ESPN"
    ),


    (
        "2026-08-23",
        "9:00 AM",
        "W6 vs W10",
        "ESPN"
    ),

    (
        "2026-08-23",
        "11:00 AM",
        "W5 vs W9",
        "ESPN"
    ),

    (
        "2026-08-23",
        "1:00 PM",
        "W8 vs W12",
        "ABC"
    ),

    (
        "2026-08-23",
        "2:00 PM",
        "W7 vs W11",
        "ESPN"
    ),


    (
        "2026-08-24",
        "1:00 PM",
        "L9 vs W13",
        "ESPN"
    ),

    (
        "2026-08-24",
        "3:00 PM",
        "L10 vs W14",
        "ESPN"
    ),

    (
        "2026-08-24",
        "5:00 PM",
        "L11 vs W15",
        "ESPN"
    ),

    (
        "2026-08-24",
        "7:00 PM",
        "L12 vs W16",
        "ESPN"
    ),


    (
        "2026-08-25",
        "1:00 PM",
        "L18 vs W23",
        "ESPN"
    ),

    (
        "2026-08-25",
        "3:00 PM",
        "L17 vs W24",
        "ESPN"
    ),

    (
        "2026-08-25",
        "5:00 PM",
        "L20 vs W21",
        "ESPN"
    ),

    (
        "2026-08-25",
        "7:00 PM",
        "L19 vs W22",
        "ESPN"
    ),


    (
        "2026-08-26",
        "1:00 PM",
        "W18 vs W20",
        "ESPN"
    ),

    (
        "2026-08-26",
        "3:00 PM",
        "W17 vs W19",
        "ESPN"
    ),

    (
        "2026-08-26",
        "5:00 PM",
        "W25 vs W27",
        "ESPN"
    ),

    (
        "2026-08-26",
        "7:00 PM",
        "W26 vs W28",
        "ESPN"
    ),


    (
        "2026-08-27",
        "3:00 PM",
        "L29 vs W31",
        "ESPN"
    ),

    (
        "2026-08-27",
        "7:00 PM",
        "L30 vs W32",
        "ESPN"
    ),


    (
        "2026-08-29",
        "12:30 PM",
        "W29 vs W33 — International Championship",
        "ABC"
    ),

    (
        "2026-08-29",
        "3:30 PM",
        "W30 vs W34 — United States Championship",
        "ABC"
    ),


    (
        "2026-08-30",
        "10:00 AM",
        "L35 vs L36 — Third-Place Game",
        "ESPN"
    ),

    (
        "2026-08-30",
        "3:00 PM",
        "W35 vs W36 — LLWS World Championship",
        "ABC"
    ),
]


def clean(value):

    return re.sub(
        r"\s+",
        " ",
        value or ""
    ).strip()


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


def get_tokens(soup):

    return [
        clean(x)
        for x in soup.stripped_strings
        if clean(x)
    ]


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

                blocks.append(
                    current
                )

            current = {

                "game_number":
                    int(
                        match.group(1)
                    ),

                "tokens":
                    [token]
            }

            continue

        if current:

            current["tokens"].append(
                token
            )

    if current:

        blocks.append(
            current
        )

    return blocks


def parse_header(
    header,
    default_timezone
):

    date_match = re.search(
        r"-\s*August\s+(\d{1,2})\b",
        header,
        re.I
    )

    time_match = re.search(
        r"(\d{1,2}:\d{2})\s*"
        r"([ap])\.?m\.?",
        header,
        re.I
    )

    if (
        not date_match
        or not time_match
    ):

        return None, None


    day = int(
        date_match.group(1)
    )

    date_iso = (
        f"2026-08-{day:02d}"
    )


    time_text = (
        time_match.group(1)
        + " "
        + time_match.group(2).upper()
        + "M"
    )


    explicit_tz = None

    tz_match = re.search(
        r"\b(ET|CT|MT|PT)\b",
        header,
        re.I
    )

    if tz_match:

        explicit_tz = (
            tz_match.group(1).upper()
        )


    if explicit_tz:

        source_timezone = (
            TZ_MAP.get(
                explicit_tz,
                default_timezone
            )
        )

    else:

        source_timezone = (
            default_timezone
        )


    dt = datetime.strptime(
        f"{date_iso} {time_text}",
        "%Y-%m-%d %I:%M %p"
    )

    dt = dt.replace(
        tzinfo=ZoneInfo(
            source_timezone
        )
    )


    eastern = dt.astimezone(
        ZoneInfo(
            "America/New_York"
        )
    )


    return (
        date_iso,
        eastern.strftime(
            "%-I:%M %p"
        )
    )


def extract_region_teams(
    block_tokens
):

    teams = []

    for token in block_tokens:

        if token in TEAM_ALIASES:

            normalized = (
                TEAM_ALIASES[token]
            )

            if normalized not in teams:

                teams.append(
                    normalized
                )

    return teams[:2]


def raw_region_team_tokens(
    block_tokens
):

    result = []

    for token in block_tokens:

        if token in TEAM_ALIASES:

            result.append(
                token
            )

    return result[:2]


def raw_world_team_tokens(
    block_tokens
):

    result = []

    for token in block_tokens:

        if token in WORLD_REGION_LABELS:

            result.append(
                token
            )

    return result[:2]


def extract_scores(
    block_tokens,
    raw_team_tokens
):

    if len(raw_team_tokens) < 2:

        return None


    first = raw_team_tokens[0]

    second = raw_team_tokens[1]


    try:

        first_index = (
            block_tokens.index(first)
        )

        second_index = (
            block_tokens.index(
                second,
                first_index + 1
            )
        )

    except ValueError:

        return None


    score1 = None

    score2 = None


    for token in block_tokens[
        first_index + 1:
        second_index
    ]:

        if re.fullmatch(
            r"\d{1,2}",
            token
        ):

            score1 = token


    for token in block_tokens[
        second_index + 1:
        second_index + 10
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


def parse_region_page(
    region,
    url
):

    soup = fetch_soup(
        url
    )

    tokens = get_tokens(
        soup
    )


    timezone_name = (
        page_timezone(
            tokens
        )
    )


    blocks = (
        split_into_game_blocks(
            tokens
        )
    )


    games = []


    for block in blocks:

        header = (
            block["tokens"][0]
        )


        date_iso, eastern_time = (
            parse_header(
                header,
                timezone_name
            )
        )


        if (
            not date_iso
            or not eastern_time
        ):

            continue


        teams = (
            extract_region_teams(
                block["tokens"]
            )
        )


        if len(teams) < 2:

            continue


        raw_teams = (
            raw_region_team_tokens(
                block["tokens"]
            )
        )


        scores = (
            extract_scores(
                block["tokens"],
                raw_teams
            )
        )


        if scores:

            matchup = (
                f"{teams[0]} "
                f"{scores[0]}"
                f" — "
                f"{teams[1]} "
                f"{scores[1]}"
            )

            status = "FINAL"

        else:

            matchup = (
                f"{teams[0]}"
                f" vs "
                f"{teams[1]}"
            )

            status = ""


        games.append({

            "date":
                date_iso,

            "time":
                eastern_time,

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


def parse_participant_map(
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
        PARTICIPANT_REGION_NAMES
    ):

        try:

            index = (
                prefix.index(region)
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


        if team in {

            "TBA",
            "Team",
            "City",
            "City/State",
            "City/Country",
            "Record"

        }:

            continue


        mapping[region] = team


    return mapping


def extract_world_sides(
    block_tokens
):

    sides = []


    for token in block_tokens:

        if token in WORLD_REGION_LABELS:

            if (
                token
                == "Europe & Africa Region"
            ):

                normalized = (
                    "Europe-Africa Region"
                )

            else:

                normalized = token


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
    participant_map
):

    if not side.endswith(
        " Region"
    ):

        return side


    region_name = side[
        :-7
    ]


    if (
        region_name
        == "Europe-Africa"
    ):

        map_key = (
            "Europe & Africa"
        )

    else:

        map_key = (
            region_name
        )


    team = (
        participant_map.get(
            map_key
        )
    )


    if team:

        return (
            f"{team} "
            f"({region_name})"
        )


    return side


def parse_world_series_page():

    soup = fetch_soup(
        WORLD_SERIES_URL
    )

    tokens = get_tokens(
        soup
    )


    participant_map = (
        parse_participant_map(
            tokens
        )
    )


    blocks = (
        split_into_game_blocks(
            tokens
        )
    )


    games = []


    for block in blocks:

        header = (
            block["tokens"][0]
        )


        date_iso, eastern_time = (
            parse_header(
                header,
                "America/New_York"
            )
        )


        if (
            not date_iso
            or not eastern_time
        ):

            continue


        sides = (
            extract_world_sides(
                block["tokens"]
            )
        )


        if len(sides) < 2:

            continue


        display_sides = [

            display_world_side(
                side,
                participant_map
            )

            for side in sides
        ]


        raw_teams = (
            raw_world_team_tokens(
                block["tokens"]
            )
        )


        scores = (
            extract_scores(
                block["tokens"],
                raw_teams
            )
        )


        if (
            scores
            and len(raw_teams) >= 2
        ):

            matchup = (
                f"{display_sides[0]} "
                f"{scores[0]}"
                f" — "
                f"{display_sides[1]} "
                f"{scores[1]}"
            )

            status = "FINAL"

        else:

            matchup = (
                f"{display_sides[0]}"
                f" vs "
                f"{display_sides[1]}"
            )

            status = ""


        games.append({

            "date":
                date_iso,

            "time":
                eastern_time,

            "region":
                "World Series",

            "matchup":
                matchup,

            "status":
                status,

            "game_number":
                block["game_number"]
        })


    return (
        games,
        participant_map
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

            "date":
                date_iso,

            "time":
                game_time,

            "region":
                "World Series",

            "matchup":
                matchup,

            "tv":
                tv,

            "status":
                ""
        })


add_world_series_base_games()


scraped = []

errors = []


for region, url in (
    REGION_URLS.items()
):

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


participant_map = {}


try:

    (
        world_games,
        participant_map
    ) = parse_world_series_page()


    scraped.extend(
        world_games
    )


    if not world_games:

        errors.append(
            "World Series: "
            "no games parsed"
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


    key = (
        row["date"],
        row["time"],
        row["region"]
    )


    official = (
        lookup.get(key)
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
            ZoneInfo("UTC")
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

        participant_map,


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
    "World Series participants:",
    participant_map
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


print(
    "\n--- WORLD SERIES OPENING GAMES ---"
)


for game in scraped:

    if (
        game["region"]
        == "World Series"
        and
        game["date"]
        <= "2026-08-21"
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
