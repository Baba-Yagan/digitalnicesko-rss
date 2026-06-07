#!/usr/bin/env python3
"""Convert digitalnicesko.gov.cz/aktuality to RSS feed."""

import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import formatdate, format_datetime
from html import escape

URL = "https://digitalnicesko.gov.cz/aktuality"
RSS_PATH = "aktuality.rss"


def fetch_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": "aktuality2rss/1.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def extract_articles(html):
    # Try Next.js RSC payload first (it has full JSON data)
    m = re.search(r'"articles":(\[.*?\])', html, re.DOTALL)
    if m:
        articles = json.loads(m.group(1))
        return [
            {
                "title": a["title"],
                "excerpt": a["excerpt"],
                "slug": a["slug"],
                "publishedAt": a["publishedAt"],
            }
            for a in articles
        ]

    # Fallback: parse from HTML structure
    articles = []
    for card in re.finditer(
        r'<a class="css-fzzx90-cardLink" href="(/aktuality/[^"]+)".*?'
        r'<p class="css-pynawr-root">(.*?)</p>.*?'
        r"<h3[^>]*>(.*?)</h3>.*?"
        r'<p class="css-jj61sk-root-excerpt">(.*?)</p>',
        html,
        re.DOTALL,
    ):
        articles.append(
            {
                "title": card.group(3).strip(),
                "excerpt": card.group(4).strip(),
                "slug": card.group(1).replace("/aktuality/", ""),
                "publishedAt": card.group(2).strip(),
            }
        )
    return articles


def czech_date_to_iso(czech_date):
    month_map = {
        "ledna": "01",
        "února": "02",
        "března": "03",
        "dubna": "04",
        "května": "05",
        "června": "06",
        "července": "07",
        "srpna": "08",
        "září": "09",
        "října": "10",
        "listopadu": "11",
        "prosince": "12",
    }
    m = re.match(r"(\d+)\.\s*(\S+)\s*(\d{4})", czech_date)
    if not m:
        return czech_date
    day, month_cz, year = m.group(1), m.group(2), m.group(3)
    month = month_map.get(month_cz.lower())
    if not month:
        return czech_date
    return f"{year}-{month}-{int(day):02d}T00:00:00Z"


def gen_rss(articles):
    rss = ET.Element(
        "rss", version="2.0", attrib={"xmlns:atom": "http://www.w3.org/2005/Atom"}
    )
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Digitální Česko 2.0 – Aktuality"
    ET.SubElement(channel, "link").text = URL
    ET.SubElement(channel, "description").text = "Aktuality z Digitálního Česka 2.0"
    ET.SubElement(channel, "language").text = "cs"
    ET.SubElement(channel, "lastBuildDate").text = formatdate(
        timeval=None, localtime=False, usegmt=True
    )

    atom_link = ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link")
    atom_link.set("href", URL + "/aktuality.rss")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    for a in articles:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = a["title"]
        ET.SubElement(item, "link").text = f"{URL}/{a['slug']}"
        ET.SubElement(item, "guid", isPermaLink="true").text = f"{URL}/{a['slug']}"
        ET.SubElement(item, "description").text = escape(a.get("excerpt", ""))
        pub_date = a.get("publishedAt", "")
        if pub_date.startswith("20"):
            dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            ET.SubElement(item, "pubDate").text = format_datetime(dt, usegmt=True)
        else:
            iso = czech_date_to_iso(pub_date)
            dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            ET.SubElement(item, "pubDate").text = format_datetime(dt, usegmt=True)

    ET.indent(rss, space="  ")
    return ET.tostring(rss, encoding="unicode", xml_declaration=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--fetch":
        html = fetch_html(URL)
        with open("aktuality.html", "w", encoding="utf-8") as f:
            f.write(html)
    else:
        try:
            with open("aktuality.html", "r", encoding="utf-8") as f:
                html = f.read()
        except FileNotFoundError:
            html = fetch_html(URL)
            with open("aktuality.html", "w", encoding="utf-8") as f:
                f.write(html)

    articles = extract_articles(html)
    rss = gen_rss(articles)
    with open(RSS_PATH, "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"Wrote {len(articles)} articles to {RSS_PATH}")


if __name__ == "__main__":
    main()
