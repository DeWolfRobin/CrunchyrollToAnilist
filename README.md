# Crunchyroll to AniList Sync

## Overview

This Python script automatically syncs your watch history from **Crunchyroll** to **AniList**. If you watch anime on Crunchyroll but want to track your progress on AniList, this tool will save you from manual updates!

## Features

✅ Fetches **watch history** from Crunchyroll using its API.  
✅ Searches for the anime on AniList automatically.  
✅ Updates **episode progress** on AniList.  
✅ Uses a **.env file** to store API tokens securely.  
✅ Fully **automated** – just run the script and it syncs everything.  
✅ **Virtual environment support** for easy setup.

---

## Installation

### **1. Clone the Repository**

```bash
git clone https://github.com/DeWolfRobin/CrunchyrollToAnilist
cd CrunchyrollToAnilist
```

### **2. Set Up a Virtual Environment**

It is recommended to use a virtual environment to manage dependencies.

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### **3. Install Dependencies**

Ensure you have Python 3 installed, then install the required packages:

```bash
pip install -r requirements.txt
```

### **4. Set Up Environment Variables**

Create a `.env` file in the project directory and add your API credentials:

```ini
CRUNCHYROLL_ACCESS_TOKEN=your_crunchyroll_access_token
ANILIST_ACCESS_TOKEN=your_anilist_access_token
CRUNCHYROLL_USER_ID=your_crunchyroll_user_id
```

- **`CRUNCHYROLL_ACCESS_TOKEN`** – Find this in your browser's Developer Tools under `Authorization: Bearer`.
- **`ANILIST_ACCESS_TOKEN`** – Generate this from [AniList API](https://docs.anilist.co/guide/auth/).
- **`CRUNCHYROLL_USER_ID`** – Extracted from Crunchyroll API requests (`/content/v2/YOUR_USER_ID/watch-history`).

### **5. Run the Script**

```bash
python app.py
```

---

## How It Works

1. Fetches **your Crunchyroll watch history**.
2. Extracts **anime titles & episode numbers**.
3. Searches **AniList for the matching anime**.
4. Updates **watch progress on AniList**.
5. Skips **partially watched episodes** (only syncs fully watched ones).

---

## Troubleshooting

❓ **Invalid token error**: Ensure your `.env` file contains the correct access tokens. Refresh them if needed.
❓ **No anime found on AniList**: Some titles may be different (e.g., English vs. Romaji). Consider modifying the search logic.

---

## Contributing

Want to improve the script? Contributions are welcome! Fork the repo, make changes, and submit a pull request.

---

## License

This project is licensed under the **MIT License**. See `LICENSE` for details.

---

## Contact

💬 Questions? Open an issue on GitHub.
