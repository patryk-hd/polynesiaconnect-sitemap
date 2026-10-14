"""Polynesia Connect — sitemap generator (crawler).

  python3 crawl.py            → docs/sitemap.xml + docs/sitemap-<type>.xml, state.json

Visits www.polynesiaconnect.com like a search engine (polite: 4 parallel requests, ~4/s) and
keeps only pages that load (200), are HTML, are not "noindex" and are their own canonical page.
Empty search pages answer 404 on this site, so they are left out naturally.
Addresses are written exactly as the site links them (accents percent-encoded once).

lastmod = the day a page's title / description / main heading last changed (state.json keeps
a fingerprint per page), so search engines can trust it.
Seeds: the home page, the section pages, the pages already in state.json and extra-seeds.txt.
"""
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "docs"  # served by GitHub Pages
STATE = HERE / "state.json"
HOST = "www.polynesiaconnect.com"
BASE = f"https://{HOST}"
UA = "PolynesiaConnectSitemap/1.0 (+https://www.polynesiaconnect.com)"
MAX_PAGES = 6000
TODAY = dt.date.today().isoformat()

# never crawled: accounts, forms, technical pages, search parameters
SKIP = re.compile(r"^/(api|admin|account|login|logout|checkout|join|joindre|rejoindre|signup|register|connect|"
                  r"write-a-review|devpreview|search_results|search|cart|invoice|password|unsubscribe|"
                  r"filedata|uploads|images|css|js|cdn-cgi|404|pc-sitemap-sync)(/|$)|\.(jpe?g|png|gif|webp|svg|pdf|zip|xml|txt|js|css|ico)$",
                  re.I)
SECTIONS = ["/", "/annonces", "/immobilier-offres", "/evenements-en-cours", "/emploi", "/produits", "/coupons",
            "/blog", "/articles", "/photo-albums", "/videos", "/listing"]

# sitemap file per page type (first matching rule wins)
TYPES = [
    ("evenements", re.compile(r"^/evenements-en-cours/.+")),
    ("emploi", re.compile(r"^/emploi/.+")),
    ("annonces", re.compile(r"^/annonces/.+")),
    ("immobilier", re.compile(r"^/immobilier-offres/.+")),
    ("articles", re.compile(r"^/(blog|articles|produits|coupons|photo-albums|videos|photos)/.+")),
    ("entreprises", re.compile(r"^/[^/]+/[^/]+/[^/]+(/[^/]+)?$")),  # (pays/)commune/catégorie/entreprise
    ("pages", re.compile(r".*")),
]


# content sections (BD post types + about pages): their sub-pages are posts, listed in the sitemap
SECTION_ROOTS = {"annonces", "immobilier-offres", "evenements-en-cours", "emploi", "produits", "coupons", "blog",
                 "articles", "photo-albums", "videos", "about", "vehicules"}
# location × category combination pages (thin duplicates): never listed, never explored
COMBO_ROOT = re.compile(r"^/(french-polynesia|france|(%c3%ae|i|î)les-[^/]*)(/|$)", re.I)
MAX_PAGINATION = 60
# technical / account pages that answer 200 but must not be indexed
NOT_LISTED = re.compile(r"^/(favoris|favoriteswidget\.php|mon-compte|sitemap-generator|discussion|reviews|audio|"
                        r"specialities|account|members?|pays-de-la-loire|pc-sitemap-sync)(/|$)", re.I)
EMPTY = re.compile(r"aucun r(é|&eacute;)sultat|no results found", re.I)


def fetch(path, query=""):
    url = BASE + path + (f"?{query}" if query else "")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                final = urllib.parse.urlsplit(r.geturl())
                ctype = r.headers.get("Content-Type", "")
                body = r.read().decode("utf-8", "replace") if "html" in ctype else ""
                return r.status, final, body
        except urllib.error.HTTPError as e:
            return e.code, None, ""
        except Exception:  # noqa: BLE001 — network hiccup: retry once
            if attempt:
                return 0, None, ""
            time.sleep(3)


def norm(href, current, keep_page=False):
    """(path, query) of an internal link — query kept only for ?page=N when asked — or None."""
    href = html.unescape(href.strip())
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    u = urllib.parse.urlsplit(urllib.parse.urljoin(BASE + current, href))
    if u.scheme not in ("http", "https") or u.netloc.lower() not in (HOST, HOST.replace("www.", "")):
        return None
    path = urllib.parse.quote(urllib.parse.unquote(u.path), safe="/-_.~'!*()")  # one encoding, whatever the link used
    path = re.sub(r"/{2,}", "/", path) or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    path = re.sub(r"%[0-9A-F]{2}", lambda m: m.group(0).lower(), path)
    if SKIP.search(path) or re.search(r"/(connect|writeareview|write-a-review)$", path) or COMBO_ROOT.match(path):
        return None
    page = re.fullmatch(r"page=(\d+)", u.query or "")
    query = f"page={page.group(1)}" if keep_page and page and 1 < int(page.group(1)) <= MAX_PAGINATION else ""
    if u.query and not query and not keep_page:
        pass
    return path, query


def segments(path):
    return [x for x in path.split("/") if x]


def is_hub(path):
    """Pages whose links are explored: home, section pages, categories / cities (one segment)."""
    return len(segments(path)) <= 1


def worth_visiting(path):
    seg = segments(path)
    if len(seg) <= 1:
        return True
    if seg[0] in SECTION_ROOTS:
        return len(seg) == 2
    return len(seg) in (3, 4)  # business profile: commune/catégorie/entreprise, sometimes pays/commune/catégorie/entreprise


def page_info(body):
    head = body[: body.find("</head>") + 7] if "</head>" in body else body[:20000]
    robots = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)', head, re.I)
    canon = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', head, re.I)
    title = re.search(r"<title[^>]*>(.*?)</title>", head, re.S | re.I)
    desc = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)', head, re.I)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S | re.I)
    clean = lambda m: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(m.group(1)))).strip() if m else ""  # noqa: E731
    return {
        "noindex": bool(robots and "noindex" in robots.group(1).lower()),
        "canonical": canon.group(1) if canon else None,
        "profile": '"LocalBusiness"' in body,
        "empty": bool(EMPTY.search(body)),
        "member": "member_profile" in body or '"LocalBusiness"' in body,
        "fingerprint": hashlib.sha1("|".join(clean(x) for x in (title, desc, h1)).encode()).hexdigest()[:16],
        "links": re.findall(r'<a\s[^>]*href=["\']([^"\']+)["\']', body, re.I),
    }


def listed(path, info):
    """Does this (loaded, indexable, self-canonical) page belong in the sitemap?"""
    seg = segments(path)
    if NOT_LISTED.match(path) or (info["empty"] and not info["profile"]):
        return False
    if len(seg) == 1 and info["member"]:  # personal accounts without commune/category (private individuals)
        return False
    return len(seg) <= 1 or seg[0] in SECTION_ROOTS or info["profile"]


def crawl(seeds):
    seen, queue, pages = set(), [], {}

    def push(item):
        if item and item not in seen and (item[1] or worth_visiting(item[0])):
            seen.add(item)
            queue.append(item)

    for s in seeds:
        push((s, "") if isinstance(s, str) else s)
    with ThreadPoolExecutor(max_workers=4) as pool:
        while queue and len(seen) <= MAX_PAGES:
            batch, queue = queue[:40], queue[40:]
            results = pool.map(lambda it: (time.sleep(0.25), fetch(*it))[1], batch)
            for (path, query), (status, final, body) in zip(batch, results):
                if status != 200 or not body or final is None or final.netloc.lower() != HOST:
                    continue
                info = page_info(body)
                links = info.pop("links")
                if is_hub(path):  # explore categories / sections, including their pagination
                    for href in links:
                        push(norm(href, path, keep_page=True))
                if query:  # a ?page=N view: only used to discover links
                    continue
                final_path = (norm(final.path, "/") or (path, ""))[0]
                if final_path != path:  # redirected: record the destination instead
                    push((final_path, ""))
                    continue
                canon = (norm(info["canonical"], path) or (None, ""))[0] if info["canonical"] else path
                if info["noindex"] or (canon and canon != path):
                    push((canon, "") if canon else None)
                    continue
                if listed(path, info):
                    pages[path] = info["fingerprint"]
    return pages, len(seen)


def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    extra = (HERE / "extra-seeds.txt").read_text().split() if (HERE / "extra-seeds.txt").exists() else []
    seeds = SECTIONS + sorted(state) + [x for x in (norm(s, "/") for s in extra) if x]
    t0 = time.time()
    pages, visited = crawl(seeds)
    # lastmod: keep the date while the fingerprint is unchanged
    new_state = {}
    for path, fp in pages.items():
        old = state.get(path)
        new_state[path] = {"fp": fp, "lastmod": old["lastmod"] if old and old["fp"] == fp else TODAY}
    added = sorted(set(new_state) - set(state))
    removed = sorted(set(state) - set(new_state))
    changed = sorted(p for p in new_state if p in state and state[p]["fp"] != new_state[p]["fp"])

    OUT.mkdir(exist_ok=True)
    for f in OUT.glob("sitemap*.xml"):
        f.unlink()
    groups = {}
    for path in sorted(new_state):
        name = next(n for n, rx in TYPES if rx.match(path))
        groups.setdefault(name, []).append(path)
    index = ['<?xml version="1.0" encoding="UTF-8"?>', '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for name, paths in sorted(groups.items()):
        rows = [f"<url><loc>{html.escape(BASE + p)}</loc><lastmod>{new_state[p]['lastmod']}</lastmod></url>" for p in paths]
        (OUT / f"sitemap-{name}.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                                 + "\n".join(rows) + "\n</urlset>\n")
        last = max(new_state[p]["lastmod"] for p in paths)
        index.append(f"<sitemap><loc>{SITEMAP_BASE}/sitemap-{name}.xml</loc><lastmod>{last}</lastmod></sitemap>")
    index.append("</sitemapindex>")
    (OUT / "sitemap.xml").write_text("\n".join(index) + "\n")
    STATE.write_text(json.dumps(new_state, ensure_ascii=False, indent=0, sort_keys=True))
    (HERE / "changes.json").write_text(json.dumps({"date": TODAY, "added": added, "changed": changed, "removed": removed},
                                                  ensure_ascii=False, indent=1))
    print(f"{len(new_state)} pages in the sitemap ({visited} addresses visited, {time.time() - t0:.0f}s) · "
          f"{len(added)} new, {len(changed)} changed, {len(removed)} gone")
    for name, paths in sorted(groups.items()):
        print(f"  sitemap-{name}.xml: {len(paths)}")


SITEMAP_BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://patryk-hd.github.io/polynesiaconnect-sitemap").rstrip("/")

if __name__ == "__main__":
    main()
