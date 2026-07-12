#!/usr/bin/env python3
"""
Mirror a small static site locally.

Usage example:
    python scripts/mirror_site.py https://experience.slap-apps.de/en --output ./scraped
"""

from __future__ import annotations

import argparse
import logging
import os
import re
from collections import deque
from typing import Deque, Dict, Iterable, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin, urlparse, urldefrag

REQUEST_TIMEOUT = 20.0
VALID_HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
LOG = logging.getLogger("mirror-site")


def sanitize_rel_path(path: str, query: str) -> str:
    if path.endswith("/"):
        path = path + "index.html"
    else:
        name, ext = os.path.splitext(path)
        if not ext:
            path = path + "/index.html"

    rel = path.lstrip("/")
    if not rel:
        rel = "index.html"

    if query:
        safe_q = quote_plus(query, safe="")
        base, ext = os.path.splitext(rel)
        rel = f"{base}__{safe_q}{ext or ''}"

    rel = re.sub(r"[<>:\"|?*]", "_", rel)
    return rel


def build_local_path(base_dir: str, netloc: str, rel: str) -> str:
    full = os.path.join(base_dir, netloc, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    return full


def parse_srcset(value: str) -> Iterable[tuple[str, str]]:
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        parts = token.split()
        url_part = parts[0]
        suffix = ""
        if len(parts) > 1:
            suffix = " " + " ".join(parts[1:])
        yield url_part, suffix


def should_download(parsed, base_netloc: str, base_path: str, limit_path: bool) -> bool:
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc != base_netloc:
        return False
    if not limit_path:
        return True
    if base_path in {"/", ""}:
        return True
    if parsed.path == base_path or parsed.path.startswith(base_path + "/"):
        return True
    return False


def compute_local_paths(
    url: str, base_dir: str, base_netloc: str
) -> str:
    parsed = urlparse(url)
    rel = sanitize_rel_path(parsed.path or "/", parsed.query)
    return build_local_path(base_dir, base_netloc, rel)


def rewrite_attribute(
    tag,
    attr: str,
    page_url: str,
    current_local: str,
    base_dir: str,
    base_netloc: str,
    queue: Deque[Tuple[str, int]],
    visited: Dict[str, bool],
    base_path: str,
    limit_path: bool,
    current_depth: int,
    max_depth: int,
) -> None:
    raw = tag.get(attr)
    if not raw:
        return
    if attr == "srcset":
        parts = []
        for asset_url, suffix in parse_srcset(raw):
            new_url = rewrite_single_asset(
                asset_url,
                page_url,
                current_local,
                base_dir,
                base_netloc,
                queue,
                visited,
                base_path,
                limit_path,
                current_depth,
                max_depth,
            )
            parts.append(new_url + suffix if new_url else asset_url + suffix)
        if parts:
            tag[attr] = ", ".join(parts)
        return

    new_url = rewrite_single_asset(
        raw,
        page_url,
        current_local,
        base_dir,
        base_netloc,
        queue,
        visited,
        base_path,
        limit_path,
        current_depth,
        max_depth,
    )
    if new_url:
        tag[attr] = new_url


def rewrite_single_asset(
    raw_url: str,
    page_url: str,
    current_local: str,
    base_dir: str,
    base_netloc: str,
    queue: Deque[Tuple[str, int]],
    visited: Dict[str, bool],
    base_path: str,
    limit_path: bool,
    current_depth: int,
    max_depth: int,
) -> Optional[str]:
    raw_url = raw_url.strip()
    if raw_url.lower().startswith("data:"):
        return None
    abs_url = urljoin(page_url, raw_url)
    abs_url, _ = urldefrag(abs_url)
    parsed = urlparse(abs_url)
    if not should_download(parsed, base_netloc, base_path, limit_path):
        return None

    next_depth = current_depth + (1 if limit_path else 0)
    if abs_url not in visited:
        if not limit_path or next_depth <= max_depth:
            queue.append((abs_url, next_depth))

    local_target = compute_local_paths(abs_url, base_dir, base_netloc)
    rel = os.path.relpath(local_target, os.path.dirname(current_local))
    return rel.replace(os.sep, "/")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mirror a single static site locally.")
    parser.add_argument("url", help="Root URL to scrape (must match domain)")
    parser.add_argument(
        "--output", "-o", default="mirrored_site", help="Output directory for mirrored files"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="How deep to follow internal links (default: 3)",
    )
    args = parser.parse_args()

    base_parsed = urlparse(args.url)
    if base_parsed.scheme not in {"http", "https"}:
        raise SystemExit("URL must use http or https")
    base_netloc = base_parsed.netloc
    base_path = base_parsed.path.rstrip("/") or "/"

    session = requests.Session()
    session.headers.update({"User-Agent": "mirror-site/1.0 (local)"})

    queue: Deque[Tuple[str, int]] = deque([(args.url, 0)])
    visited: Dict[str, bool] = {}

    while queue:
        url, depth = queue.popleft()
        if url in visited:
            continue
        visited[url] = True
        if depth > args.max_depth:
            continue

        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except Exception as exc:
            LOG.warning("Failed to download %s: %s", url, exc)
            continue

        content_type = resp.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        is_html = content_type in VALID_HTML_CONTENT_TYPES

        local_path = compute_local_paths(url, args.output, base_netloc)

        if is_html:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag_name, attr, limit in [
                ("a", "href", True),
                ("link", "href", False),
                ("img", "src", False),
                ("img", "srcset", False),
                ("script", "src", False),
                ("source", "src", False),
                ("source", "srcset", False),
                ("video", "poster", False),
                ("iframe", "src", False),
            ]:
                for tag in soup.find_all(tag_name):
                    rewrite_attribute(
                        tag,
                        attr,
                        url,
                        local_path,
                        args.output,
                        base_netloc,
                        queue,
                        visited,
                        base_path,
                        limit,
                        depth,
                        args.max_depth,
                    )
            rendered = soup.prettify()
            with open(local_path, "w", encoding="utf-8", errors="ignore") as fh:
                fh.write(rendered)
            LOG.info("Saved HTML %s", local_path)
        else:
            with open(local_path, "wb") as fh:
                fh.write(resp.content)
            LOG.info("Saved asset %s", local_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
