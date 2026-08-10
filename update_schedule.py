import json
import re
import time
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent

EASTERN = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

BASE = json.loads(
    (ROOT / "base_schedule.json").read_text(encoding="utf-8")
)


# Only check GameChanger around the time a game could
# reasonably be underway.
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
        "(compatible; personal LLWS schedule dashboard/7.0)"
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

    """
    Find GameChanger links while tracking the most recent
    'Game N' heading on the Little League tournament page.
    """

    soup = fetch_soup(url)

    links = {}

    current_game = None

    for element in soup.descendants:

        if isinstance(element, str):

            text = clean(element)

            match = re.match(
                r"^Game\s+(\d+)\b",
                text,
                re.I
            )

            if match:

                current_game = int(
                    match.group(1)
                )

        elif getattr(
            element,
            "name",
            None
        ) == "a":

            href = element.get(
                "href",
                ""
            )

            if (
                current_game is not None
                and "web.gc.com/" in href
            ):

                links[current_game] = href

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
                "game_number":
                    int(match.group(1)),

                "tokens":
                    [token]
            }

            continue

        if current:
            current["tokens"].append(
                token
            )

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

    tokens = fetch_tokens(
        url
    )

    gc_links = get_gamechanger_links(
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
                block["game_number"],

            "scheduled_dt":
                scheduled_dt,

            "team1":
                teams[0],

            "team2":
                teams[1],

            "gc_url":
                gc_links.get(
                    block["game_number"]
                )
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

    if (
        label
        == "Europe & Africa Region"
    ):

        return (
            "Europe-Africa Region"
        )

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

        if (
            block["game_number"]
            > 38
        ):

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
            "date":
                date_iso,

            "time":
                game_time,

            "region":
                "World Series",

            "matchup":
                (
                    f"{display_sides[0]}"
                    f" vs "
                    f"{display_sides[1]}"
                ),

            "status":
                "",

            "game_number":
                block["game_number"],

            "scheduled_dt":
                scheduled_dt,

            "team1":
                display_sides[0],

            "team2":
                display_sides[1],

            "gc_url":
                None
        })


    return (
        games,
        participants
    )


def normalize_for_match(text):

    text = clean(
        text
    ).lower()

    text = (
        text
        .replace(
            "southern california",
            "southern calif"
        )
        .replace(
            "northern california",
            "northern calif"
        )
        .replace(
            "washington, d.c.",
            "washington, dc"
        )
    )

    return text


def find_score_in_team_row(
    page,
    team_name,
    other_team
):

    """
    Find a visible element containing the team name.

    Walk upward through its ancestors until we find the
    smallest row/card that contains that team and a numeric
    score, but NOT the opposing team.

    This prevents one team's score from being accidentally
    assigned to both teams.
    """

    result = page.evaluate(
        """
        ({teamName, otherTeam}) => {

            function norm(value) {
                return (value || "")
                    .replace(/\\s+/g, " ")
                    .trim()
                    .toLowerCase();
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

                    if (!txt) return false;

                    return (
                        txt === wanted ||
                        txt.includes(wanted)
                    );
                });


            for (const el of matches) {

                let node = el;

                for (
                    let depth = 0;
                    depth < 7 && node;
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
                                .filter(x => /^\\d{1,2}$/.test(x));

                            if (
                                cleanNums.length === 1
                            ) {

                                return {
                                    score:
                                        cleanNums[0],

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

    return result


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


    try:

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=45000
        )


        page.wait_for_timeout(
            3500
        )


        body_text = (
            page.locator(
                "body"
            ).inner_text()
        )


        if not body_text:

            print(
                "GC SKIP: empty page"
            )

            return None


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
            not row1
            or not row2
        ):

            print(
                "GC SKIP: could not "
                "unambiguously pair both teams "
                "with scores"
            )

            return None


        score1 = row1[
            "score"
        ]

        score2 = row2[
            "score"
        ]


        if (
            not re.fullmatch(
                r"\d{1,2}",
                score1
            )
            or not re.fullmatch(
                r"\d{1,2}",
                score2
            )
        ):

            print(
                "GC SKIP: invalid score"
            )

            return None


        upper = (
            body_text.upper()
        )


        if "FINAL" in upper:

            status = "FINAL"

        else:

            status = "LIVE"


        print(
            "GC RESULT:",
            game["team1"],
            score1,
            "—",
            game["team2"],
            score2,
            status
        )


        print(
            "  ROW 1:",
            row1["rowText"][:200]
        )


        print(
            "  ROW 2:",
            row2["rowText"][:200]
        )


        return {
            "score1":
                score1,

            "score2":
                score2,

            "status":
                status
        }


    except Exception as exc:

        print(
            "GC ERROR:",
            type(exc).__name__,
            exc
        )

        return None


def should_check_gc(game):

    if not game.get(
        "gc_url"
    ):

        return False


    # No reason to ask GC for something Little League
    # already says is final.
    if game.get(
        "status"
    ) == "FINAL":

        return False


    now = datetime.now(
        EASTERN
    )


    scheduled = game.get(
        "scheduled_dt"
    )


    if scheduled is None:

        return False


    start = (
        scheduled
        - timedelta(
            minutes=GC_BEFORE_MINUTES
        )
    )


    end = (
        scheduled
        + timedelta(
            hours=GC_AFTER_HOURS
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


        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 1200
            }
        )


        for game in candidates:

            result = inspect_gamechanger(
                page,
                game
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
            ] = result[
                "status"
            ]


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


# --------------------------------------------------
# GAMECHANGER LIVE PASS
# --------------------------------------------------

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
        "Official LittleLeague.org schedules "
        "+ GameChanger live scoring",

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
    "\n--- FINALS ---"
)


for game in scraped:

    if game.get(
        "status"
    ) == "FINAL":

        print(
            game["region"],
            game["date"],
            game["time"],
            game["matchup"],
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
