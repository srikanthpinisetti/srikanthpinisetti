#!/usr/bin/env python3
"""Builds the Projects section of the profile README.

Reads projects.json, fills in live details from the GitHub API when it can
(language, license, stars, latest release), adds any public repo of yours
tagged with the 'showcase' topic, draws one card per project in the
datacrate360.com style, and rewrites the README between the PROJECTS markers.

Needs: pip install fonttools brotli
Run from the repository root: python tools/projects.py
"""
import json, os, re, sys, urllib.request
from common import *

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "projects")
README = os.path.join(ROOT, "README.md")

# ---------------- data ----------------
def api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={"Accept": "application/vnd.github+json", "User-Agent": "profile-projects"})
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except Exception as e:
        print(f"  (GitHub API unavailable for {path}: {e})", file=sys.stderr)
        return None

def enrich(p):
    if "repo" not in p:
        return p
    r = api(f"/repos/{p['repo']}")
    if isinstance(r, dict) and "full_name" in r:
        p["language"] = r.get("language") or p.get("language")
        lic = (r.get("license") or {}).get("spdx_id")
        if lic and lic != "NOASSERTION":
            p["license"] = lic
        p["stars"] = r.get("stargazers_count", 0)
        p.setdefault("blurb", r.get("description") or "")
        if p.get("status") == "auto":
            rel = api(f"/repos/{p['repo']}/releases/latest")
            if isinstance(rel, dict) and rel.get("tag_name"):
                p["version"] = rel["tag_name"]
    return p

def discover(cfg, known):
    found = []
    for acct in cfg.get("accounts", []):
        for path in (f"/orgs/{acct}/repos?type=public&per_page=100", f"/users/{acct}/repos?type=owner&per_page=100"):
            rs = api(path)
            if isinstance(rs, list):
                break
        for r in rs if isinstance(rs, list) else []:
            if r.get("fork") or r.get("archived") or r.get("private"):
                continue
            if cfg.get("topic") in (r.get("topics") or []) and r["full_name"] not in known:
                found.append({"repo": r["full_name"], "name": r["name"].replace("-", " ").title(),
                              "kind": "Open source", "blurb": r.get("description") or "", "status": "auto"})
                known.add(r["full_name"])
    return found

def slug(p):
    return re.sub(r"[^a-z0-9]+", "-", p["name"].lower()).strip("-")

def link(p):
    return p.get("url") or f"https://github.com/{p['repo']}"

# ---------------- drawing ----------------
CW, CH = 420, 220

def card(p, i):
    a = ACCENTS[i % len(ACCENTS)]
    b = [background(CW, CH, f"c{i}", (CW - 30, -10), a)]
    # monogram tile
    mono = p.get("mono") or "".join(w[0] for w in p["name"].split()[:2]).upper()
    b.append(f'<rect x="24.75" y="24.75" width="38.5" height="38.5" rx="9" fill="{SURFACE}" stroke="{a}" stroke-opacity=".7" stroke-width="1.5"/>'
             f'<text x="44" y="49.5" text-anchor="middle" font-family="MonoM" font-size="14" fill="{a}">{esc(mono)}</text>')
    b.append(f'<text x="78" y="38" font-family="MonoM" font-size="9.5" letter-spacing="1.3" fill="{DIM}">{esc(p.get("kind", "Project").upper())}</text>')
    name_size = 21
    while width(p["name"], "Disp", name_size, -.3) > CW - 78 - 24 - 96 and name_size > 15:
        name_size -= 1
    b.append(f'<text x="77" y="62" font-family="Disp" font-size="{name_size}" letter-spacing="-.3" fill="{TEXT}">{esc(p["name"])}</text>')
    # status chip
    st = p.get("version") if p.get("status") == "auto" else p.get("status")
    if st:
        dot = {"Live": "#6CC4B6", "In development": "#D9B56C"}.get(st, a)
        sw = width(st, "SansM", 11) + 30
        b.append(f'<rect x="{CW-24-sw:.1f}" y="24" width="{sw:.1f}" height="24" rx="12" fill="{SURFACE}" stroke="{LINE}"/>'
                 f'<circle cx="{CW-24-sw+13:.1f}" cy="36" r="3" fill="{dot}"/>'
                 f'<text x="{CW-24-sw+22:.1f}" y="40" font-family="SansM" font-size="11" fill="{TEXT}">{esc(st)}</text>')
    for k, line in enumerate(wrap(p.get("blurb", ""), "Sans", 13.5, CW - 48, 3)):
        b.append(f'<text x="24" y="{98+k*20}" font-family="Sans" font-size="13.5" fill="{MUTED}">{esc(line)}</text>')
    b.append(f'<line x1="24" y1="{CH-48}" x2="{CW-24}" y2="{CH-48}" stroke="{LINE}"/>')
    x = 24; fy = CH - 22
    if p.get("language"):
        b.append(f'<circle cx="{x+5}" cy="{fy-4}" r="4.5" fill="{LANG.get(p["language"], a)}"/>'
                 f'<text x="{x+15}" y="{fy}" font-family="Sans" font-size="12" fill="{MUTED}">{esc(p["language"])}</text>')
        x += 15 + width(p["language"], "Sans", 12) + 16
    if p.get("license"):
        b.append(f'<text x="{x}" y="{fy}" font-family="Sans" font-size="12" fill="{DIM}">{esc(p["license"])}</text>')
        x += width(p["license"], "Sans", 12) + 16
    if p.get("stars"):
        b.append(f'<text x="{x}" y="{fy}" font-family="Sans" font-size="12" fill="{DIM}">★ {p["stars"]}</text>')
    lab = p.get("link_label") or ("View repo" if "repo" in p else "Visit site")
    lw = width(lab, "SansM", 12)
    b.append(f'<text x="{CW-24-14-lw:.1f}" y="{fy}" font-family="SansM" font-size="12" fill="{TEXT}">{esc(lab)}</text>'
             f'<path d="M{CW-30} {fy-8}l5 4-5 4" stroke="{TEXT}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>')
    b.append(f'<rect x=".5" y=".5" width="{CW-1}" height="{CH-1}" rx="14" stroke="{LINE}"/>')
    return svg(CW, CH, "".join(b))

def more_card(url):
    b = [background(CW, CH, "mo", (CW / 2, CH + 40), ACCENTS[0])]
    b.append(f'<rect x="1" y="1" width="{CW-2}" height="{CH-2}" rx="13" stroke="{DIM}" stroke-dasharray="5 6"/>')
    b.append(f'<text x="{CW/2}" y="98" text-anchor="middle" font-family="Disp" font-size="22" letter-spacing="-.3" fill="{TEXT}">More on GitHub</text>'
             f'<text x="{CW/2}" y="126" text-anchor="middle" font-family="Serif" font-size="15" fill="{MUTED}">Everything else I’m building and exploring.</text>'
             f'<text x="{CW/2}" y="160" text-anchor="middle" font-family="Mono" font-size="12" fill="{ACCENTS[0]}">{esc(url.replace("https://", ""))}</text>')
    return svg(CW, CH, "".join(b))

def header(count, W=850):
    """The dark Projects band; W=400 is the phone version."""
    phone = W < 600
    H = 150 if phone else 132
    b = [background(W, H, "hd", (W - 130, H + 38), GLOW)]
    sub = ["Tools I build outside client work,", "mostly for data and AI engineers."] if phone else ["Tools I build outside client work, mostly for data and AI engineers."]
    x = 20 if phone else 36
    b.append(f'<text x="{x}" y="44" font-family="MonoM" font-size="10" letter-spacing="1.5" fill="{ACCENTS[0]}">SIDE PROJECTS · OPEN SOURCE</text>'
             f'<text x="{x-1}" y="84" font-family="Disp" font-size="{28 if phone else 32}" letter-spacing="-.7" fill="{TEXT}">Projects.</text>'
             + "".join(f'<text x="{x}" y="{110+i*20}" font-family="Sans" font-size="14" fill="{MUTED}">{l}</text>' for i, l in enumerate(sub)))
    lab = "All projects"
    w = width(lab, "SansM", 13) + 32
    b.append(f'<rect x="{W-x-w:.1f}" y="{60 if phone else 62}" width="{w:.1f}" height="34" rx="17" fill="{TEXT}"/>'
             f'<text x="{W-x-w+16:.1f}" y="{81.7 if phone else 83.7}" font-family="SansM" font-size="13" fill="#141414">{lab}</text>')
    b.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="14" stroke="{LINE}"/>')
    return svg(W, H, "".join(b))

# ---------------- main ----------------
def main():
    cfg = json.load(open(os.path.join(ROOT, "projects.json")))
    projects = [dict(p) for p in cfg["projects"]]
    known = {p["repo"] for p in projects if "repo" in p} | set(cfg.get("exclude", []))
    projects += discover(cfg, known)
    projects = [enrich(p) for p in projects]
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".svg"):
            os.remove(os.path.join(OUT, f))
    more = cfg.get("more_url", "https://github.com/" + cfg["accounts"][0])
    open(os.path.join(OUT, "header.svg"), "w").write(header(len(projects)))
    open(os.path.join(OUT, "header-phone.svg"), "w").write(header(len(projects), W=400))
    items = []
    for i, p in enumerate(projects):
        open(os.path.join(OUT, slug(p) + ".svg"), "w").write(card(p, i))
        alt = f'{p["name"]}: {p.get("blurb", "")}'.replace('"', "'")
        items.append(f'<a href="{link(p)}"><img src="./assets/projects/{slug(p)}.svg" width="49%" alt="{esc(alt)}"/></a>')
    if len(projects) % 2 == 1:  # fill the empty slot; the header's "All projects" link covers the even case
        open(os.path.join(OUT, "more.svg"), "w").write(more_card(more))
        items.append(f'<a href="{more}"><img src="./assets/projects/more.svg" width="49%" alt="More projects on GitHub: {more}"/></a>')
    rows = ["<p align=\"center\">\n  " + "\n  ".join(items[k:k + 2]) + "\n</p>" for k in range(0, len(items), 2)]
    block = (f'<a href="{more}"><picture><source media="(max-width: 700px)" srcset="./assets/projects/header-phone.svg"/>'
             f'<img src="./assets/projects/header.svg" width="100%" alt="Projects: tools I build outside client work, mostly for data and AI engineers."/></picture></a>\n\n'
             + "\n\n".join(rows))
    md = open(README).read()
    md = re.sub(r"<!-- PROJECTS:START -->.*?<!-- PROJECTS:END -->",
                lambda m: f"<!-- PROJECTS:START -->\n{block}\n<!-- PROJECTS:END -->", md, flags=re.S)
    open(README, "w").write(md)
    print(f"Built {len(projects)} project cards.")

if __name__ == "__main__":
    main()
