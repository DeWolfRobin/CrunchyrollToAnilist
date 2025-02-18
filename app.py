import os
import time
import logging
import requests
import cloudscraper
from dotenv import load_dotenv
from requests_toolbelt.utils import dump

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

# Create a cloudscraper instance to handle requests
scraper = cloudscraper.create_scraper()


def log_request_response(response):
    """Log detailed request and response information."""
    data = dump.dump_all(response)
    logger.debug(data.decode("utf-8"))


def make_request(method, url, headers=None, json_data=None, retries=3, delay=60*5):
    """
    Make an HTTP request using the given method and handle retries for rate limiting.
    """
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
    headers = {
        "Authorization": f"Bearer {CRUNCHYROLL_ACCESS_TOKEN}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Referer": "https://www.crunchyroll.com/",
        "Origin": "https://www.crunchyroll.com",
        "Sec-Fetch-Site": "same-origin"
    }
    response = make_request("get", CRUNCHYROLL_HISTORY_URL, headers=headers)
    if response:
        return response.json().get("data", [])
    else:
        logger.error("Failed to fetch Crunchyroll history.")
        return []


# Cache to store search results and avoid duplicate API calls
anime_search_cache = {}


def search_anilist_anime(title, retries=3, delay=60*5):
    if title in anime_search_cache:
        return anime_search_cache[title]

    query = """
    query ($search: String) {
      Media (search: $search, type: ANIME) {
        id
        title {
          romaji
          english
        }
      }
    }
    """
    variables = {"search": title}
    headers = {
        "Authorization": f"Bearer {ANILIST_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://anilist.co/",
        "Origin": "https://anilist.co",
    }
    response = make_request(
        "post", ANILIST_GRAPHQL_URL, headers=headers, json_data={"query": query, "variables": variables},
        retries=retries, delay=delay
    )
    if response:
        data = response.json()
        if "data" in data and "Media" in data["data"]:
            anime = data["data"]["Media"]
            anime_search_cache[title] = anime
            return anime
        else:
            logger.error(
                f"Unexpected response format for title '{title}': {data}")
    return None


def get_anilist_progress(anime_ids, retries=3, delay=60*5):
    """
    Fetch current progress for multiple anime in one request.
    """
    if not anime_ids:
        return {}

    query = """
    query ($ids: [Int]) {
      Page {
        mediaList(mediaId_in: $ids, type: ANIME) {
          mediaId
          progress
        }
      }
    }
    """
    variables = {"ids": anime_ids}
    headers = {
        "Authorization": f"Bearer {ANILIST_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://anilist.co/",
        "Origin": "https://anilist.co",
    }
    response = make_request(
        "post", ANILIST_GRAPHQL_URL, headers=headers, json_data={"query": query, "variables": variables},
        retries=retries, delay=delay
    )
    if response:
        data = response.json()
        if "data" in data and "Page" in data["data"]:
            return {entry["mediaId"]: entry["progress"] for entry in data["data"]["Page"]["mediaList"]}
        else:
            logger.error(
                f"Unexpected response format in get_anilist_progress: {data}")
    return {}


def batch_update_anilist_progress(anime_updates, retries=3, delay=60*5):
    """
    Batch update AniList progress for multiple anime entries.
    """
    if not anime_updates:
        logger.info("No updates needed. All anime are already up to date.")
        return

    mutation = """
    mutation batchUpdate($updates: [MediaListEntryUpdateInput]) {
      UpdateMediaListEntries(entries: $updates) {
        id
        progress
      }
    }
    """
    updates = [{"mediaId": media_id, "progress": progress}
               for media_id, progress in anime_updates.items()]
    variables = {"updates": updates}
    headers = {
        "Authorization": f"Bearer {ANILIST_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://anilist.co/",
        "Origin": "https://anilist.co",
    }
    response = make_request(
        "post", ANILIST_GRAPHQL_URL, headers=headers, json_data={"query": mutation, "variables": variables},
        retries=retries, delay=delay
    )
    if response:
        logger.info(
            f"Successfully updated {len(anime_updates)} anime entries.")
        return response.json()
    return None


def sync_crunchyroll_to_anilist():
    history = get_crunchyroll_history()
    if not history:
        logger.error("No history data found.")
        return

    anime_updates = {}
    anime_ids = set()

    for entry in history:
        metadata = entry.get("panel", {}).get("episode_metadata", {})
        title = metadata.get("series_title")
        episode = metadata.get("episode_number")
        fully_watched = entry.get("fully_watched", False)

        if not title or episode is None:
            logger.warning(f"Skipping entry due to missing data: {entry}")
            continue

        if not fully_watched:
            logger.info(
                f"Skipping '{title}' Episode {episode} (Not fully watched).")
            continue

        anime = search_anilist_anime(title)
        if anime:
            anime_id = anime.get("id")
            if anime_id:
                anime_ids.add(anime_id)
                # If multiple entries exist for the same anime, use the highest episode number.
                anime_updates[anime_id] = max(
                    anime_updates.get(anime_id, 0), episode)

    # Fetch current progress in one batch call
    current_progress = get_anilist_progress(list(anime_ids))

    # Filter out unnecessary updates
    updates_to_apply = {
        anime_id: ep for anime_id, ep in anime_updates.items()
        if current_progress.get(anime_id, 0) < ep
    }
    batch_update_anilist_progress(updates_to_apply)


if __name__ == '__main__':
    sync_crunchyroll_to_anilist()
