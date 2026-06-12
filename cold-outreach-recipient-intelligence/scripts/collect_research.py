#!/usr/bin/env python3
"""Collect YouTube transcripts and Reddit findings for cold outreach research."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError as GoogleHttpError
from youtube_transcript_api import YouTubeTranscriptApi

ROOT = Path(__file__).resolve().parent.parent
YOUTUBE_DIR = ROOT / "research" / "youtube-transcripts"
REDDIT_OUTPUT = ROOT / "research" / "other" / "reddit-findings.md"

REDDIT_USER_AGENT = os.environ.get(
    "REDDIT_USER_AGENT",
    "python:cold-outreach-recipient-intelligence:v1.0 (by /u/research)",
)
REDDIT_DELAY_SECONDS = 1.5
REDDIT_SESSION = requests.Session()
REDDIT_SESSION.headers.update(
    {
        "User-Agent": REDDIT_USER_AGENT,
        "Accept": "application/json",
    }
)

YOUTUBE_SOURCES = [
    {
        "handle": "exitfive",
        "channel_name": "Exit Five",
        "expert_name": "Dave Gerhardt",
        "expert_slug": "dave-gerhardt",
        "keywords": [
            "cold email",
            "outbound",
            "cold outreach",
            "inbox",
            "sales email",
            "SDR",
        ],
        "limit": 3,
    },
    {
        "handle": "recruitingbrainfood",
        "channel_name": "Recruiting Brainfood",
        "expert_name": "Hung Lee",
        "expert_slug": "hung-lee",
        "keywords": [
            "cold outreach",
            "recruiter message",
            "LinkedIn DM",
            "vendor pitch",
            "outbound recruiting",
        ],
        "limit": 3,
    },
    {
        "handle": "pragmaticengineer",
        "channel_name": "The Pragmatic Engineer",
        "expert_name": "Gergely Orosz",
        "expert_slug": "gergely-orosz",
        "keywords": ["recruiter", "cold email", "outreach", "hiring"],
        "limit": 2,
    },
]

REDDIT_SEARCHES = [
    {
        "query": "cold email worst spam screenshot founder",
        "subreddits": ["sales", "SaaS"],
    },
    {
        "query": "pitch slap pitch slapped vendor ATS HR tech",
        "subreddits": ["sales", "recruiting"],
    },
    {
        "query": "cold email rant roast bad",
        "subreddits": ["sales", "SaaS"],
    },
    {
        "query": "recruiter spam message outreach LinkedIn",
        "subreddits": ["recruitinghell", "recruiting"],
    },
    {
        "query": "reacting cold emails founder CEO VP",
        "subreddits": ["sales", "SaaS"],
    },
]


@dataclass
class VideoCandidate:
    video_id: str
    title: str
    published_at: str
    channel_name: str
    expert_name: str
    expert_slug: str
    relevance_score: int


def slugify(text: str, max_len: int = 60) -> str:
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug[:max_len] or "untitled"


def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def title_matches_keywords(title: str, keywords: list[str]) -> bool:
    lowered = title.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def relevance_score(title: str, keywords: list[str]) -> int:
    lowered = title.lower()
    return sum(1 for keyword in keywords if keyword.lower() in lowered)


def get_youtube_client():
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("ERROR: YOUTUBE_API_KEY environment variable is not set.")
        return None
    return build("youtube", "v3", developerKey=api_key)


def get_channel_id(youtube, handle: str) -> str | None:
    try:
        response = (
            youtube.channels()
            .list(part="id", forHandle=handle)
            .execute()
        )
        items = response.get("items", [])
        if items:
            return items[0]["id"]
    except GoogleHttpError as exc:
        print(f"ERROR: Could not resolve channel @{handle}: {exc}")

    try:
        response = (
            youtube.search()
            .list(part="snippet", q=handle, type="channel", maxResults=1)
            .execute()
        )
        items = response.get("items", [])
        if items:
            return items[0]["snippet"]["channelId"]
    except GoogleHttpError as exc:
        print(f"ERROR: Fallback channel lookup failed for @{handle}: {exc}")

    return None


def search_channel_videos(
    youtube,
    channel_id: str,
    keywords: list[str],
    channel_name: str,
    expert_name: str,
    expert_slug: str,
    limit: int,
) -> list[VideoCandidate]:
    candidates: dict[str, VideoCandidate] = {}

    for keyword in keywords:
        try:
            response = (
                youtube.search()
                .list(
                    part="snippet",
                    channelId=channel_id,
                    q=keyword,
                    type="video",
                    order="relevance",
                    maxResults=10,
                )
                .execute()
            )
        except GoogleHttpError as exc:
            print(f"ERROR: YouTube search failed for '{keyword}' on {channel_name}: {exc}")
            continue

        items = response.get("items", [])
        if not items:
            print(f"LOG: No YouTube results for query '{keyword}' on {channel_name}")
            continue

        for item in items:
            snippet = item["snippet"]
            title = snippet["title"]
            video_id = item["id"]["videoId"]

            if not title_matches_keywords(title, keywords):
                continue

            score = relevance_score(title, keywords)
            existing = candidates.get(video_id)
            if existing is None or score > existing.relevance_score:
                candidates[video_id] = VideoCandidate(
                    video_id=video_id,
                    title=title,
                    published_at=snippet.get("publishedAt", "Unknown"),
                    channel_name=channel_name,
                    expert_name=expert_name,
                    expert_slug=expert_slug,
                    relevance_score=score,
                )

    ranked = sorted(
        candidates.values(),
        key=lambda video: (-video.relevance_score, video.published_at),
    )
    return ranked[:limit]


def fetch_transcript_entries(video_id: str) -> list[dict[str, Any]] | None:
    try:
        fetched = YouTubeTranscriptApi().fetch(video_id)
        return [
            {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
            for snippet in fetched
        ]
    except Exception:
        return None


def format_transcript_with_timestamps(entries: list[dict[str, Any]], interval: int = 150) -> str:
    if not entries:
        return "_No transcript content._\n"

    lines: list[str] = []
    chunk_start = entries[0]["start"]
    chunk_text: list[str] = []

    for entry in entries:
        start = entry["start"]
        if start - chunk_start >= interval and chunk_text:
            lines.append(f"**[{format_timestamp(chunk_start)}]**")
            lines.append(" ".join(chunk_text))
            lines.append("")
            chunk_start = start
            chunk_text = []

        chunk_text.append(entry["text"].strip())

    if chunk_text:
        lines.append(f"**[{format_timestamp(chunk_start)}]**")
        lines.append(" ".join(chunk_text))
        lines.append("")

    return "\n".join(lines)


def save_transcript(video: VideoCandidate) -> bool:
    entries = fetch_transcript_entries(video.video_id)
    if not entries:
        print(f"SKIP: {video.title} — transcript unavailable")
        return False

    publish_date = video.published_at
    if publish_date != "Unknown":
        try:
            publish_date = datetime.fromisoformat(
                publish_date.replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")
        except ValueError:
            publish_date = video.published_at

    title_slug = slugify(video.title)
    filename = f"{video.expert_slug}-{title_slug}.md"
    output_path = YOUTUBE_DIR / filename

    header = (
        f"# {video.title}\n"
        f"Channel: {video.channel_name}\n"
        f"URL: https://youtube.com/watch?v={video.video_id}\n"
        f"Date: {publish_date}\n"
        f"Expert: {video.expert_name}\n"
    )
    body = format_transcript_with_timestamps(entries)
    output_path.write_text(f"{header}\n{body}", encoding="utf-8")
    print(f"SAVED: {output_path.name}")
    return True


def collect_youtube_transcripts() -> int:
    youtube = get_youtube_client()
    if youtube is None:
        return 0

    YOUTUBE_DIR.mkdir(parents=True, exist_ok=True)
    saved_count = 0

    for source in YOUTUBE_SOURCES:
        print(f"\n--- {source['channel_name']} ({source['expert_name']}) ---")
        channel_id = get_channel_id(youtube, source["handle"])
        if not channel_id:
            print(f"ERROR: Could not find channel ID for @{source['handle']}")
            continue

        videos = search_channel_videos(
            youtube=youtube,
            channel_id=channel_id,
            keywords=source["keywords"],
            channel_name=source["channel_name"],
            expert_name=source["expert_name"],
            expert_slug=source["expert_slug"],
            limit=source["limit"],
        )

        if not videos:
            print(
                f"LOG: No matching videos found for {source['channel_name']} "
                f"with keywords {source['keywords']}"
            )
            continue

        for video in videos:
            if save_transcript(video):
                saved_count += 1

    return saved_count


def reddit_request(url: str) -> dict[str, Any] | None:
    for attempt in range(2):
        try:
            response = REDDIT_SESSION.get(url, timeout=20)
            if response.status_code == 429:
                print(f"RETRY: Reddit rate limited for {url}")
                time.sleep(5)
                continue

            content_type = response.headers.get("Content-Type", "")
            if response.status_code != 200 or "application/json" not in content_type:
                raise requests.HTTPError(
                    f"HTTP {response.status_code} ({content_type or 'unknown content type'})"
                )

            return response.json()
        except (requests.RequestException, json.JSONDecodeError, ValueError) as exc:
            if attempt == 0:
                print(f"RETRY: Reddit request failed for {url} ({exc})")
                time.sleep(2)
            else:
                print(f"SKIP: Reddit request failed for {url} ({exc})")
                return None

    return None


def fetch_reddit_posts(query: str, subreddits: list[str]) -> list[dict[str, Any]]:
    posts_by_id: dict[str, dict[str, Any]] = {}

    for subreddit in subreddits:
        encoded_query = quote(query)
        url = (
            f"https://www.reddit.com/r/{subreddit}/search.json"
            f"?q={encoded_query}&restrict_sr=1&sort=relevance&limit=10"
        )
        payload = reddit_request(url)
        time.sleep(REDDIT_DELAY_SECONDS)

        if not payload:
            continue

        children = payload.get("data", {}).get("children", [])
        for child in children:
            data = child.get("data", {})
            post_id = data.get("id")
            if not post_id:
                continue

            permalink = data.get("permalink", "")
            post_url = f"https://www.reddit.com{permalink}" if permalink else data.get("url", "")

            posts_by_id[post_id] = {
                "id": post_id,
                "title": data.get("title", "").strip(),
                "url": post_url,
                "subreddit": data.get("subreddit", subreddit),
                "score": data.get("score", 0),
            }

    ranked_posts = sorted(posts_by_id.values(), key=lambda post: post["score"], reverse=True)
    return ranked_posts[:10]


def fetch_top_comments(subreddit: str, post_id: str, limit: int = 3) -> list[str]:
    url = (
        f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
        f"?sort=top&limit={limit}"
    )
    payload = reddit_request(url)
    time.sleep(REDDIT_DELAY_SECONDS)

    if not payload or len(payload) < 2:
        return []

    comments: list[str] = []
    children = payload[1].get("data", {}).get("children", [])

    for child in children:
        if child.get("kind") != "t1":
            continue
        body = child.get("data", {}).get("body", "").strip()
        if body and body not in ("[deleted]", "[removed]"):
            comments.append(re.sub(r"\s+", " ", body))
        if len(comments) >= limit:
            break

    return comments


def format_reddit_markdown(results: list[tuple[str, list[dict[str, Any]]]]) -> str:
    lines = [
        "# Reddit Findings",
        "",
        "Recipient-side cold outreach sentiment collected via Reddit public search.",
        "",
    ]

    for query, posts in results:
        lines.append(f"## {query}")
        lines.append("")

        if not posts:
            lines.append("_No posts found for this search._")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        for post in posts:
            comments = fetch_top_comments(post["subreddit"], post["id"])
            lines.append(f"### Post: {post['title']}")
            lines.append(f"Subreddit: r/{post['subreddit']}")
            lines.append(f"URL: {post['url']}")
            lines.append(f"Upvotes: {post['score']}")
            lines.append("")
            lines.append("**Top Comments:**")

            if comments:
                for index, comment in enumerate(comments, start=1):
                    lines.append(f"{index}. {comment}")
            else:
                lines.append("1. _No comments available._")

            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def collect_reddit_findings() -> bool:
    results: list[tuple[str, list[dict[str, Any]]]] = []

    for search in REDDIT_SEARCHES:
        print(f"\n--- Reddit search: {search['query']} ---")
        posts = fetch_reddit_posts(search["query"], search["subreddits"])
        print(f"Found {len(posts)} posts")
        results.append((search["query"], posts))

    total_posts = sum(len(posts) for _, posts in results)
    if total_posts == 0:
        print(
            "WARN: No Reddit posts collected; leaving existing "
            f"{REDDIT_OUTPUT.name} unchanged"
        )
        return False

    markdown = format_reddit_markdown(results)
    REDDIT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REDDIT_OUTPUT.write_text(markdown, encoding="utf-8")
    print(f"\nSAVED: {REDDIT_OUTPUT}")
    return True


def main() -> int:
    print("Collecting YouTube transcripts...")
    youtube_saved = collect_youtube_transcripts()
    print(f"\nYouTube transcripts saved: {youtube_saved}")

    print("\nCollecting Reddit findings...")
    collect_reddit_findings()

    return 0


if __name__ == "__main__":
    sys.exit(main())
