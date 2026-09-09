#!/usr/bin/env python3
"""Generate Hololive JP HASM JSON seed files.

The script always writes PERSON entities for the configured roster. When the
YOUTUBE_API_KEY environment variable is set, it also searches each member's
YouTube channel, imports uploaded videos as FACT entries, stores video metadata
in description_lines, and creates collaboration LINK entries for videos that
mention other roster members.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from common_logger import get_logger

NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://hasm.example/hololive-jp")
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_WATCH_BASE = "https://www.youtube.com/watch?v="


@dataclass(frozen=True)
class Member:
    slug: str
    name: str
    generation: str
    search_query: str
    aliases: tuple[str, ...]
    channel_id: str = ""


HOLOLIVE_JP_MEMBERS: tuple[Member, ...] = (
    Member("tokino_sora", "Tokino Sora", "0th gen", "Tokino Sora hololive official", ("tokino sora", "sora")),
    Member("roboco_san", "Roboco-san", "0th gen", "Roboco-san hololive official", ("roboco", "roboco-san")),
    Member("sakura_miko", "Sakura Miko", "0th gen", "Sakura Miko hololive official", ("sakura miko", "miko")),
    Member("hoshimachi_suisei", "Hoshimachi Suisei", "0th gen", "Hoshimachi Suisei hololive official", ("hoshimachi suisei", "suisei")),
    Member("azki", "AZKi", "0th gen", "AZKi hololive official", ("azki",)),
    Member("aki_rosenthal", "Aki Rosenthal", "1st gen", "Aki Rosenthal hololive official", ("aki rosenthal", "akirose", "aki")),
    Member("akai_haato", "Akai Haato", "1st gen", "Akai Haato Haachama hololive official", ("akai haato", "haachama", "haato")),
    Member("shirakami_fubuki", "Shirakami Fubuki", "1st gen / Gamers", "Shirakami Fubuki hololive official", ("shirakami fubuki", "fubuki", "fbk")),
    Member("natsuiro_matsuri", "Natsuiro Matsuri", "1st gen", "Natsuiro Matsuri hololive official", ("natsuiro matsuri", "matsuri")),
    Member("nakiri_ayame", "Nakiri Ayame", "2nd gen", "Nakiri Ayame hololive official", ("nakiri ayame", "ayame")),
    Member("yuzuki_choco", "Yuzuki Choco", "2nd gen", "Yuzuki Choco hololive official", ("yuzuki choco", "choco")),
    Member("oozora_subaru", "Oozora Subaru", "2nd gen", "Oozora Subaru hololive official", ("oozora subaru", "subaru")),
    Member("ookami_mio", "Ookami Mio", "Gamers", "Ookami Mio hololive official", ("ookami mio", "mio")),
    Member("nekomata_okayu", "Nekomata Okayu", "Gamers", "Nekomata Okayu hololive official", ("nekomata okayu", "okayu")),
    Member("inugami_korone", "Inugami Korone", "Gamers", "Inugami Korone hololive official", ("inugami korone", "korone")),
    Member("usada_pekora", "Usada Pekora", "3rd gen", "Usada Pekora hololive official", ("usada pekora", "pekora")),
    Member("shiranui_flare", "Shiranui Flare", "3rd gen", "Shiranui Flare hololive official", ("shiranui flare", "flare")),
    Member("shirogane_noel", "Shirogane Noel", "3rd gen", "Shirogane Noel hololive official", ("shirogane noel", "noel")),
    Member("houshou_marine", "Houshou Marine", "3rd gen", "Houshou Marine hololive official", ("houshou marine", "marine")),
    Member("amane_kanata", "Amane Kanata", "4th gen", "Amane Kanata hololive official", ("amane kanata", "kanata")),
    Member("tsunomaki_watame", "Tsunomaki Watame", "4th gen", "Tsunomaki Watame hololive official", ("tsunomaki watame", "watame")),
    Member("tokoyami_towa", "Tokoyami Towa", "4th gen", "Tokoyami Towa hololive official", ("tokoyami towa", "towa")),
    Member("himemori_luna", "Himemori Luna", "4th gen", "Himemori Luna hololive official", ("himemori luna", "luna")),
    Member("yukihana_lamy", "Yukihana Lamy", "5th gen", "Yukihana Lamy hololive official", ("yukihana lamy", "lamy")),
    Member("momosuzu_nene", "Momosuzu Nene", "5th gen", "Momosuzu Nene hololive official", ("momosuzu nene", "nene")),
    Member("shishiro_botan", "Shishiro Botan", "5th gen", "Shishiro Botan hololive official", ("shishiro botan", "botan")),
    Member("omaru_polka", "Omaru Polka", "5th gen", "Omaru Polka hololive official", ("omaru polka", "polka")),
    Member("laplus_darknesss", "La+ Darknesss", "holoX", "La+ Darknesss hololive official", ("laplus darknesss", "la+ darknesss", "laplus")),
    Member("takane_lui", "Takane Lui", "holoX", "Takane Lui hololive official", ("takane lui", "lui")),
    Member("hakui_koyori", "Hakui Koyori", "holoX", "Hakui Koyori hololive official", ("hakui koyori", "koyori")),
    Member("kazama_iroha", "Kazama Iroha", "holoX", "Kazama Iroha hololive official", ("kazama iroha", "iroha")),
)

HOLOLIVE_DEV_IS_MEMBERS: tuple[Member, ...] = (
    Member("hiodoshi_ao", "Hiodoshi Ao", "ReGLOSS", "Hiodoshi Ao hololive DEV_IS official", ("hiodoshi ao", "ao")),
    Member("otonose_kanade", "Otonose Kanade", "ReGLOSS", "Otonose Kanade hololive DEV_IS official", ("otonose kanade", "kanade")),
    Member("ichijou_ririka", "Ichijou Ririka", "ReGLOSS", "Ichijou Ririka hololive DEV_IS official", ("ichijou ririka", "ririka")),
    Member("juufuutei_raden", "Juufuutei Raden", "ReGLOSS", "Juufuutei Raden hololive DEV_IS official", ("juufuutei raden", "raden")),
    Member("todoroki_hajime", "Todoroki Hajime", "ReGLOSS", "Todoroki Hajime hololive DEV_IS official", ("todoroki hajime", "hajime")),
    Member("isaki_riona", "Isaki Riona", "FLOW GLOW", "Isaki Riona hololive DEV_IS official", ("isaki riona", "riona")),
    Member("koganei_niko", "Koganei Niko", "FLOW GLOW", "Koganei Niko hololive DEV_IS official", ("koganei niko", "niko")),
    Member("mizumiya_su", "Mizumiya Su", "FLOW GLOW", "Mizumiya Su hololive DEV_IS official", ("mizumiya su", "su")),
    Member("rindo_chihaya", "Rindo Chihaya", "FLOW GLOW", "Rindo Chihaya hololive DEV_IS official", ("rindo chihaya", "chihaya")),
    Member("kikirara_vivi", "Kikirara Vivi", "FLOW GLOW", "Kikirara Vivi hololive DEV_IS official", ("kikirara vivi", "vivi")),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Hololive JP HASM JSON files.")
    parser.add_argument(
        "--output-dir",
        default="data/persons",
        help="Directory to write JSON files into (default: data/persons)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("YOUTUBE_API_KEY", ""),
        help="YouTube Data API key. Defaults to YOUTUBE_API_KEY environment variable.",
    )
    parser.add_argument(
        "--include-dev-is",
        action="store_true",
        help="Also generate hololive DEV_IS members.",
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        default=0,
        help="Maximum videos per channel. Use 0 for all videos (default: 0).",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.1,
        help="Delay between YouTube API calls (default: 0.1).",
    )
    parser.add_argument(
        "--revise-existing",
        action="store_true",
        help="Add collaboration experiences and reciprocal FACTs to existing JSON files.",
    )
    return parser.parse_args()


def entity_id(kind: str, key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{kind}:{key}"))


def output_folder_name(member: Member) -> str:
    return "_".join(part.capitalize() for part in member.slug.split("_"))


def collaboration_experience_id(member: Member) -> str:
    return entity_id("experience", f"{member.slug}:colaboration")


def iso_datetime(value: str) -> str:
    if value.endswith("Z"):
        return f"{value[:-1]}+00:00"
    return value


def youtube_get(api_key: str, endpoint: str, params: dict[str, str | int]) -> dict[str, Any]:
    encoded_params = urllib.parse.urlencode({**params, "key": api_key})
    url = f"{YOUTUBE_API_BASE}/{endpoint}?{encoded_params}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"YouTube API error {exc.code}: {body}") from exc


def search_channel(api_key: str, member: Member) -> str:
    if member.channel_id:
        return member.channel_id
    data = youtube_get(
        api_key,
        "search",
        {
            "part": "snippet",
            "type": "channel",
            "maxResults": 5,
            "q": member.search_query,
        },
    )
    items = data.get("items", [])
    if not items:
        raise RuntimeError(f"No YouTube channel found for {member.name}")
    return str(items[0]["snippet"]["channelId"])


def uploads_playlist_id(api_key: str, channel_id: str) -> str:
    data = youtube_get(
        api_key,
        "channels",
        {"part": "contentDetails", "id": channel_id, "maxResults": 1},
    )
    items = data.get("items", [])
    if not items:
        raise RuntimeError(f"No channel details found for {channel_id}")
    return str(items[0]["contentDetails"]["relatedPlaylists"]["uploads"])


def playlist_video_ids(
    api_key: str,
    playlist_id: str,
    max_videos: int,
    delay_seconds: float,
) -> list[str]:
    video_ids: list[str] = []
    page_token = ""
    while True:
        params: dict[str, str | int] = {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
        }
        if page_token:
            params["pageToken"] = page_token
        data = youtube_get(api_key, "playlistItems", params)
        for item in data.get("items", []):
            video_ids.append(str(item["contentDetails"]["videoId"]))
            if max_videos and len(video_ids) >= max_videos:
                return video_ids
        page_token = str(data.get("nextPageToken", ""))
        if not page_token:
            return video_ids
        time.sleep(delay_seconds)


def batched(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index:index + size]


def video_details(api_key: str, video_ids: list[str], delay_seconds: float) -> list[dict[str, Any]]:
    videos: list[dict[str, Any]] = []
    for batch in batched(video_ids, 50):
        data = youtube_get(
            api_key,
            "videos",
            {"part": "snippet,contentDetails,liveStreamingDetails", "id": ",".join(batch)},
        )
        videos.extend(data.get("items", []))
        time.sleep(delay_seconds)
    return videos


def detect_collaborators(owner: Member, members: tuple[Member, ...], text: str) -> list[Member]:
    normalized = text.lower()
    collaborators: list[Member] = []
    for member in members:
        if member.slug == owner.slug:
            continue
        for alias in member.aliases:
            pattern = rf"(?<![a-z0-9]){re.escape(alias.lower())}(?![a-z0-9])"
            if re.search(pattern, normalized):
                collaborators.append(member)
                break
    return collaborators


def markdown_description(description: str, max_chars: int = 6000) -> str:
    cleaned = description.strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[:max_chars].rstrip()}\n\n[Description truncated by generator.]"


def build_member_payload(
    member: Member,
    all_members: tuple[Member, ...],
    videos: list[dict[str, Any]],
) -> dict[str, Any]:
    person_id = entity_id("person", member.slug)
    experience_id = entity_id("experience", f"{member.slug}:youtube")
    collaboration_id = collaboration_experience_id(member)
    person = {
        "person_id": person_id,
        "person_name": member.name,
        "output_folder_name": output_folder_name(member),
        "person_description_path": f"PERSON/{person_id}/main.md",
        "birthday": "",
        "die": "",
        "link_ids": [],
        "description_lines": [
            "",
            "## Profile",
            f"- organization: hololive JP",
            f"- generation: {member.generation}",
            f"- source_query: {member.search_query}",
        ],
    }
    experiences = [
        {
            "experience_id": experience_id,
            "person_id": person_id,
            "experience_name": f"{member.name} YouTube Activity",
            "experience_description_path": f"EXPERIENCE/{experience_id}/main.md",
            "parent_experience_ids": [],
            "link_ids": [],
            "description_lines": ["", "## Scope", "Videos imported from the member's YouTube uploads playlist."],
        },
        {
            "experience_id": collaboration_id,
            "person_id": person_id,
            "experience_name": f"{member.name}_colaboration",
            "experience_description_path": f"EXPERIENCE/{collaboration_id}/main.md",
            "parent_experience_ids": [experience_id],
            "link_ids": [],
            "description_lines": [
                "",
                "## Scope",
                "Videos featuring this member and one or more other Hololive members.",
            ],
        },
    ]

    facts: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    person_link_ids: list[str] = []
    for video in videos:
        video_id = str(video["id"])
        snippet = video.get("snippet", {})
        title = str(snippet.get("title", f"YouTube video {video_id}"))
        description = str(snippet.get("description", ""))
        published_at = iso_datetime(str(snippet.get("publishedAt", "1970-01-01T00:00:00+00:00")))
        collaborators = detect_collaborators(member, all_members, f"{title}\n{description}")
        collaborator_ids = [entity_id("person", collaborator.slug) for collaborator in collaborators]
        link_ids: list[str] = []

        fact_id = entity_id("fact", f"{member.slug}:youtube:{video_id}")
        if collaborators:
            link_id = entity_id("link", f"{member.slug}:youtube:{video_id}:collaboration")
            link_ids.append(link_id)
            person_link_ids.append(link_id)
            links.append(
                {
                    "link_id": link_id,
                    "link_name": f"Collaboration on {title}",
                    "link_type": "collaboration",
                    "link_description_path": f"LINK/{link_id}/main.md",
                    "related_ids": [person_id, *collaborator_ids, fact_id],
                    "description_lines": [
                        "",
                        "## Detected Participants",
                        *[f"- {collaborator.name}" for collaborator in collaborators],
                        "",
                        "Detected from title and description text. Review manually for false positives.",
                    ],
                }
            )

        experience_ids = [experience_id]
        if collaborators:
            experience_ids.append(collaboration_id)

        facts.append(
            {
                "fact_id": fact_id,
                "fact_name": title,
                "occurred_at": published_at,
                "fact_description_path": f"FACT/{fact_id}/main.md",
                "experience_ids": experience_ids,
                "person_ids": [person_id, *collaborator_ids],
                "link_ids": link_ids,
                "description_lines": [
                    "",
                    "## YouTube Video",
                    f"- video_id: {video_id}",
                    f"- url: {YOUTUBE_WATCH_BASE}{video_id}",
                    f"- channel_title: {snippet.get('channelTitle', '')}",
                    f"- published_at: {published_at}",
                    "",
                    "## Description",
                    markdown_description(description),
                ],
            }
        )

    person["link_ids"] = person_link_ids
    return {"person": person, "experiences": experiences, "facts": facts, "links": links}


def add_collaboration_fact_mirrors(
    payloads: dict[str, dict[str, Any]], members: tuple[Member, ...]
) -> None:
    """Copy each collaboration fact into every participating member's payload."""
    payload_by_person_id = {
        payload["person"]["person_id"]: payload for payload in payloads.values()
    }
    member_by_person_id = {
        entity_id("person", member.slug): member for member in members
    }

    for source_slug, source_payload in payloads.items():
        source_person_id = source_payload["person"]["person_id"]
        for fact in source_payload["facts"]:
            participant_ids = fact.get("person_ids", [])
            if len(participant_ids) < 2:
                continue
            for participant_id in participant_ids:
                if participant_id == source_person_id or participant_id not in payload_by_person_id:
                    continue
                participant = member_by_person_id[participant_id]
                participant_payload = payload_by_person_id[participant_id]
                mirror_id = entity_id(
                    "fact", f"{source_slug}:collaboration:{fact['fact_id']}:{participant.slug}"
                )
                if any(existing["fact_id"] == mirror_id for existing in participant_payload["facts"]):
                    continue
                mirror = dict(fact)
                mirror["fact_id"] = mirror_id
                mirror["fact_description_path"] = f"FACT/{mirror_id}/main.md"
                mirror["experience_ids"] = [collaboration_experience_id(participant)]
                mirror["link_ids"] = []
                mirror["description_lines"] = [
                    *fact.get("description_lines", []),
                    "",
                    f"- mirrored_from: {source_person_id}",
                ]
                participant_payload["facts"].append(mirror)


def revise_existing_payloads(output_dir: Path, members: tuple[Member, ...]) -> int:
    payloads: dict[str, dict[str, Any]] = {}
    for member in members:
        path = output_dir / f"hololive_jp_{member.slug}.json"
        if path.exists():
            payloads[member.slug] = json.loads(path.read_text(encoding="utf-8"))

    for member in members:
        payload = payloads.get(member.slug)
        if payload is None:
            continue
        person_id = payload["person"]["person_id"]
        collaboration_id = collaboration_experience_id(member)
        if not any(exp["experience_id"] == collaboration_id for exp in payload["experiences"]):
            payload["experiences"].append(
                {
                    "experience_id": collaboration_id,
                    "person_id": person_id,
                    "experience_name": f"{member.name}_colaboration",
                    "experience_description_path": f"EXPERIENCE/{collaboration_id}/main.md",
                    "parent_experience_ids": [
                        entity_id("experience", f"{member.slug}:youtube")
                    ],
                    "link_ids": [],
                    "description_lines": [
                        "",
                        "## Scope",
                        "Videos featuring this member and one or more other Hololive members.",
                    ],
                }
            )
        for fact in payload["facts"]:
            if len(fact.get("person_ids", [])) > 1 and collaboration_id not in fact["experience_ids"]:
                fact["experience_ids"].append(collaboration_id)

    add_collaboration_fact_mirrors(payloads, members)
    for member in members:
        payload = payloads.get(member.slug)
        if payload is None:
            continue
        path = output_dir / f"hololive_jp_{member.slug}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(payloads)


def fetch_member_videos(
    api_key: str,
    member: Member,
    max_videos: int,
    delay_seconds: float,
    logger: Any,
) -> list[dict[str, Any]]:
    channel_id = search_channel(api_key, member)
    logger.info("%s channel_id=%s", member.name, channel_id)
    playlist_id = uploads_playlist_id(api_key, channel_id)
    video_ids = playlist_video_ids(api_key, playlist_id, max_videos, delay_seconds)
    logger.info("%s videos discovered=%d", member.name, len(video_ids))
    return video_details(api_key, video_ids, delay_seconds)


def write_payload(output_dir: Path, member: Member, payload: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"hololive_jp_{member.slug}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    logger = get_logger("hololive-jp-generator")
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = (repo_root / args.output_dir).resolve()
    members = HOLOLIVE_JP_MEMBERS
    if args.include_dev_is:
        members = (*members, *HOLOLIVE_DEV_IS_MEMBERS)

    if args.revise_existing:
        revised_count = revise_existing_payloads(output_dir, members)
        logger.info("Revised %d existing Hololive JSON file(s) in %s", revised_count, output_dir)
        return 0

    if not args.api_key:
        logger.warning("YOUTUBE_API_KEY is not set; writing PERSON-only files.")

    payloads: dict[str, dict[str, Any]] = {}
    for member in members:
        logger.info("Generating %s", member.name)
        videos: list[dict[str, Any]] = []
        if args.api_key:
            videos = fetch_member_videos(
                args.api_key,
                member,
                args.max_videos,
                args.delay_seconds,
                logger,
            )
        payloads[member.slug] = build_member_payload(member, members, videos)

    add_collaboration_fact_mirrors(payloads, members)
    for member in members:
        write_payload(output_dir, member, payloads[member.slug])

    logger.info("Wrote %d Hololive JSON file(s) to %s", len(members), output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())