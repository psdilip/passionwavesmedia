#!/usr/bin/env python3
"""
Passionwaves Media — site builder.

Workflow:
  1. Write an article as Markdown in  content/your-slug.md  (with a small header).
  2. Run:  python3 build.py
  3. Upload everything in  public/  to your S3 bucket.

That's it. You never edit HTML by hand. No pip installs — pure standard library.
"""
import html
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
PUBLIC = ROOT / "public"

# ----------------------------------------------------------------------
# Tiny Markdown -> HTML (enough for articles: headings, lists, quotes,
# code, links, images, bold/italic, rules).
# ----------------------------------------------------------------------
def _inline(text):
    codes = []
    text = re.sub(r"`([^`]+)`", lambda m: (codes.append(m.group(1)), f"\x00{len(codes)-1}\x00")[1], text)
    text = html.escape(text, quote=False)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: "<code>" + html.escape(codes[int(m.group(1))], quote=False) + "</code>", text)
    return text


def md_to_html(md):
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            i += 1; continue
        if line.strip().startswith("```"):
            i += 1; buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf), quote=False) + "</code></pre>")
            continue
        if line.strip().startswith("<iframe") and line.strip().endswith("</iframe>"):
            cls = "video-embed" if "youtube.com/embed" in line else "map-embed"
            out.append(f'<div class="{cls}">{line.strip()}</div>'); i += 1; continue
        if re.match(r"^\s*-{3,}\s*$", line):
            out.append("<hr>"); i += 1; continue
        h = re.match(r"^(#{1,4})\s+(.*)$", line)
        if h:
            lvl = len(h.group(1)); out.append(f"<h{lvl}>{_inline(h.group(2).strip())}</h{lvl}>"); i += 1; continue
        if line.lstrip().startswith(">"):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append("<blockquote>" + _inline(" ".join(buf)) + "</blockquote>"); continue
        if re.match(r"^\s*[-*]\s+", line):
            buf = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                buf.append(re.sub(r"^\s*[-*]\s+", "", lines[i])); i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in buf) + "</ul>"); continue
        if re.match(r"^\s*\d+\.\s+", line):
            buf = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                buf.append(re.sub(r"^\s*\d+\.\s+", "", lines[i])); i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(x)}</li>" for x in buf) + "</ol>"); continue
        buf = []
        while (i < len(lines) and lines[i].strip() != ""
               and not re.match(r"^(#{1,4})\s|^\s*[-*]\s+|^\s*\d+\.\s+|^\s*>", lines[i])
               and not lines[i].strip().startswith("```")):
            buf.append(lines[i]); i += 1
        out.append("<p>" + _inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


def parse_md(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    meta, body = {}, text
    if m:
        for l in m.group(1).splitlines():
            if ":" in l:
                k, v = l.split(":", 1); v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                    v = v[1:-1]
                meta[k.strip()] = v
        body = m.group(2)
    return meta, body


# ----------------------------------------------------------------------
# HTML building blocks
# ----------------------------------------------------------------------
WAVE = ('<svg viewBox="0 0 24 16" fill="none"><path d="M2 10 q3 -6 6 0 t6 0 t6 0" '
        'stroke="#fff" stroke-width="2.2" stroke-linecap="round"/></svg>')

LINKEDIN = ('<svg viewBox="0 0 24 24" fill="currentColor"><path d="M4.98 3.5C4.98 4.88 3.87 6 2.5 6S0 4.88 0 3.5 '
            '1.12 1 2.5 1 4.98 2.12 4.98 3.5zM0 8h5v16H0V8zm7.5 0h4.78v2.19h.07c.67-1.27 2.3-2.61 4.73-2.61 '
            '5.06 0 6 3.33 6 7.66V24h-5v-6.99c0-1.67-.03-3.82-2.33-3.82-2.33 0-2.69 1.82-2.69 3.7V24h-5V8z"/></svg>')
XICON = ('<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.24 2H21l-6.55 7.48L22 22h-6.15l-4.82-6.3L5.5 22H2.74'
         'l7.01-8-7.4-12h6.3l4.36 5.77L18.24 2zm-1.08 18h1.7L7.02 3.9H5.2L17.16 20z"/></svg>')

HEART = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 21s-7.5-4.6-10-9.2'
         'C.4 8.4 2 5 5.3 5c2 0 3.3 1.1 4.7 2.8C11.4 6.1 12.7 5 14.7 5 18 5 19.6 8.4 22 11.8 19.5 16.4 12 21 12 21z"/></svg>')
EYE = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M1 12s4-7 11-7 11 7 11 7'
       '-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>')

_TS = " ".join(["t180 0"] * 17)  # 17 half-periods after the opening curve
HERO_WAVE = f'''<div class="wave-wrap" aria-hidden="true">
  <svg viewBox="0 0 1440 150" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="wg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="720" y2="0" spreadMethod="repeat">
      <stop offset="0%" stop-color="#FF6B4A"/><stop offset="25%" stop-color="#E5468A"/>
      <stop offset="50%" stop-color="#6B4EE6"/><stop offset="75%" stop-color="#22B0C4"/>
      <stop offset="100%" stop-color="#FF6B4A"/>
    </linearGradient></defs>
    <g class="wave-flow f3" opacity="0.26"><path fill="none" stroke="url(#wg)" stroke-width="1.5" stroke-linecap="round" d="M-720 50 q90 -26 180 0 {_TS}"/></g>
    <g class="wave-flow f2" opacity="0.5"><path fill="none" stroke="url(#wg)" stroke-width="2" stroke-linecap="round" d="M-720 95 q90 -30 180 0 {_TS}"/></g>
    <g class="wave-flow f1" opacity="0.95"><path fill="none" stroke="url(#wg)" stroke-width="2.5" stroke-linecap="round" d="M-720 70 q90 -40 180 0 {_TS}"/></g>
  </svg></div>'''


def brand(cfg, sm=False):
    cls = "brand brand--sm" if sm else "brand"
    return (f'<a href="index.html" class="{cls}"><span class="brand-mark" aria-hidden="true">{WAVE}</span>'
            f'<span class="brand-text">{cfg["brandName"]}</span></a>')


def dot(color):
    return f'<span class="dot" style="background:{color}"></span>'


def footer(cfg, present_cats=None):
    present_cats = present_cats if present_cats is not None else list(cfg["categories"].keys())
    cats = '<a href="articles.html">All articles</a>' + "".join(f'<a href="articles.html#{c}">{c}</a>' for c in present_cats)
    soc = ""
    if cfg["social"].get("linkedin"):
        soc += f'<a href="{cfg["social"]["linkedin"]}" target="_blank" rel="noopener">{LINKEDIN}LinkedIn</a>'
    if cfg["social"].get("x"):
        soc += f'<a href="{cfg["social"]["x"]}" target="_blank" rel="noopener">{XICON}X</a>'
    return f'''<footer class="footer"><div class="wrap">
  <div class="footer-top">
    <div>{brand(cfg, sm=True)}<p class="colophon">Spreading passions from me to the world — one article, one wave, at a time.</p></div>
    <nav>
      <div class="col"><h4>Read</h4>{cats}</div>
      <div class="col"><h4>More</h4><a href="index.html#mission">About</a><a href="feed.xml">RSS Feed</a></div>
      <div class="col"><h4>Elsewhere</h4>{soc}</div>
    </nav>
  </div>
  <div class="base mono">© {datetime.now().year} {cfg["brandName"]} · Built and hosted on AWS</div>
</div></footer>'''


def thumb_html(cfg, p):
    col = cfg["categories"].get(p["category"], "#999")
    fallback = f'<div class="c-thumb-fallback" style="--tc:{col}"><span>{p["category"]}</span></div>'
    if p.get("thumb"):
        img = (f'<img src="{p["thumb"]}" alt="" loading="lazy" '
               f'onerror="this.closest(\'.c-thumb\').classList.add(\'c-thumb--fallback\')">')
        return f'<div class="c-thumb">{img}{fallback}</div>'
    return f'<div class="c-thumb c-thumb--fallback">{fallback}</div>'


def trend_thumb_html(p):
    if p.get("thumb"):
        return (f'<span class="trend-thumb"><img src="{p["thumb"]}" alt="" loading="lazy" '
                f'onerror="this.parentElement.style.display=\'none\'"></span>')
    return '<span class="trend-thumb"></span>'


def posts_index_json(posts):
    return [{
        "slug": p["slug"], "title": p["title"], "excerpt": p["excerpt"],
        "category": p["category"], "tags": p["tags"], "thumb": p.get("thumb"),
        "date": p["card_date"], "iso": p["iso"], "minutes": p["minutes"],
    } for p in posts]


def tag_chips_html(tags, limit=4):
    return "".join(f'<span class="tagchip">{html.escape(t)}</span>' for t in tags[:limit])


def card_html(cfg, p, idx=0, extra=False):
    col = cfg["categories"].get(p["category"], "#999")
    cls = "card reveal in extra" if extra else "card reveal"
    return (f'<a href="{p["slug"]}.html" class="{cls}" style="--i:{idx}" data-cat="{p["category"]}">'
            f'{thumb_html(cfg, p)}'
            f'<div class="card-body">'
            f'<span class="catline mono">{dot(col)}{p["category"]}</span>'
            f'<h3>{p["title"]}</h3><p>{p["excerpt"]}</p>'
            f'<div class="tags">{tag_chips_html(p["tags"])}</div>'
            f'<div class="foot mono"><span>{p["card_date"]} · {p["minutes"]} min</span></div>'
            f'</div></a>')


def nav(cfg, home=False, active=""):
    about = "#mission" if home else "index.html#mission"
    def cls(x):
        return "navlink active" if x == active else "navlink"
    return (f'<header class="masthead"><div class="wrap masthead-inner">{brand(cfg)}<nav class="nav">'
            f'<a class="{cls("read")}" href="articles.html">Read</a>'
            f'<a class="{cls("about")}" href="{about}">About</a>'
            f'<a class="navlink" href="feed.xml" title="Subscribe via RSS">RSS</a>'
            f'</nav></div></header>')


def page_head(cfg, title, desc, canonical, jsonld):
    fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" '
             'href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?'
             'family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400;1,9..144,500'
             '&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">')
    return f'''<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{html.escape(desc, quote=True)}">
<link rel="canonical" href="{canonical}">
<link rel="alternate" type="application/rss+xml" title="{html.escape(cfg['brandName'], quote=True)}" href="{cfg['domain']}/feed.xml">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(desc, quote=True)}">
<meta property="og:image" content="{cfg['domain']}/og-cover.jpg">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{jsonld}</script>
{fonts}
<style>{STYLES}</style></head><body>'''


def page_tail(cfg, init_js=""):
    pw = json.dumps({"supabaseUrl": cfg["supabase"].get("url", ""), "supabaseAnonKey": cfg["supabase"].get("anonKey", "")})
    return f'<script>window.PW={pw};</script>\n<script>{APP_JS}</script>\n<script>{init_js}</script>\n</body></html>'


# ----------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------
def build_index(cfg, posts, present_cats):
    featured = next((p for p in posts if p.get("featured")), posts[0] if posts else None)
    feat_html = ""
    if featured:
        col = cfg["categories"].get(featured["category"], "#999")
        feat_img = (f'<img src="{featured["thumb"]}" alt="" loading="lazy" onerror="this.remove()">'
                    if featured.get("thumb") else "")
        feat_html = f'''<a href="{featured['slug']}.html" class="feature reveal">
  <div class="art">{feat_img}<div class="coord mono">{featured['category']} · {featured['minutes']} min</div></div>
  <div class="body"><span class="catline mono">{dot(col)}Featured</span>
    <h3>{featured['title']}</h3><p>{featured['excerpt']}</p><span class="readmore">Read the article</span></div></a>'''

    latest = [q for q in posts if q is not featured][:6]
    cards = "".join(card_html(cfg, p, i) for i, p in enumerate(latest))

    recent_items = "".join(
        f'<li><a class="trend-item" href="{p["slug"]}.html">'
        f'<span class="trend-rank mono">{i + 1}</span>'
        f'{trend_thumb_html(p)}'
        f'<span class="trend-body"><span class="t">{p["title"]}</span>'
        f'<span class="m">{p["card_date"]} · {p["minutes"]} min</span></span></a></li>'
        for i, p in enumerate(posts[:5])
    )
    trend_html = f'''<section class="section trending"><div class="wrap">
  <div class="section-head reveal"><h2>Trending</h2><p>What readers are actually clicking on right now — updates live, no rebuild needed.</p></div>
  <div class="trend-grid reveal">
    <div class="trend-col"><h4>Most viewed</h4><ol class="trend-list" id="trendViews"><li class="trend-empty">Loading…</li></ol></div>
    <div class="trend-col"><h4>Most liked</h4><ol class="trend-list" id="trendLikes"><li class="trend-empty">Loading…</li></ol></div>
    <div class="trend-col"><h4>Recent</h4><ol class="trend-list" id="trendRecent">{recent_items}</ol></div>
  </div>
</div></section>'''

    mission = cfg["mission"]
    mission_body = "".join(f"<p>{b}</p>" for b in mission["body"])
    mission_html = f'''<section class="section mission" id="mission"><div class="wrap mission-inner">
  <div class="reveal"><div class="mono">The idea</div><h2>{mission['heading']}</h2></div>
  <div class="reveal">{mission_body}<p class="sig">{mission['sig']}</p></div></div></section>'''

    body = f'''{nav(cfg, home=True)}
<section class="hero"><div class="wrap">
  <div class="mono eyebrow">{cfg['hero']['eyebrow']}</div>
  <h1>{cfg['hero']['titleHtml']}</h1>
  <p class="lede">{cfg['hero']['lede']}</p>
  <div class="cues"><a href="#latest"><button class="btn btn-grad">Start reading</button></a>
  <a href="#mission"><button class="btn btn-ghost">Why this exists</button></a></div>
  <div class="hero-stats mono" id="heroStats" hidden></div>
</div>{HERO_WAVE}</section>

<section class="section" id="latest"><div class="wrap">
  <div class="section-head reveal"><h2>Latest</h2><p>The newest dispatches — browse everything in the archive.</p></div>
  {feat_html}
  <div class="grid" id="grid">{cards}</div>
</div></section>

{trend_html}

<section class="section" style="padding-top:0"><div class="wrap">
  <div class="more-cta reveal"><a href="articles.html"><button class="btn btn-grad btn-lg">Browse all articles →</button></a></div>
</div></section>

{mission_html}
{footer(cfg, present_cats)}'''

    init_js = "window.PW_POSTS=" + json.dumps(posts_index_json(posts)) + ";pwInitTrending();"

    jsonld = json.dumps({"@context": "https://schema.org", "@type": "Blog",
                         "name": f'{cfg["brandName"]}', "url": cfg["domain"] + "/"})
    head = page_head(cfg, f'{cfg["brandName"]} — spreading what I love, from me to you',
                     "A personal publication spreading one person's passions to the world — AWS, travel, food, and life.",
                     cfg["domain"] + "/", jsonld)
    (PUBLIC / "index.html").write_text(head + body + page_tail(cfg, init_js), encoding="utf-8")


def build_archive(cfg, posts, present_cats):
    total = len(posts)

    posts_js = posts_index_json(posts)
    cat_colors = {c: cfg["categories"][c] for c in present_cats}
    quotes = cfg.get("quotes", [])

    sidebar = '''<aside class="arc-side">
  <div class="arc-quote" id="arcQuote" aria-live="polite"></div>
  <input type="search" id="arcSearch" class="arc-search" placeholder="Search titles, tags, places…">
  <nav class="arc-nav" id="arcNav" aria-label="Filter by category"></nav>
  <div class="arc-sortwrap">
    <label class="mono" for="arcSort">Sort</label>
    <select id="arcSort" class="arc-sort">
      <option value="new">Newest first</option>
      <option value="old">Oldest first</option>
      <option value="quick">Quickest read</option>
    </select>
  </div>
</aside>'''

    main = '''<div class="arc-main">
  <div class="arc-heading"><h2 id="arcHeadingTitle">All articles</h2><span class="mono" id="arcCount"></span></div>
  <div class="arc-grid" id="arcGrid"></div>
  <p class="arc-empty" id="arcEmpty" hidden>No articles match that search.</p>
</div>'''

    body = f'''{nav(cfg, active="read")}
<section class="section arc-section"><div class="wrap">
  <div class="section-head reveal"><h2>All articles</h2><p>{total} pieces — search by title, tag, or place, or browse by category.</p></div>
  <div class="arc-layout">{sidebar}{main}</div>
</div></section>
{footer(cfg, present_cats)}'''

    init_js = ("window.PW_POSTS=" + json.dumps(posts_js) + ";"
               "window.PW_CATS=" + json.dumps(cat_colors) + ";"
               "window.PW_QUOTES=" + json.dumps(quotes) + ";"
               "pwArchiveInitV2();")

    jsonld = json.dumps({"@context": "https://schema.org", "@type": "CollectionPage",
                         "name": f'All articles — {cfg["brandName"]}', "url": cfg["domain"] + "/articles.html"})
    head = page_head(cfg, f'All articles — {cfg["brandName"]}',
                     "Browse the full archive by category, tag, or search.",
                     cfg["domain"] + "/articles.html", jsonld)
    (PUBLIC / "articles.html").write_text(head + body + page_tail(cfg, init_js), encoding="utf-8")


def build_article(cfg, p, present_cats):
    col = cfg["categories"].get(p["category"], "#999")
    header = nav(cfg)

    reactions = f'''<div class="reactions">
  <button class="like-btn" id="likeBtn" aria-label="Like this article">{HEART}<span id="likeCount">0</span></button>
  <span class="views">{EYE}<span id="viewCount"></span></span></div>'''

    mode_match = re.search(r"<h2>\s*Practical Guide[^<]*</h2>", p["html"], re.IGNORECASE)
    if mode_match:
        story_html = p["html"][:mode_match.start()]
        guide_html = p["html"][mode_match.start():]
        mode_switch = ('<div class="mode-switch" role="tablist">'
                       '<button class="mode-btn active" role="tab" aria-selected="true" onclick="pwSetMode(this,\'story\')">Story</button>'
                       '<button class="mode-btn" role="tab" aria-selected="false" onclick="pwSetMode(this,\'guide\')">Practical Guide</button>'
                       '</div>')
        prose_inner = (f'{mode_switch}'
                       f'<div class="mode-panel" data-mode="story">{story_html}</div>'
                       f'<div class="mode-panel" data-mode="guide" hidden>{guide_html}</div>')
    else:
        prose_inner = p["html"]

    body = f'''{header}
<article>
  <div class="article a-head">
    <a href="index.html#read" class="back">← All articles</a>
    <div class="kicker mono"><span class="dot" style="background:{col}"></span>{p['category']} · {p['minutes']} min read · {p['display_date']}</div>
    <h1>{p['title']}</h1>
    <p class="dek">{p['excerpt']}</p>
  </div>
  <div class="article">
    <div class="prose">{prose_inner}<div class="endmark">〜</div></div>
    {reactions}
  </div>
</article>
<div class="more"><div class="mono">Enjoyed this?</div>
  <p style="margin:0 0 20px;color:var(--muted)">Grab the RSS feed and new pieces show up the moment they're published — no account, no email required.</p>
  <a href="feed.xml"><button class="btn btn-grad">Subscribe via RSS</button></a></div>
{footer(cfg, present_cats)}'''

    jsonld = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": p["title"],
                         "datePublished": p["iso"], "author": {"@type": "Person", "name": cfg["author"]["name"]},
                         "publisher": {"@type": "Organization", "name": f'{cfg["brandName"]}'}})
    head = page_head(cfg, f'{p["title"]} — {cfg["brandName"]}',
                     p["excerpt"], f'{cfg["domain"]}/{p["slug"]}.html', jsonld)
    (PUBLIC / f'{p["slug"]}.html').write_text(head + body + page_tail(cfg, f'pwInitArticle("{p["slug"]}");'), encoding="utf-8")


def build_rss(cfg, posts):
    def rfc822(dt):
        return dt.strftime("%a, %d %b %Y 12:00:00 +0000")

    items = "".join(f'''  <item>
    <title>{html.escape(p["title"])}</title>
    <link>{cfg['domain']}/{p['slug']}.html</link>
    <guid isPermaLink="true">{cfg['domain']}/{p['slug']}.html</guid>
    <pubDate>{rfc822(p['dt'])}</pubDate>
    <category>{html.escape(p['category'])}</category>
    <description>{html.escape(p['excerpt'])}</description>
  </item>
''' for p in posts)

    feed = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>{html.escape(cfg['brandName'])}</title>
  <link>{cfg['domain']}/</link>
  <description>{html.escape(cfg['hero']['lede'])}</description>
  <language>en-us</language>
  <atom:link xmlns:atom="http://www.w3.org/2005/Atom" href="{cfg['domain']}/feed.xml" rel="self" type="application/rss+xml"/>
{items}</channel></rss>'''
    (PUBLIC / "feed.xml").write_text(feed, encoding="utf-8")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    global STYLES, APP_JS
    cfg = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    STYLES = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
    APP_JS = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")

    posts = []
    for md_file in sorted((ROOT / "content").glob("*.md")):
        meta, body = parse_md(md_file.read_text(encoding="utf-8"))
        dt = datetime.strptime(meta["date"], "%Y-%m-%d")
        words = len(re.findall(r"\w+", body))
        tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
        img_match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", body)
        posts.append({
            "title": meta["title"], "slug": meta.get("slug", md_file.stem),
            "category": meta.get("category", "Career"), "excerpt": meta.get("excerpt", ""),
            "tags": tags, "thumb": img_match.group(1) if img_match else None,
            "featured": str(meta.get("featured", "")).lower() == "true",
            "iso": meta["date"], "dt": dt,
            "display_date": dt.strftime("%d %b %Y"), "card_date": dt.strftime("%b %Y"),
            "minutes": max(1, round(words / 200)), "html": md_to_html(body),
        })
    posts.sort(key=lambda p: p["dt"], reverse=True)
    present_cats = [c for c in cfg["categories"] if any(p["category"] == c for p in posts)]

    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir()

    images_dir = ROOT / "assets" / "images"
    if images_dir.exists():
        shutil.copytree(images_dir, PUBLIC / "assets" / "images")

    build_index(cfg, posts, present_cats)
    build_archive(cfg, posts, present_cats)
    build_rss(cfg, posts)
    for p in posts:
        build_article(cfg, p, present_cats)

    # robots + sitemap
    (PUBLIC / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {cfg['domain']}/sitemap.xml\n", encoding="utf-8")
    urls = [f"  <url><loc>{cfg['domain']}/</loc><priority>1.0</priority></url>",
            f"  <url><loc>{cfg['domain']}/articles.html</loc><priority>0.9</priority></url>"]
    urls += [f"  <url><loc>{cfg['domain']}/{p['slug']}.html</loc><priority>0.8</priority></url>" for p in posts]
    (PUBLIC / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls) + "\n</urlset>\n")

    print(f"✓ Built {len(posts)} articles → {PUBLIC}/")
    for p in posts:
        flag = " (featured)" if p["featured"] else ""
        print(f"  · {p['slug']}.html  [{p['category']}]{flag}")
    print("\nUpload everything in public/ to your S3 bucket.")


if __name__ == "__main__":
    main()
