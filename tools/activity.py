#!/usr/bin/env python3
"""Builds assets/activity.svg: the last year of GitHub contributions, streaks and
achievements, drawn in the datacrate360.com light style.

Reads the public contribution graph and achievements from github.com (the same
data your profile shows), saves them to data/activity.json, and falls back to
that file when github.com can't be reached.

Run from the repository root: python tools/activity.py
"""
import html, json, os, re, sys, urllib.request
from datetime import date, timedelta
from common import *

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "activity.json")
OUT = os.path.join(ROOT, "assets", "activity.svg")

# datacrate360.com light palette
L_BG, L_SURFACE, L_LINE, L_TEXT, L_MUTED, L_DIM, L_ACCENT = "#FAFAF9", "#FFFFFF", "#E7E5E0", "#141414", "#6B6B66", "#A3A19B", "#0F4C4C"
RAMP = ["#EFEEEA", "#C9E3DF", "#8CC5BB", "#3F8F84", "#0F4C4C"]
ABOUT = {"Pull Shark": "Merged pull requests", "Pair Extraordinaire": "Co-authored commits", "YOLO": "Merged without a review",
         "Public Sponsor": "Sponsors open source", "Quickdraw": "Closed an issue fast", "Starstruck": "A repo with many stars",
         "Galaxy Brain": "Accepted answers", "Arctic Code Vault Contributor": "Code in the 2020 Arctic Vault"}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 profile-activity"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")

def fetch(login, old):
    t = get(f"https://github.com/users/{login}/contributions")
    tips = {m.group(1): html.unescape(m.group(2)).strip() for m in re.finditer(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>(.*?)</tool-tip>', t, re.S)}
    days = []
    for m in re.finditer(r"<td\b([^>]*)>", t):
        attrs = m.group(1)
        d = re.search(r'data-date="([\d-]+)"', attrs)
        if not d:
            continue
        lv = int((re.search(r'data-level="(\d)"', attrs) or [0, 0])[1])
        tid = (re.search(r'\bid="([^"]+)"', attrs) or [0, ""])[1]
        c = re.match(r"(\d[\d,]*|No) contribution", tips.get(tid, ""))
        n = 0 if not c or c.group(1) == "No" else int(c.group(1).replace(",", ""))
        days.append([d.group(1), lv, n])
    days.sort()
    if len(days) < 300:
        raise ValueError("contribution graph not found")
    tot = re.search(r"([\d,]+)\s+contributions?\s+in the last year", t)
    total = int(tot.group(1).replace(",", "")) if tot else sum(d[2] for d in days)
    ach = old.get("achievements", [])
    try:
        a = get(f"https://github.com/{login}?tab=achievements")
        found = []
        hits = list(re.finditer(r'alt="Achievement: ([^"]+)"', a))
        for i, m in enumerate(hits):
            name = html.unescape(m.group(1))
            if name in [f[0] for f in found]:
                continue
            # the "x2" tier label sits between this badge and the next one
            end = hits[i + 1].start() if i + 1 < len(hits) else m.end() + 1500
            tier = re.search(r"\bx(\d)\b", re.sub(r"<[^>]+>", " ", a[m.end():end]))
            found.append([name, int(tier.group(1)) if tier else 1])
        if found:
            ach = found
    except Exception as e:
        print(f"  (achievements unavailable: {e})", file=sys.stderr)
    return {"login": login, "total": total, "days": days, "achievements": ach}

def streaks(days):
    longest = run = 0
    for _, _, n in days:
        run = run + 1 if n > 0 else 0
        longest = max(longest, run)
    cur = 0
    seq = [n for _, _, n in days]
    if seq and seq[-1] == 0:
        seq = seq[:-1]  # today may not have started yet
    for n in reversed(seq):
        if n == 0:
            break
        cur += 1
    return cur, longest

def draw(data):
    W = 850; x0 = 36
    days = data["days"]
    first = date.fromisoformat(days[0][0])
    start = first - timedelta(days=(first.weekday() + 1) % 7)  # weeks start on Sunday, as on GitHub
    cells = {d: (lv, n) for d, lv, n in days}
    weeks = ((date.fromisoformat(days[-1][0]) - start).days // 7) + 1
    cs, gap = 11, 3
    gx = x0 + 34; gy = 236
    cur, longest = streaks(days)
    busiest = max(days, key=lambda d: d[2])
    active = sum(1 for d in days if d[2] > 0)
    b = [f'<rect width="{W}" height="{{H}}" rx="16" fill="{L_BG}"/>']
    b.append(f'<text x="{x0-1}" y="60" font-family="Disp" font-size="30" letter-spacing="-.66" fill="{L_TEXT}">Activity.</text>'
             f'<text x="{x0}" y="88" font-family="Sans" font-size="15" fill="{L_MUTED}">Contributions on GitHub in the last year. Updated daily.</text>')
    # stats: top-ruled columns
    bd = date.fromisoformat(busiest[0])
    stats = [("Contributions", f'{data["total"]:,}', "in the last year"), ("Active days", f"{active}", "with at least one"),
             ("Longest streak", f"{longest}", "days in a row"), ("Busiest day", f"{busiest[2]}", bd.strftime("%b %-d, %Y"))]
    cw = (W - 72 - 22 * 3) / 4
    for i, (lab, num, sub) in enumerate(stats):
        x = x0 + i * (cw + 22)
        b.append(f'<line x1="{x}" y1="112" x2="{x+cw:.1f}" y2="112" stroke="{L_TEXT}" stroke-opacity=".75"/>'
                 f'<text x="{x}" y="134" font-family="SansM" font-size="12" fill="{L_TEXT}">{lab}</text>'
                 f'<text x="{x-1}" y="170" font-family="Disp" font-size="32" letter-spacing="-.8" fill="{L_TEXT}">{num}</text>'
                 f'<text x="{x+width(num, "Disp", 32, -.8)+6:.1f}" y="170" font-family="Serif" font-size="15" fill="{L_ACCENT}">{esc(sub)}</text>')
    # heatmap panel
    pw = weeks * (cs + gap) - gap + 34 + 30
    b.append(f'<rect x="{x0}" y="{gy-34}" width="{W-72}" height="{7*(cs+gap)+60}" rx="12" fill="{L_SURFACE}" stroke="{L_LINE}"/>')
    gx = x0 + (W - 72 - (weeks * (cs + gap) - gap + 30)) / 2 + 30
    for r, lab in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        b.append(f'<text x="{gx-8}" y="{gy+r*(cs+gap)+9}" text-anchor="end" font-family="Sans" font-size="10" fill="{L_DIM}">{lab}</text>')
    for w in range(weeks):
        wd = start + timedelta(days=7 * w)
        if 0 < w < weeks - 1 and wd.day <= 7:
            b.append(f'<text x="{gx+w*(cs+gap)}" y="{gy-10}" font-family="Sans" font-size="10" fill="{L_DIM}">{wd.strftime("%b")}</text>')
        for r in range(7):
            d = (wd + timedelta(days=r)).isoformat()
            if d not in cells:
                continue
            lv, n = cells[d]
            delay = .3 + w * .018
            anim = f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{delay/(delay+.3):.3f};1" dur="{delay+.3:.2f}s" fill="freeze"/>' if lv else ""
            b.append(f'<rect x="{gx+w*(cs+gap)}" y="{gy+r*(cs+gap)}" width="{cs}" height="{cs}" rx="2.5" fill="{RAMP[min(lv,4)]}"'
                     + (f' stroke="{L_LINE}" stroke-width=".6"' if lv == 0 else "") + f'>{anim}</rect>')
    ly = gy + 7 * (cs + gap) + 14
    lx = W - 36 - 16 - 5 * (cs + gap) - 34
    b.append(f'<text x="{lx-8}" y="{ly+9}" text-anchor="end" font-family="Sans" font-size="10" fill="{L_DIM}">Less</text>'
             f'<text x="{gx}" y="{ly+9}" font-family="Sans" font-size="10" fill="{L_DIM}">github.com/{data["login"]}</text>')
    for k in range(5):
        b.append(f'<rect x="{lx+k*(cs+gap)}" y="{ly}" width="{cs}" height="{cs}" rx="2.5" fill="{RAMP[k]}"' + (f' stroke="{L_LINE}" stroke-width=".6"' if k == 0 else "") + "/>")
    b.append(f'<text x="{lx+5*(cs+gap)+4}" y="{ly+9}" font-family="Sans" font-size="10" fill="{L_DIM}">More</text>')
    # achievements
    ay = ly + 52
    ach = data.get("achievements", [])
    if ach:
        b.append(f'<text x="{x0}" y="{ay}" font-family="SansM" font-size="12" fill="{L_TEXT}">Achievements</text>')
        x = x0; y = ay + 16
        for name, tier in ach:
            sub = ABOUT.get(name, "GitHub achievement")
            t = name + (f"  ×{tier}" if tier and tier > 1 else "")
            w = max(width(t, "SansSB", 13), width(sub, "Sans", 11.5)) + 58
            if x + w > W - 36:
                x = x0; y += 58
            b.append(f'<rect x="{x}" y="{y}" width="{w:.1f}" height="48" rx="10" fill="{L_SURFACE}" stroke="{L_LINE}"/>'
                     f'<circle cx="{x+24}" cy="{y+24}" r="12" fill="{L_ACCENT}" fill-opacity=".09" stroke="{L_ACCENT}" stroke-opacity=".5"/>'
                     f'<path d="M{x+24} {y+17}l2 4.2 4.6.6-3.4 3.2.9 4.6-4.1-2.3-4.1 2.3.9-4.6-3.4-3.2 4.6-.6z" fill="{L_ACCENT}"/>'
                     f'<text x="{x+44}" y="{y+21}" font-family="SansSB" font-size="13" fill="{L_TEXT}">{esc(name)}'
                     + (f'<tspan font-family="Serif" font-size="14" fill="{L_ACCENT}">  ×{tier}</tspan>' if tier and tier > 1 else "")
                     + f'</text><text x="{x+44}" y="{y+37}" font-family="Sans" font-size="11.5" fill="{L_MUTED}">{esc(sub)}</text>')
            x += w + 10
        H = int(y + 48 + 32)
    else:
        H = int(ly + 44)
    b.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="16" stroke="{L_LINE}"/>')
    body = "".join(b).replace("{H}", str(H))
    return svg(W, H, body)

def main():
    old = json.load(open(DATA)) if os.path.exists(DATA) else {}
    login = old.get("login") or os.environ.get("PROFILE_LOGIN", "srikanthpinisetti")
    try:
        data = fetch(login, old)
        os.makedirs(os.path.dirname(DATA), exist_ok=True)
        json.dump(data, open(DATA, "w"))
    except Exception as e:
        print(f"  (using saved activity: {e})", file=sys.stderr)
        data = old
    open(OUT, "w").write(draw(data))
    print(f"Built activity: {data['total']} contributions, {len(data.get('achievements', []))} achievements.")

if __name__ == "__main__":
    main()
