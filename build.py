#!/usr/bin/env python3
"""
Mindful Yen — drip publishing builder.

Reads manifest.json, regenerates:
  - blog/index.html  (lists only published articles with publish_date <= today, newest first)
  - sitemap.xml      (only published article URLs + static pages)

Run daily via GitHub Actions or manually:  python build.py
"""

import json
import os
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
MANIFEST = ROOT / "manifest.json"
BLOG_INDEX = ROOT / "blog" / "index.html"
SITEMAP = ROOT / "sitemap.xml"

STATIC_PAGES = [
    {"loc": "/", "priority": "1.0", "changefreq": "weekly"},
    {"loc": "/about/", "priority": "0.7", "changefreq": "monthly"},
    {"loc": "/blog/", "priority": "0.9", "changefreq": "daily"},
    {"loc": "/portfolio/", "priority": "0.8", "changefreq": "monthly"},
]


def load_manifest():
    with MANIFEST.open(encoding="utf-8") as f:
        return json.load(f)


def published_articles(manifest, today=None):
    """Return list of articles where status == 'published' AND publish_date <= today."""
    today = today or date.today()
    out = []
    for a in manifest["articles"]:
        if a.get("status") != "published":
            continue
        try:
            pub = date.fromisoformat(a["publish_date"])
        except (KeyError, ValueError):
            continue
        if pub <= today:
            out.append(a)
    # newest first
    out.sort(key=lambda x: x["publish_date"], reverse=True)
    return out


def auto_excerpt(slug, length=300):
    """If excerpt missing, pull first <p> from the article HTML."""
    article = ROOT / "blog" / slug / "index.html"
    if not article.exists():
        return ""
    html = article.read_text(encoding="utf-8")
    m = re.search(r"<p>(.*?)</p>", html, re.DOTALL)
    if not m:
        return ""
    text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    if len(text) > length:
        text = text[:length].rsplit(" ", 1)[0] + "&hellip;"
    return text


def render_blog_index(articles, site):
    items = []
    for a in articles:
        excerpt = a.get("excerpt") or auto_excerpt(a["slug"])
        read_min = a.get("read_min", 10)
        items.append(
            f'      <li>\n'
            f'  <div class="meta">{read_min} min read &middot; {site["author"]}</div>\n'
            f'  <h2><a href="/blog/{a["slug"]}/">{a["title"]}</a></h2>\n'
            f'  <p class="excerpt">{excerpt}</p>\n'
            f'  <a class="readmore" href="/blog/{a["slug"]}/">Read more &rarr;</a>\n'
            f'</li>'
        )
    items_html = "".join(items) if items else "      <li><p>New essays coming soon.</p></li>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Blog — {site["title"]}</title>
<meta name="description" content="Essays on kakeibo, the Japanese budget method, and the quiet practice of paying attention to money. Written from Tokyo.">
<link rel="canonical" href="{site["url"]}/blog/">
<meta property="og:title" content="Blog — {site["title"]}">
<meta property="og:description" content="Essays on kakeibo, the Japanese budget method, and the quiet practice of paying attention to money. Written from Tokyo.">
<meta property="og:type" content="website">
<meta property="og:url" content="{site["url"]}/blog/">
<meta property="og:site_name" content="{site["title"]}">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">

</head>
<body>
<header class="site-header">
  <div class="container">
    <a href="/" class="brand">{site["title"]}</a>
    <nav class="nav">
      <a href="/">Home</a>
      <a href="/blog/">Blog</a>
      <a href="/about/">About</a>
      <a href="https://mindfulyen.substack.com">Substack</a>
    </nav>
  </div>
</header>

<section class="article">
  <div class="narrow">
    <header class="article-header">
      <p class="article-kicker">Journal</p>
      <h1 class="article-title">The writing</h1>
      <p class="article-byline">{site["tagline"]}</p>
    </header>
    <ul class="blog-list">
{items_html}
    </ul>
  </div>
</section>
<footer class="site-footer">
  <div class="container">
    <div>&copy; 2026 {site["title"]}</div>
    <nav>
      <a href="/about/">About</a>
      <a href="/blog/">Blog</a>
      <a href="https://mindfulyen.substack.com">Substack</a>
      <a href="https://mindfulyen.etsy.com">Etsy</a>
    </nav>
  </div>
</footer>
</body></html>
"""
    return html


def render_sitemap(articles, site):
    urls = []
    for p in STATIC_PAGES:
        urls.append(
            f'  <url><loc>{site["url"]}{p["loc"]}</loc><changefreq>{p["changefreq"]}</changefreq><priority>{p["priority"]}</priority></url>'
        )
    for a in articles:
        urls.append(
            f'  <url><loc>{site["url"]}/blog/{a["slug"]}/</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>'
        )
    body = "\n".join(urls)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{body}
</urlset>
"""


def main():
    manifest = load_manifest()
    site = manifest["site"]
    articles = published_articles(manifest)
    print(f"[build.py] Today={date.today()}  published_articles={len(articles)}")

    blog_html = render_blog_index(articles, site)
    sitemap_xml = render_sitemap(articles, site)

    BLOG_INDEX.write_text(blog_html, encoding="utf-8", newline="\n")
    SITEMAP.write_text(sitemap_xml, encoding="utf-8", newline="\n")
    print(f"[build.py] wrote {BLOG_INDEX.relative_to(ROOT)}")
    print(f"[build.py] wrote {SITEMAP.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
