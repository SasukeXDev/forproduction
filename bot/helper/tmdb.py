
from tmdbv3api import TMDb, Movie, TV
import requests
import re

TMDB_API_KEY = "68be78e728be4e86e934df1591d26c5b"

tmdb = TMDb()
tmdb.api_key = TMDB_API_KEY
tmdb.language = "en"

movie_api = Movie()
tv_api = TV()


def extract_info(title: str):
    year = None
    season = None

    y = re.search(r"\b(19|20)\d{2}\b", title)
    if y:
        year = int(y.group())

    s = re.search(r"[Ss](\d+)|Season\s*(\d+)", title)
    if s:
        season = int(s.group(1) or s.group(2))

    forced_type = None
    if "(movie)" in title.lower():
        forced_type = "movie"
    elif "(tv)" in title.lower():
        forced_type = "tv"

    clean = re.sub(r"\(.*?\)", "", title)
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    return clean, year, season, forced_type


def tmdb_season_poster(tv_id: int, season: int):
    """
    OFFICIAL TMDb season poster endpoint
    """
    url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US"
    }

    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        if data.get("poster_path"):
            return f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
    except:
        pass

    return None


def best_match(results, search_title, year):
    best = None
    score_best = -1

    for r in results:
        title = getattr(r, "title", None) or getattr(r, "name", "")
        score = r.popularity or 0

        if search_title.lower() in title.lower():
            score += 40

        r_year = None
        if hasattr(r, "release_date") and r.release_date:
            r_year = int(r.release_date[:4])
        elif hasattr(r, "first_air_date") and r.first_air_date:
            r_year = int(r.first_air_date[:4])

        if year and r_year == year:
            score += 30

        if score > score_best:
            score_best = score
            best = r

    return best


def fetch_poster(title: str) -> str:
    clean_title, year, season, forced = extract_info(title)

    # ---------- MOVIE ----------
    if forced != "tv":
        movies = movie_api.search(clean_title)
        best = best_match(movies, clean_title, year)
        if best and best.poster_path:
            return f"https://image.tmdb.org/t/p/w500{best.poster_path}"

    # ---------- TV ----------
    shows = tv_api.search(clean_title)
    best_tv = best_match(shows, clean_title, year)

    if best_tv:
        # ✅ SEASON POSTER (CORRECT WAY)
        if season:
            poster = tmdb_season_poster(best_tv.id, season)
            if poster:
                return poster

        # ✅ TV SHOW POSTER
        if best_tv.poster_path:
            return f"https://image.tmdb.org/t/p/w500{best_tv.poster_path}"

    # ---------- FALLBACK ----------
    return "https://cdn-icons-png.flaticon.com/512/565/565547.png"
