import argparse
import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime

from urllib.parse import urljoin

import aiofiles
import aiohttp
from bs4 import BeautifulSoup


HN_ROOT = "https://news.ycombinator.com/"
HN_ITEM = "https://news.ycombinator.com/item?id={item_id}"


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Story:
    item_id: str
    title: str
    story_url: str
    comments_url: str


def now_utc() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def setup_logger() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def safe_name(text: str, max_len: int = 80) -> str:
    text = (text or "").strip().lower()
    out = []
    for ch in text:
        if ch.isalnum():
            out.append(ch)
        elif ch in {" ", "_", "-"}:
            out.append("_")
    name = "".join(out).strip("_")
    if not name:
        name = "untitled"
    return name[:max_len]


def normalize_url(url: str) -> str | None:
    url = (url or "").strip()
    if not url:
        return None
    if url.startswith("#") or url.startswith("mailto:") or url.startswith("javascript:"):
        return None
    return url


async def fetch_bytes(session: aiohttp.ClientSession, url: str) -> bytes:
    async with session.get(url, allow_redirects=True) as resp:
        resp.raise_for_status()
        return await resp.read()


async def write_bytes(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiofiles.open(path, "wb") as f:
        await f.write(data)


def parse_top_30(root_html: str) -> list[Story]:
    soup = BeautifulSoup(root_html, "html.parser")
    rows = soup.select("tr.athing")
    stories: list[Story] = []

    for row in rows[:30]:
        item_id = row.get("id")
        a = row.select_one("span.titleline a")
        if not item_id or not a:
            continue

        title = a.get_text(strip=True) or "untitled"
        href = (a.get("href") or "").strip()
        story_url = urljoin(HN_ROOT, href)
        comments_url = HN_ITEM.format(item_id=item_id)

        stories.append(
            Story(
                item_id=item_id,
                title=title,
                story_url=story_url,
                comments_url=comments_url,
            )
        )

    return stories


def extract_links_from_comments(hn_item_html: str) -> list[str]:
    soup = BeautifulSoup(hn_item_html, "html.parser")
    links: list[str] = []

    for a in soup.select(".commtext a"):
        href = normalize_url(a.get("href", ""))
        if not href:
            continue
        abs_url = urljoin(HN_ROOT, href)
        if abs_url.startswith("http://") or abs_url.startswith("https://"):
            links.append(abs_url)

    uniq: list[str] = []
    seen: set[str] = set()
    for u in links:
        if u not in seen:
            uniq.append(u)
            seen.add(u)
    return uniq


async def download_story_bundle(
    session: aiohttp.ClientSession,
    out_dir: str,
    story: Story,
) -> None:
    folder = f"{story.item_id}_{safe_name(story.title)}"
    story_dir = os.path.join(out_dir, folder)
    os.makedirs(story_dir, exist_ok=True)

    hn_html_bytes = await fetch_bytes(session, story.comments_url)
    await write_bytes(os.path.join(story_dir, "hn_comments.html"), hn_html_bytes)

    try:
        hn_html = hn_html_bytes.decode("utf-8")
    except UnicodeDecodeError:
        hn_html = hn_html_bytes.decode("utf-8", errors="ignore")

    comment_links = extract_links_from_comments(hn_html)

    story_bytes = await fetch_bytes(session, story.story_url)
    await write_bytes(os.path.join(story_dir, "story.html"), story_bytes)

    tasks = []
    for idx, url in enumerate(comment_links, start=1):
        filename = f"comment_link_{idx:03d}.html"
        path = os.path.join(story_dir, filename)

        async def _dl(u: str, p: str) -> None:
            data = await fetch_bytes(session, u)
            await write_bytes(p, data)

        tasks.append(asyncio.create_task(_dl(url, path)))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    logger.info(
        "saved item=%s links=%s -> %s",
        story.item_id,
        len(comment_links),
        story_dir,
    )


async def crawl(out_dir: str, interval: int) -> None:
    os.makedirs(out_dir, exist_ok=True)
    seen_ids: set[str] = set()

    timeout = aiohttp.ClientTimeout(total=30)
    headers = {"User-Agent": "ycrawler/1.0 (aiohttp)"}

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        while True:
            try:
                root_html = await fetch_bytes(session, HN_ROOT)
                root_text = root_html.decode("utf-8", errors="ignore")
                top = parse_top_30(root_text)

                new = [s for s in top if s.item_id not in seen_ids]
                for s in new:
                    seen_ids.add(s.item_id)

                if new:
                    await asyncio.gather(
                        *(
                            asyncio.create_task(
                                download_story_bundle(session, out_dir, s)
                            )
                            for s in new
                        ),
                        return_exceptions=True,
                    )
                else:
                    logger.info("no new stories in top-30")

            except Exception:
                logger.exception("ERROR during crawl iteration")

            await asyncio.sleep(interval)


def main() -> None:
    setup_logger()

    parser = argparse.ArgumentParser(
        description="Async YCombinator News crawler (top-30 + new items)."
    )
    parser.add_argument(
        "--out",
        default="data",
        help="Output directory (default: data)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Polling interval seconds (default: 30)",
    )
    args = parser.parse_args()

    asyncio.run(crawl(args.out, args.interval))


if __name__ == "__main__":
    main()