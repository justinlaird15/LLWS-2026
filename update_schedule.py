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
    "Great Lakes": "https://www.littleleague.org/world-series/2026/llbws/tournaments/great-lakes-region/",
    "Metro": "https://www.littleleague.org/world-series/2026/llbws/tournaments/metro-region/",
    "Mid-Atlantic": "https://www.littleleague.org/world-series/2026/llbws/tournaments/mid-atlantic-region/",
    "Midwest": "https://www.littleleague.org/world-series/2026/llbws/tournaments/midwest-region/",
    "Mountain": "https://www.littleleague.org/world-series/2026/llbws/tournaments/mountain-region/",
    "New England": "https://www.littleleague.org/world-series/2026/llbws/tournaments/new-england-region/",
    "Northwest": "https://www.littleleague.org/world-series/2026/llbws/tournaments/northwest-region/",
    "Southeast": "https://www.littleleague.org/world-series/2026/llbws/tournaments/southeast-region/",
    "Southwest": "https://www.littleleague.org/world-series/2026/llbws/tournaments/southwest-region/",
    "West": "https://www.littleleague.org/world-series/2026/llbws/tournaments/west-region/",
}


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


TZ_MAP = {
    "Eastern": "America/New_York",
    "Central": "America/Chicago",
    "Mountain": "America/Denver",
    "Pacific": "America/Los_Angeles",
}


def convert_to_eastern(date_iso, time_text, timezone_name):

    dt = datetime.strptime(
        f"{date_iso} {time_text}",
        "%Y-%m-%d %I:%M %p"
    )

    local = dt.replace(
        tzinfo=ZoneInfo(
            TZ_MAP.get(
                timezone_name,
                "America/New_York"
            )
        )
    )

    eastern = local.astimezone(
        ZoneInfo("America/New_York")
    )

    return eastern.strftime("%-I:%M %p")


def parse_region(region, url):

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

    text = soup.get_text(
        "\n",
        strip=True
    )

    # Determine the timezone used by this tournament page.
    tz_match = re.search(
        r"All game times are "
        r"(Eastern|Central|Mountain|Pacific) time",
        text
    )

    timezone_name = (
        tz_match.group(1)
        if tz_match
        else "Eastern"
    )

    # Only examine the Tournament Schedule portion.
    if "Tournament Schedule" in text:
        text = text.split(
            "Tournament Schedule",
            1
        )[1]

    if "Secondary Navigation" in text:
        text = text.split(
            "Secondary Navigation",
            1
        )[0]

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    games = []

    current_date = None

    i = 0

    while i < len(lines):

        line = lines[i]

        # Example:
        # Sunday, August 9, 2026
        date_match = re.match(
            r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
            r"([A-Za-z]+) (\d{1,2}), 2026",
            line
        )

        if date_match:

            current_date = datetime.strptime(
                line,
                "%A, %B %d, %Y"
            ).strftime("%Y-%m-%d")

            i += 1
            continue


        # Example:
        # Game 2 | 1:00 p.m. - August 9
        game_match = re.match(
            r"Game\s+\d+"
            r"(?:\s*-\s*Championship)?"
            r"\s*\|\s*"
            r"(\d{1,2}:\d{2})\s*"
            r"([ap])\.?m\.?",
            line,
            re.I
        )

        if game_match and current_date:

            time_text = (
                game_match.group(1)
                + " "
                + game_match.group(2).upper()
                + "M"
            )

            game_time = convert_to_eastern(
                current_date,
                time_text,
                timezone_name
            )

            # Gather lines belonging to this game,
            # stopping at the next game/date.
            block = []

            j = i + 1

            while j < len(lines):

                next_line = lines[j]

                if re.match(
                    r"Game\s+\d+",
                    next_line
                ):
                    break

                if re.match(
                    r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
                    r"[A-Za-z]+ \d{1,2}, 2026",
                    next_line
                ):
                    break

                block.append(next_line)

                j += 1

print("\n--- MID-ATLANTIC DIAGNOSTIC ---")

url = URLS["Mid-Atlantic"]

r = requests.get(
    url,
    headers=HEADERS,
    timeout=30
)

print("HTTP status:", r.status_code)
print("Downloaded characters:", len(r.text))

print(
    "Contains Pennsylvania:",
    "Pennsylvania" in r.text
)

print(
    "Contains Delaware:",
    "Delaware" in r.text
)

print(
    "Contains Tournament Schedule:",
    "Tournament Schedule" in r.text
)

print(
    "Contains Game 2:",
    "Game 2" in r.text
)

print("--- END DIAGNOSTIC ---")
            # Remove labels
