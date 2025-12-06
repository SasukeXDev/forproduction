from tmdbv3api import TMDb, Movie, TV
# tmdb_poster_fetcher.py
import re
import requests
from difflib import SequenceMatcher
from typing import Optional, Tuple, List, Dict

TMDB_API_KEY = "68be78e728be4e86e934df1591d26c5b"  # <-- put your key here
TMDB_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
FALLBACK_IMAGE = "https://cdn-icons-png.flaticon.com/512/565/565547.png"
REQUEST_TIMEOUT = 6


def clean_title(raw: str) -> str:
    """Remove bracketed content, codecs, resolutions, tags etc for better search."""
    s = re.sub(r'\[.*?\]|\(.*?\)', ' ', raw)            # remove brackets/parentheses content
    s = re.sub(r'\b(720p|1080p|480p|WEB-DL|HDRip|HEVC|x264|x265|10bit|NF|WEB|BluRay|BRRip)\b', ' ', s, flags=re.I)
    s = re.sub(r'\b(Dual Audio|Hindi|English|ORG|HE-AAC|AAC)\b', ' ', s, flags=re.I)
    s = re.sub(r'[^a-zA-Z0-9\s]', ' ', s)               # remove symbols
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def extract_info(raw_title: str) -> Tuple[str, Optional[int], Optional[int], Optional[str]]:
    """
    Return (clean_title, year, season_number, forced_type)
    forced_type in {"movie","tv"} or None
    """
    year = None
    season = None
    forced_type = None

    # extract year
    y = re.search(r'\b(19|20)\d{2}\b', raw_title)
    if y:
        try:
            year = int(y.group())
        except:
            year = None

    # extract season: match like "S02", "S2", "Season 2", "season2", "S05V1" (we pick the S05 part)
    s = re.search(r'\b[Ss](\d{1,2})\b', raw_title) or re.search(r'[Ss]eason[\s:_-]*(\d{1,2})', raw_title, re.I)
    if s:
        try:
            season = int(s.group(1))
        except:
            season = None

    low = raw_title.lower()
    if "(movie)" in low or " (movie)" in low:
        forced_type = "movie"
    elif "(tv)" in low or "(series)" in low or " (tv)" in low:
        forced_type = "tv"

    cleaned = clean_title(raw_title)

    return cleaned, year, season, forced_type


def tmdb_search_movie(query: str, year: Optional[int] = None) -> List[Dict]:
    """Use TMDb search/movie endpoint (returns JSON list of results)."""
    params = {"api_key": TMDB_API_KEY, "query": query, "page": 1, "include_adult": False}
    if year:
        params["year"] = year
    try:
        r = requests.get(f"{TMDB_BASE}/search/movie", params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception:
        return []


def tmdb_search_tv(query: str, first_air_year: Optional[int] = None) -> List[Dict]:
    """Use TMDb search/tv endpoint (returns JSON list of results)."""
    params = {"api_key": TMDB_API_KEY, "query": query, "page": 1}
    if first_air_year:
        params["first_air_date_year"] = first_air_year
    try:
        r = requests.get(f"{TMDB_BASE}/search/tv", params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception:
        return []


def tmdb_get_season(tv_id: int, season_number: int) -> Optional[Dict]:
    """Official TMDb season endpoint: /tv/{id}/season/{season_number}"""
    params = {"api_key": TMDB_API_KEY, "language": "en-US"}
    try:
        r = requests.get(f"{TMDB_BASE}/tv/{tv_id}/season/{season_number}", params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def score_result(item: Dict, search_title: str, search_year: Optional[int]) -> float:
    """
    Compute a score for a TMDb result JSON object.
    Factors:
      - fuzzy title similarity (SequenceMatcher ratio)
      - year match (+boost)
      - popularity boost
      - vote_count as tie-breaker
    """
    # title can be 'title' (movie) or 'name' (tv)
    item_title = (item.get("title") or item.get("name") or "").strip()
    if not item_title:
        return -999.0

    # fuzzy similarity (0..1) scaled
    sim = SequenceMatcher(None, search_title.lower(), item_title.lower()).ratio()

    score = sim * 100.0  # base

    # year match
    item_year = None
    rd = item.get("release_date") or item.get("first_air_date")
    if isinstance(rd, str) and len(rd) >= 4:
        try:
            item_year = int(rd[:4])
        except:
            item_year = None

    if search_year and item_year and search_year == item_year:
        score += 40.0

    # popularity and vote_count (they are floats/ints) — scale down to avoid overwhelming similarity
    pop = item.get("popularity") or 0
    votes = item.get("vote_count") or 0
    # normalize/pop weighting
    score += float(pop) * 0.5
    score += (min(votes, 10000) / 1000.0)  # small bump for higher vote_count

    return score


def pick_best(results: List[Dict], search_title: str, search_year: Optional[int]) -> Optional[Dict]:
    """Return best-scoring result dict or None."""
    if not results:
        return None
    best = None
    best_score = -1.0
    for it in results:
        # ensure item is dict with expected keys
        if not isinstance(it, dict):
            continue
        s = score_result(it, search_title, search_year)
        if s > best_score:
            best_score = s
            best = it
    return best


def fetch_poster(raw_title: str) -> str:
    """
    Main public function.
    Returns poster URL for Movie, TV show or specific TV season (if season present).
    Flow:
      1. Extract cleaned title, year, season, forced_type
      2. If forced movie: search movie first
      3. If forced tv: search tv first (and fetch season poster if season specified)
      4. If no forced type: try movie search then tv search (season handling included)
      5. Fallback to generic icon
    """
    cleaned, year, season, forced = extract_info(raw_title)
    # protection: if cleaned empty fallback to raw
    if not cleaned:
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', raw_title).strip()

    # 1) If user forced movie
    if forced == "movie":
        movies = tmdb_search_movie(cleaned, year)
        best_movie = pick_best(movies, cleaned, year)
        if best_movie and best_movie.get("poster_path"):
            return IMAGE_BASE + best_movie["poster_path"]

    # 2) If user forced tv
    if forced == "tv":
        shows = tmdb_search_tv(cleaned, year)
        best_show = pick_best(shows, cleaned, year)
        if best_show:
            tv_id = best_show.get("id")
            # season poster if requested
            if season and isinstance(tv_id, int):
                season_data = tmdb_get_season(tv_id, season)
                if season_data and season_data.get("poster_path"):
                    return IMAGE_BASE + season_data["poster_path"]
            # fallback to show poster
            if best_show.get("poster_path"):
                return IMAGE_BASE + best_show["poster_path"]

    # 3) Auto-detect: Movie first
    movies = tmdb_search_movie(cleaned, year)
    best_movie = pick_best(movies, cleaned, year)
    if best_movie and best_movie.get("poster_path"):
        return IMAGE_BASE + best_movie["poster_path"]

    # 4) Auto-detect: TV
    shows = tmdb_search_tv(cleaned, year)
    best_show = pick_best(shows, cleaned, year)
    if best_show:
        tv_id = best_show.get("id")
        if season and isinstance(tv_id, int):
            season_data = tmdb_get_season(tv_id, season)
            if season_data and season_data.get("poster_path"):
                return IMAGE_BASE + season_data["poster_path"]
        if best_show.get("poster_path"):
            return IMAGE_BASE + best_show["poster_path"]

    # final fallback
    return FALLBACK_IMAGE

