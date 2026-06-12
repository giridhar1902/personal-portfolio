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
import praw
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
YOUTUBE_DIR = ROOT / "research" / "youtube-transcripts"
REDDIT_OUTPUT = ROOT / "research" / "other" / "reddit-findings.md"

# PRAW Reddit client
reddit = praw.Reddit(
    client_id=os.environ.get("REDDIT_CLIENT_ID"),
    client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
    user_agent=os.environ.get("REDDIT_USER_AGENT")
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

# Reddit searches configuration removed in favor of search_queries in collect_reddit_findings()


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


def collect_reddit_findings() -> bool:
    search_queries = [
        ("cold email worst spam screenshot founder", ["sales", "SaaS"]),
        ("pitch slap vendor ATS HR tech", ["sales", "recruiting"]),
        ("cold email rant roast bad", ["sales", "SaaS"]),
        ("recruiter spam message outreach LinkedIn", ["recruitinghell", "recruiting"]),
        ("reacting cold emails founder CEO VP", ["sales", "SaaS"]),
    ]

    lines = [
        "# Reddit Findings",
        "",
        "Recipient-side cold outreach sentiment collected via Reddit public search using the PRAW API.",
        "",
    ]

    total_posts_found = 0

    for query, subreddits in search_queries:
        lines.append(f"## Query: {query}")
        lines.append("")

        for subreddit_name in subreddits:
            print(f"Searching r/{subreddit_name} for '{query}'...")
            try:
                subreddit = reddit.subreddit(subreddit_name)
                results = subreddit.search(query, limit=5, sort="relevance")
                
                posts_list = list(results)
                if not posts_list:
                    print(f"  No posts found in r/{subreddit_name}")
                    continue
                
                for post in posts_list:
                    total_posts_found += 1
                    print(f"  Found post: {post.title[:50]}...")
                    
                    full_url = f"https://www.reddit.com{post.permalink}"
                    
                    lines.append(f"### Post: {post.title}")
                    lines.append(f"Subreddit: r/{post.subreddit.display_name}")
                    lines.append(f"URL: {full_url}")
                    lines.append(f"Upvotes: {post.score}")
                    lines.append("")
                    lines.append("**Top Comments:**")
                    
                    post.comment_sort = "top"
                    try:
                        post.comments.replace_more(limit=0)
                        comments = []
                        for comment in post.comments:
                            if len(comments) >= 3:
                                break
                            body = getattr(comment, "body", "").strip()
                            if body and body not in ("[deleted]", "[removed]"):
                                cleaned = re.sub(r"\s+", " ", body)
                                comments.append(cleaned)
                        
                        if comments:
                            for idx, comment in enumerate(comments, start=1):
                                lines.append(f"{idx}. {comment}")
                        else:
                            lines.append("1. _No comments available._")
                    except Exception as comm_exc:
                        print(f"  Failed to fetch comments for post {post.id}: {comm_exc}")
                        lines.append("1. _Failed to load comments._")
                    
                    lines.append("")
                    lines.append("---")
                    lines.append("")
                    
            except Exception as search_exc:
                print(f"ERROR: Search failed on r/{subreddit_name} for '{query}': {search_exc}")
                continue

    if total_posts_found == 0:
        print("WARN: No Reddit posts collected; leaving existing file unchanged")
        return False

    markdown_content = "\n".join(lines).rstrip() + "\n"
    REDDIT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REDDIT_OUTPUT.write_text(markdown_content, encoding="utf-8")
    print(f"\nSAVED: {REDDIT_OUTPUT}")
    return True


def main() -> int:
    print("\nCollecting Reddit findings...")
    collect_reddit_findings()

    return 0


if __name__ == "__main__":
    sys.exit(main())
