import json
import re
import time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, Tag, NavigableString


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

    "World Series":
        "https://www.littleleague.org/world-series/2026/llbws/tournaments/world-series/",
}


HEADERS = {
    "User-Agent":
        "Mozilla/5.0 (compatible; personal LLWS schedule dashboard/1.1)"
}


MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
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


DATE_RE = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
    r"([A-Z][a-z]+) (\d{1,2}), 2026$"
)


GAME_RE = re.compile(
    r"^Game\s+(\d+)"
    r"(?:\s*-\s*Championship)?"
    r"\s*\|\s*"
    r"(\d{1,2}:\d{2})\s*"
    r"([ap]\.?m\.?)"
    r"(?:\s*(ET|CT|MT|PT))?"
    r"\s*-\s*"
    r"([A-Z][a-z]+)\s+"
    r"(\d{1,2})",
    re.I,
)


def clean(text):
    return re.sub(
        r"\s+",
        " ",
        text or ""
    ).strip()


def page_timezone(soup):

    text = soup.get_text(
        " ",
        strip=True
    )

    match = re.search(
        r"All game times are "
        r"(Eastern|Central|Mountain|Pacific) time",
        text,
        re.I,
    )

    if match:

        name = match.group(1).title()

        return TZ_MAP[name]

    return "America/New_York"


def to_eastern(
    date_iso,
    hhmm,
    ampm,
    page_tz,
    explicit_abbr=None,
):

    ampm = ampm.replace(
        ".",
        ""
    ).upper()

    dt = datetime.strptime(
        f"{date_iso} {hhmm} {ampm}",
        "%Y-%m-%d %I:%M %p",
    )

    source_tz = page_tz

    if explicit_abbr:

        source_tz = TZ_MAP.get(
            explicit_abbr.upper(),
            page_tz,
        )

    localized = dt.replace(
        tzinfo=ZoneInfo(source_tz)
    )

    eastern = localized.astimezone(
        ZoneInfo("America/New_York")
    )

    return eastern.strftime(
        "%-I:%M %p"
    )


def extract_game_from_elements(
    game_info,
    elements,
):

    teams = []

    numeric_scores = []

    for element in elements:

        if (
            isinstance(element, Tag)
            and element.name == "h4"
        ):

            name = clean(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if (
                name
                and name not in teams
            ):

                teams.append(name)

            continue

        if isinstance(
            element,
            NavigableString
        ):

            text = clean(
                str(element)
            )

            if re.fullmatch(
                r"\d{1,2}",
                text
            ):

                numeric_scores.append(
                    text
                )

    teams = teams[:2]

    if len(teams) < 2:

        return None

    if len(numeric_scores) >= 2:

        matchup = (
            f"{teams[0]} "
            f"{numeric_scores[0]}"
            f" — "
            f"{teams[1]} "
            f"{numeric_scores[1]}"
        )

        status = "FINAL"

    else:

        matchup = (
            f"{teams[0]}"
            f" vs "
            f"{teams[1]}"
        )

        status = ""

    return {
        "date":
            game_info["date"],

        "time":
            game_info["time"],

        "region":
            game_info["region"],

        "matchup":
            matchup,

        "status":
            status,
    }


def parse_page(
    region,
    url,
):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    source_tz = page_timezone(
        soup
    )

    schedule_heading = soup.find(
        lambda tag:
            isinstance(tag, Tag)
            and tag.name in {"h2", "h3"}
            and "Tournament Schedule"
            in clean(
                tag.get_text(
                    " ",
                    strip=True
                )
            )
    )

    if not schedule_heading:

        raise RuntimeError(
            "Tournament Schedule heading not found"
        )

    games = []

    current_date = None

    active = None

    active_elements = []


    def finish_active():

        nonlocal active
        nonlocal active_elements

        if active:

            parsed = (
                extract_game_from_elements(
                    active,
                    active_elements,
                )
            )

            if parsed:

                games.append(
                    parsed
                )

        active = None

        active_elements = []


    for element in (
        schedule_heading.next_elements
    ):

        if (
            isinstance(element, Tag)
            and element.name == "h2"
        ):

            text = clean(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            if (
                text
                == "Secondary Navigation"
            ):

                break


        if (
            isinstance(element, Tag)
            and element.name == "h3"
        ):

            text = clean(
                element.get_text(
                    " ",
                    strip=True
                )
            )

            date_match = (
                DATE_RE.match(text)
            )

            if date_match:

                finish_active()

                month = MONTHS[
                    date_match.group(2)
                ]

                current_date = (
                    f"2026-"
                    f"{month:02d}-"
                    f"{int(date_match.group(3)):02d}"
                )

                continue


        if isinstance(
            element,
            NavigableString
        ):

            text = clean(
                str(element)
            )

            game_match = (
                GAME_RE.match(text)
            )

            if (
                game_match
                and current_date
            ):

                finish_active()

                hhmm = (
                    game_match.group(2)
                )

                ampm = (
                    game_match.group(3)
                )

                explicit_tz = (
                    game_match.group(4)
                )

                active = {
                    "date":
                        current_date,

                    "time":
                        to_eastern(
                            current_date,
                            hhmm,
                            ampm,
                            source_tz,
                            explicit_tz,
                        ),

                    "region":
                        region,
                }

                continue


        if active:

            active_elements.append(
                element
            )


    finish_active()

    return games


scraped = []

errors = []


for region, url in URLS.items():

    try:

        parsed = parse_page(
            region,
            url,
        )

        if parsed:

            scraped.extend(
                parsed
            )

        else:

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


lookup = {
    (
        game["date"],
        game["time"],
        game["region"],
    ): game

    for game in scraped
}


out = []

updated_count = 0


for base_game in BASE:

    row = dict(
        base_game
    )

    official = lookup.get(
        (
            row["date"],
            row["time"],
            row["region"],
        )
    )

    if official:

        row["matchup"] = (
            official["matchup"]
        )

        row["status"] = (
            official["status"]
        )

        updated_count += 1

    out.append(
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
        "tournament schedule pages",

    "scraped_games":
        len(scraped),

    "matched_games":
        updated_count,

    "errors":
        errors,

    "games":
        out,
}


(
    ROOT / "latest.json"
).write_text(

    json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    ),

    encoding="utf-8",
)


print(
    f"Scraped "
    f"{len(scraped)} "
    f"official games"
)

print(
    f"Matched "
    f"{updated_count} "
    f"games in base schedule"
)


if errors:

    print(
        "Warnings:"
    )

    for error in errors:

        print(
            " -",
            error
        )
