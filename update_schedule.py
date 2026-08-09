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


def clean(value
