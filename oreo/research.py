"""Web research: decide what to search, search DuckDuckGo (no key needed), read the best pages,
and hand the model short, relevant extracts with numbered sources to cite."""

import html
import ipaddress
import re
import socket
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from . import config, lean

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 Safari/605.1.15"}
PAGES = 5            # pages read per question
PAGE_CHARS = 2400    # kept from each page (~600 tokens)
URL = re.compile(r"https?://[^\s<>\"')\]]+")

PLAN = """Today is {date}. Decide if answering the last message needs fresh or factual info from the web \
(news, prices, versions, people, places, events, docs, anything that may have changed or that you might get wrong). \
If yes, reply with 1-3 short search queries, one per line, nothing else. \
If no (chit-chat, writing, maths, code you can do, or the answer is in attached files), reply NONE.

{convo}"""

ANSWER = """Web results fetched just now ({date}). Use them for facts and prefer them over memory. \
Cite sources inline like [1]. If they don't answer it, say so briefly."""


def plan(provider, chat):
    """Ask a cheap model for search queries; [] means no search needed."""
    recent = chat.messages[-5:]
    convo = "\n".join(f"{m['role']}: {lean.stub_files(m['content'])[:400]}" for m in recent)
    if chat.summary:
        convo = f"(earlier) {chat.summary}\n{convo}"
    out = "".join(provider.stream(config.SUMMARY_MODEL, [{"role": "user", "content": PLAN.format(
        date=time.strftime("%d %B %Y"), convo=convo)}], max_tokens=60, temperature=0)).strip()
    if out.upper().startswith("NONE"):
        return []
    return [q.strip(" -•\"'0123456789.") for q in out.splitlines() if q.strip()][:3]


def public(url):
    """Only fetch public sites (a visitor can't make Oreo read the router or this Mac)."""
    try:
        host = urllib.parse.urlsplit(url).hostname
        return all(ipaddress.ip_address(a[4][0]).is_global for a in socket.getaddrinfo(host, None))
    except (OSError, ValueError, TypeError):
        return False


def get(url, limit=2_000_000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=12) as r:
        return r.read(limit).decode(r.headers.get_content_charset() or "utf-8", "replace")


def search(query, n=5):
    """[(title, url, snippet)] from DuckDuckGo's HTML page."""
    page = get("https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query))
    out = []
    for m in re.finditer(r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>',
                         page, re.S):
        href = html.unescape(m[1])
        if "uddg=" in href:
            href = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
        if "duckduckgo.com/y.js" in href:   # ads
            continue
        out.append((text_of(m[2]), href, text_of(m[3])))
        if len(out) == n:
            break
    return out


def text_of(raw):
    raw = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header|form)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<(br|/p|/div|/h\d|/li|/tr|/section|/article)[^>]*>", "\n", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def extract(text, words, limit=PAGE_CHARS):
    """Keep the paragraphs that mention the question's words most, in page order."""
    paras = [p.strip() for p in re.split(r"\n+", text) if len(p.strip()) > 40]
    score = lambda p: sum(w in p.lower() for w in words)
    best = sorted(range(len(paras)), key=lambda i: -score(paras[i]))
    keep, size = set(), 0
    for i in best:
        if size + len(paras[i]) > limit:
            continue
        keep.add(i)
        size += len(paras[i])
    return "\n".join(paras[i] for i in sorted(keep))


def read(url, words):
    try:
        return extract(text_of(get(url)), words) if public(url) else ""
    except Exception:
        return ""


def gather(queries, links, words, step):
    """Search, then read pages in parallel. step(text) reports progress. Returns [{title, url, text}]."""
    found = [(u, u, "") for u in links]
    for q in queries:
        step(f"searching “{q}”")
        try:
            found += search(q)
        except Exception:
            pass
    seen, picks = set(), []
    for title, url, snippet in found:
        key = url.split("#")[0].rstrip("/")
        if key not in seen:
            seen.add(key)
            picks.append({"title": title, "url": url, "snippet": snippet})
    picks = picks[:PAGES + len(links)]
    if picks:
        hosts = list(dict.fromkeys((urllib.parse.urlsplit(p["url"]).hostname or "").removeprefix("www.") for p in picks))
        step("reading " + ", ".join(hosts[:3]) + (f" +{len(hosts) - 3}" if len(hosts) > 3 else ""))
    with ThreadPoolExecutor(8) as pool:
        texts = list(pool.map(lambda p: read(p["url"], words), picks))
    sources = []
    for p, t in zip(picks, texts):
        if t or p["snippet"]:
            sources.append({"title": p["title"] or p["url"], "url": p["url"], "text": t or p["snippet"]})
    return sources


def block(sources):
    """Text appended to the user's message for this one request (not saved in the chat)."""
    parts = [ANSWER.format(date=time.strftime("%d %B %Y"))]
    for i, s in enumerate(sources, 1):
        parts.append(f"[{i}] {s['title']} — {s['url']}\n{s['text']}")
    return "\n\n<web>\n" + "\n\n".join(parts) + "\n</web>"


def keywords(text):
    return [w for w in re.findall(r"[a-z0-9]{3,}", text.lower())
            if w not in {"the", "and", "for", "what", "how", "who", "with", "about", "this", "that", "from", "are", "is"}][:12]
