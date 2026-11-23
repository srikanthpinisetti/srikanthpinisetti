"""Shared drawing helpers for the profile cards (fonts, text, palette)."""
import base64, io, json, os, re, sys, urllib.request
from fontTools.ttLib import TTFont
from fontTools import subset

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "tools", "fonts")

# datacrate360.com dark palette
BG, SURFACE, LINE, GRID = "#0E1211", "#151A19", "#242C2B", "#161D1C"
TEXT, MUTED, DIM, GLOW = "#EDF3F2", "#93A8A5", "#5F716E", "#1F5A52"
ACCENTS = ["#6CC4B6", "#F0A27A", "#8FB8DE", "#D9B56C"]
LANG = {"Rust": "#DEA584", "Python": "#3572A5", "JavaScript": "#F1E05A", "TypeScript": "#3178C6", "Go": "#00ADD8",
        "Ruby": "#701516", "HTML": "#E34C26", "Shell": "#89E051", "Java": "#B07219", "SQL": "#E38C00", "Swift": "#F05138"}

# ---------------- fonts ----------------
_f = {}
def font(n):
    if n not in _f:
        _f[n] = TTFont(os.path.join(FONTS, n + ".woff2"))
    return _f[n]

def width(text, n, size, spacing=0.0):
    f = font(n); cmap, hm = f.getBestCmap(), f["hmtx"]; upm = f["head"].unitsPerEm
    w = sum(hm[cmap[ord(c)]][0] if ord(c) in cmap else upm * .55 for c in text)
    return w / upm * size + spacing * len(text)

def face(n, chars):
    f = TTFont(os.path.join(FONTS, n + ".woff2"))
    o = subset.Options(); o.flavor = "woff2"; o.layout_features = ["kern", "liga", "calt"]; o.notdef_outline = True
    s = subset.Subsetter(o); s.populate(text=chars); s.subset(f)
    f.flavor = "woff2"; b = io.BytesIO(); f.save(b)
    return f"@font-face{{font-family:'{n}';src:url(data:font/woff2;base64,{base64.b64encode(b.getvalue()).decode()}) format('woff2');}}"

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def svg(w, h, body):
    used = sorted(set(re.findall(r'font-family="([A-Za-z]+)"', body)))
    text = re.sub(r"<[^>]+>", "", body).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    css = "".join(face(n, "".join(sorted(set(text))) or " ") for n in used)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" fill="none">'
            f'<style>{css}</style>{body}</svg>')

def wrap(text, n, size, maxw, max_lines):
    out, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if width(t, n, size) <= maxw:
            cur = t
        else:
            out.append(cur); cur = word
    if cur:
        out.append(cur)
    if len(out) > max_lines:
        out = out[:max_lines]
        while width(out[-1] + "…", n, size) > maxw:
            out[-1] = out[-1].rsplit(" ", 1)[0]
        out[-1] += "…"
    return out

def background(w, h, gid, glow_at, accent):
    gx, gy = glow_at
    return (f'<defs><pattern id="{gid}g" width="44" height="44" patternUnits="userSpaceOnUse"><path d="M44 0H0V44" stroke="{GRID}" fill="none"/></pattern>'
            f'<radialGradient id="{gid}r"><stop offset="0" stop-color="{accent}" stop-opacity=".22"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>'
            f'<clipPath id="{gid}c"><rect width="{w}" height="{h}" rx="14"/></clipPath></defs>'
            f'<rect width="{w}" height="{h}" rx="14" fill="{BG}"/>'
            f'<g clip-path="url(#{gid}c)"><rect width="{w}" height="{h}" fill="url(#{gid}g)"/>'
            f'<circle cx="{gx}" cy="{gy}" r="190" fill="url(#{gid}r)"><animate attributeName="opacity" values=".6;1;.6" dur="7s" repeatCount="indefinite"/></circle></g>')

