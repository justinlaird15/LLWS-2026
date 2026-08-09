import json, re, sys, time
from pathlib import Path
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
BASE = json.loads((ROOT/"base_schedule.json").read_text())
URLS = {
    "Great Lakes":"https://www.littleleague.org/world-series/2026/llbws/tournaments/great-lakes-region/",
    "Metro":"https://www.littleleague.org/world-series/2026/llbws/tournaments/metro-region/",
    "Mid-Atlantic":"https://www.littleleague.org/world-series/2026/llbws/tournaments/mid-atlantic-region/",
    "Midwest":"https://www.littleleague.org/world-series/2026/llbws/tournaments/midwest-region/",
    "Mountain":"https://www.littleleague.org/world-series/2026/llbws/tournaments/mountain-region/",
    "New England":"https://www.littleleague.org/world-series/2026/llbws/tournaments/new-england-region/",
    "Northwest":"https://www.littleleague.org/world-series/2026/llbws/tournaments/northwest-region/",
    "Southeast":"https://www.littleleague.org/world-series/2026/llbws/tournaments/southeast-region/",
    "Southwest":"https://www.littleleague.org/world-series/2026/llbws/tournaments/southwest-region/",
    "West":"https://www.littleleague.org/world-series/2026/llbws/tournaments/west-region/",
    "World Series":"https://www.littleleague.org/world-series/2026/llbws/tournaments/world-series/",
}
MONTHS={m:i for i,m in enumerate(["January","February","March","April","May","June","July","August","September","October","November","December"],1)}
headers={"User-Agent":"Mozilla/5.0 LLWS-schedule-personal-dashboard/1.0"}

def clean(s):
    return re.sub(r"\s+"," ",s).strip()

def parse_page(region,url):
    r=requests.get(url,headers=headers,timeout=30)
    r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    text=soup.get_text("\n",strip=True)
    lines=[clean(x) for x in text.splitlines() if clean(x)]
    games=[]
    current_date=None

    # The official pages render headings like "Sunday, August 9, 2026",
    # then "Game 1 ... 10:00 AM ...", team names and optional numeric scores.
    date_re=re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), ([A-Z][a-z]+) (\d{1,2}), 2026$")
    game_re=re.compile(r"^Game\s+(\d+).*?(\d{1,2}:\d{2})\s*([APap]\.?[Mm]\.?)",re.I)
    score_re=re.compile(r"^\d{1,2}$")
    skip_words={"Watch","Box Score","TBA","Tournament Schedule","All game times are Eastern time.","Box scores are unofficial."}

    i=0
    while i<len(lines):
        dm=date_re.match(lines[i])
        if dm:
            mon=MONTHS[dm.group(2)]
            current_date=f"2026-{mon:02d}-{int(dm.group(3)):02d}"
            i+=1; continue
        gm=game_re.search(lines[i])
        if gm and current_date:
            hhmm=gm.group(2)
            ap=gm.group(3).replace(".","").upper()
            dt=datetime.strptime(hhmm+" "+ap,"%I:%M %p")
            time_str=dt.strftime("%-I:%M %p")
            # collect a small block until next Game/date
            block=[]
            j=i+1
            while j<len(lines) and j<i+18 and not game_re.search(lines[j]) and not date_re.match(lines[j]):
                if lines[j] not in skip_words and not lines[j].startswith("Image:"):
                    block.append(lines[j])
                j+=1

            # Candidate team names are text lines; scores are adjacent small integers.
            # Filter obvious labels/codes/links.
            cand=[]
            for b in block:
                if b in skip_words: continue
                if score_re.match(b):
                    cand.append(("score",b))
                elif len(b)>2 and not re.match(r"^[A-Z]{1,4}$",b) and not b.startswith("Game "):
                    if not any(x in b for x in ["Region Tournament","Little League","Championship Game","Presented by"]):
                        cand.append(("text",b))
            # Build team/score pairs by retaining likely team-name lines near scores.
            names=[]
            scores=[]
            for typ,val in cand:
                if typ=="score": scores.append(val)
                else:
                    # common region labels can be team labels; retain first two useful names
                    if val not in names:
                        names.append(val)
            # Prefer last few meaningful names because page blocks often contain abbreviations before full names.
            names=[n for n in names if n not in {"Watch","Box Score"}]
            if len(names)>=2:
                team1,team2=names[0],names[1]
                matchup=f"{team1} vs {team2}"
                status=""
                if len(scores)>=2:
                    matchup=f"{team1} {scores[0]} — {team2} {scores[1]}"
                    status="FINAL"
                games.append({"date":current_date,"time":time_str,"region":region,"matchup":matchup,"status":status})
            i=j; continue
        i+=1
    return games

scraped=[]
errors=[]
for region,url in URLS.items():
    try:
        g=parse_page(region,url)
        if g: scraped.extend(g)
        else: errors.append(f"{region}: no games parsed")
    except Exception as e:
        errors.append(f"{region}: {e}")
    time.sleep(.2)

# Overlay scraped matchup/status onto base by date/time/region.
out=[]
lookup={(g["date"],g["time"],g["region"]):g for g in scraped}
for b in BASE:
    x=dict(b)
    s=lookup.get((b["date"],b["time"],b["region"]))
    if s:
        # Only replace matchup when parser found two meaningful sides.
        if " vs " in s["matchup"] or " — " in s["matchup"]:
            x["matchup"]=s["matchup"]
        if s.get("status"): x["status"]=s["status"]
    out.append(x)

payload={
    "updated":datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "source":"Official LittleLeague.org tournament pages",
    "errors":errors,
    "games":out
}
(ROOT/"latest.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
print(f"Wrote {len(out)} games; scraped {len(scraped)} schedule rows")
if errors: print("Warnings:",*errors,sep="\n- ")
