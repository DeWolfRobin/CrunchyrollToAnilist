# Crunchyroll to AniList Sync

## Overview

This Python script automatically syncs your watch history from **Crunchyroll** to **AniList**. If you watch anime on Crunchyroll but want to track your progress on AniList, this tool will save you from manual updates!

## Features

- ✅ **Fetches watch history** from Crunchyroll using its API and caches the data locally (in `crunchyroll_history.json`) to reduce unnecessary requests.
- ✅ **Processes watch history** to extract distinct series with the latest fully watched episode (skipping partially watched episodes).
- ✅ **Combined AniList queries:** Uses a single GraphQL query with aliasing to retrieve media info and current progress for multiple series at once.
- ✅ **Batch updates AniList progress:** Updates multiple entries in one request using GraphQL aliasing with the `SaveMediaListEntry` mutation.
- ✅ Stores API tokens securely via a **.env file**.
- ✅ Fully **automated** – just run the script and let it sync your progress.
- ✅ **Virtual environment support** for easy setup.

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/DeWolfRobin/CrunchyrollToAnilist
cd CrunchyrollToAnilist
```

### 2. Set Up a Virtual Environment

It is recommended to use a virtual environment to manage dependencies.

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### 3. Install Dependencies

Ensure you have Python 3 installed, then install the required packages:

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project directory and add your API credentials:

```ini
CRUNCHYROLL_ACCESS_TOKEN=your_crunchyroll_access_token
ANILIST_ACCESS_TOKEN=your_anilist_access_token
CRUNCHYROLL_USER_ID=your_crunchyroll_user_id
```

- **`CRUNCHYROLL_ACCESS_TOKEN`** – Find this in your browser's Developer Tools under `Authorization: Bearer`.
- **`ANILIST_ACCESS_TOKEN`** – Generate this from the [AniList API](https://docs.anilist.co/guide/auth/).
- **`CRUNCHYROLL_USER_ID`** – Extracted from Crunchyroll API requests (e.g., `/content/v2/YOUR_USER_ID/watch-history`).

### 5. Run the Script

```bash
python app.py
```

---

## How It Works

1. **Fetch Crunchyroll History:**  
   The script retrieves your Crunchyroll watch history. If a cached version exists (in `crunchyroll_history.json`), it uses that to avoid excessive API calls.

2. **Process Watch History:**  
   It groups entries by series and determines the latest fully watched episode for each series. If the highest-numbered episode is incomplete, the script looks at previous episodes until it finds one that was fully watched.

3. **Fetch AniList Data in a Single Request:**  
   The script sends a combined GraphQL query (using aliasing) to AniList to retrieve media information (including AniList IDs and titles) along with current progress in one request.

4. **Update AniList Progress:**  
   If the Crunchyroll progress is higher than the AniList progress, the script schedules an update. Batch updates are performed using the `SaveMediaListEntry` mutation via GraphQL aliasing so that multiple updates occur in a single API call.

---

## Troubleshooting

- **Invalid token error:**  
  Ensure your `.env` file contains the correct access tokens. Refresh them if needed.

- **No anime found on AniList:**  
  Some anime titles may differ (e.g., English vs. Romaji). Consider modifying the search logic if necessary.

- **GraphQL errors during update:**  
  The script uses the `SaveMediaListEntry` mutation with aliasing for batch updates. If you encounter errors, verify that the AniList API has not undergone breaking changes.

---

## Contributing

Want to improve the script? Contributions are welcome! Fork the repo, make your changes, and submit a pull request.

---

## License

This project is licensed under the **MIT License**. See `LICENSE` for details.

---

## Contact

💬 Questions? Open an issue on GitHub.

---

Happy syncing!
