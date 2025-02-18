import os
import time
import logging
import json
import requests
import cloudscraper
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Load environment variables
load_dotenv()
CRUNCHYROLL_ACCESS_TOKEN = os.getenv("CRUNCHYROLL_ACCESS_TOKEN")
ANILIST_ACCESS_TOKEN = os.getenv("ANILIST_ACCESS_TOKEN")
CRUNCHYROLL_USER_ID = os.getenv("CRUNCHYROLL_USER_ID")

# API Endpoints
CRUNCHYROLL_HISTORY_URL = (
    f"https://www.crunchyroll.com/content/v2/{CRUNCHYROLL_USER_ID}/watch-history"
    "?page_size=1000&preferred_audio_language=ja-JP&locale=en-US"
)
ANILIST_GRAPHQL_URL = "https://graphql.anilist.co/"

# File to cache Crunchyroll history
CR_HISTORY_FILE = "crunchyroll_history.json"

# Create a cloudscraper instance
scraper = cloudscraper.create_scraper()


def make_request(method, url, headers=None, json_data=None, retries=3, delay=300):
    """Make an HTTP request with retries."""
    for attempt in range(1, retries + 1):
        try:
            if method.lower() == "get":
                response = scraper.get(url, headers=headers)
            elif method.lower() == "post":
                response = scraper.post(url, headers=headers, json=json_data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if response.status_code == 429:
                logger.warning(
                    f"Rate limit hit (HTTP 429). Retrying in {delay} seconds... (Attempt {attempt}/{retries})"
                )
                time.sleep(delay)
                continue
            elif not (200 <= response.status_code < 300):
                logger.error(
                    f"HTTP {response.status_code} Error: {response.text}")
                return None

            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception: {e}")
            return None

    logger.error("Failed after multiple retries.")
    return None


def get_crunchyroll_history():
    """
    Retrieve Crunchyroll watch history.
    Use a cached file if available; otherwise, fetch from the API.
    """
    if os.path.exists(CR_HISTORY_FILE):
        with open(CR_HISTORY_FILE, "r") as f:
            cached_data = json.load(f)
        return cached_data.get("data", [])

    logger.info("Fetching Crunchyroll history from API")
    headers = {
        "Authorization": f"Bearer {CRUNCHYROLL_ACCESS_TOKEN}",
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.crunchyroll.com/",
        "Origin": "https://www.crunchyroll.com",
        "Sec-Fetch-Site": "same-origin"
    }
    response = make_request("get", CRUNCHYROLL_HISTORY_URL, headers=headers)
    if response:
        json_data = response.json()
        with open(CR_HISTORY_FILE, "w") as f:
            json.dump(json_data, f, indent=4)
        return json_data.get("data", [])

    logger.error("Failed to fetch Crunchyroll history.")
    return []


def get_anilist_media_and_progress(series_list, retries=3, delay=300):
    """
    Given a list of series (each with 'series_title' and 'episode_number'),
    perform a single GraphQL query to fetch AniList media info and current progress.
    Returns a dict mapping each alias (media0, media1, ...) to media data.
    """
    query_parts = []
    variables = {}
    for i, series in enumerate(series_list):
        alias = f"media{i}"
        var_name = f"title{i}"
        query_parts.append(f"""
        {alias}: Media(search: ${var_name}, type: ANIME) {{
            id
            title {{
                romaji
                english
            }}
            mediaListEntry {{
                progress
            }}
        }}
        """)
        variables[var_name] = series["series_title"]

    query_vars = ", ".join([f"${var}: String!" for var in variables])
    query_body = "\n".join(query_parts)
    query = f"query ({query_vars}) {{\n{query_body}\n}}"

    headers = {
        "Authorization": f"Bearer {ANILIST_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://anilist.co/",
        "Origin": "https://anilist.co",
    }
    response = make_request(
        "post",
        ANILIST_GRAPHQL_URL,
        headers=headers,
        json_data={"query": query, "variables": variables},
        retries=retries,
        delay=delay
    )
    if response:
        data = response.json()
        if "data" in data:
            return data["data"]
        logger.error(f"Unexpected response format: {data}")
    return {}


def batch_update_anilist_progress(anime_updates, retries=3, delay=60*5):
    """
    Batch update AniList progress for multiple anime entries using GraphQL aliasing.
    Each update is performed using the SaveMediaListEntry mutation.
    """
    if not anime_updates:
        logger.info("No updates needed. All anime are already up to date.")
        return

    query_parts = []
    variables = {}
    for i, (media_id, progress) in enumerate(anime_updates.items()):
        alias = f"update{i}"
        var_media_id = f"mediaId{i}"
        var_progress = f"progress{i}"
        query_parts.append(
            f"""{alias}: SaveMediaListEntry(mediaId: ${var_media_id}, progress: ${var_progress}) {{
    id
    progress
}}"""
        )
        variables[var_media_id] = media_id
        variables[var_progress] = progress

    # Declare all variables as Int! (mediaId and progress are both integers)
    var_declarations = ", ".join([f"${key}: Int!" for key in variables])
    query_body = "\n".join(query_parts)
    query = f"mutation ({var_declarations}) {{\n{query_body}\n}}"

    headers = {
        "Authorization": f"Bearer {ANILIST_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://anilist.co/",
        "Origin": "https://anilist.co",
    }
    response = make_request(
        "post",
        ANILIST_GRAPHQL_URL,
        headers=headers,
        json_data={"query": query, "variables": variables},
        retries=retries,
        delay=delay
    )
    if response:
        logger.info(
            f"Successfully updated {len(anime_updates)} anime entries.")
        return response.json()
    return None


def get_distinct_series_latest_completed(history):
    """
    From the Crunchyroll history, return a list of distinct series with their latest fully watched episode.
    If the highest-numbered episode is incomplete, the function checks previous episodes.
    """
    series_entries = {}
    for entry in history:
        metadata = entry.get("panel", {}).get("episode_metadata", {})
        title = metadata.get("series_title")
        episode = metadata.get("episode_number")
        if not title or episode is None:
            continue
        series_entries.setdefault(title, []).append(entry)

    distinct_series = []
    for title, entries in series_entries.items():
        sorted_entries = sorted(
            entries,
            key=lambda e: e.get("panel", {}).get(
                "episode_metadata", {}).get("episode_number", 0),
            reverse=True
        )
        latest_completed = next(
            (entry for entry in sorted_entries if entry.get(
                "fully_watched", False)), None
        )
        if latest_completed:
            episode_num = latest_completed["panel"]["episode_metadata"]["episode_number"]
            distinct_series.append({
                "series_title": title,
                "episode_number": episode_num,
                "entry": latest_completed
            })
        else:
            logger.warning(
                f"No fully watched episode found for series: {title}")

    return distinct_series


def sync_crunchyroll_to_anilist_combined():
    """
    Fetch Crunchyroll history, compare each series' latest fully watched episode with AniList progress,
    and update AniList if the Crunchyroll progress is higher.
    """
    history = get_crunchyroll_history()
    if not history:
        logger.error("No Crunchyroll history data found.")
        return

    distinct_series = get_distinct_series_latest_completed(history)
    logger.info("Distinct series with latest fully watched episode:")
    for series in distinct_series:
        logger.info(
            f"{series['series_title']}: Episode {series['episode_number']}")

    anilist_data = get_anilist_media_and_progress(distinct_series)
    updates_to_apply = {}
    for i, series in enumerate(distinct_series):
        alias = f"media{i}"
        media = anilist_data.get(alias)
        if media:
            anime_id = media.get("id")
            current_progress = (media.get("mediaListEntry")
                                or {}).get("progress", 0)
            crunchyroll_episode = series["episode_number"]
            if crunchyroll_episode > current_progress:
                updates_to_apply[anime_id] = crunchyroll_episode
                logger.info(
                    f"Will update {series['series_title']} (ID: {anime_id}): "
                    f"Crunchyroll episode {crunchyroll_episode} vs AniList {current_progress}"
                )
            else:
                logger.info(
                    f"No update needed for {series['series_title']} (ID: {anime_id}): "
                    f"Crunchyroll episode {crunchyroll_episode} vs AniList {current_progress}"
                )
        else:
            logger.warning(
                f"No AniList entry found for title: {series['series_title']}")

    if updates_to_apply:
        result = batch_update_anilist_progress(updates_to_apply)
        logger.info(f"Update result: {result}")
    else:
        logger.info("No updates needed; AniList progress is already current.")


if __name__ == '__main__':
    sync_crunchyroll_to_anilist_combined()
