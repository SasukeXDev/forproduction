
"""
tmdb_poster_fetcher.py

Usage:
    from tmdb_poster_fetcher import get_poster_for_title
    poster = get_poster_for_title("Stranger Things S04 (2016) (Tv)")
"""

import re
import math
import requests
from difflib import SequenceMatcher
from urllib.parse import quote_plus

# ---------- CONFIG ----------
TMDB_API_KEY = "68be78e728be4e86e934df1591d26c5b"   # <-- PUT YOUR KEY HERE
TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
FALLBACK_POSTER = "https://cdn-icons-png.flaticon.com/512/565/565547.png"
TIMEOUT = 6  # seconds for HTTP requests

# ---------- HELPERS ----------

def clean_and_extract(raw_title: str):
    """
    Parse filename-like raw_title to extract:
      - clean_title: stripped human title
      - year: int or None
      - season: int or None
      - forced_type: "movie" / "tv" / None
    Example:
      "Stranger Things S04 (2016) (Tv)" -> ("Stranger Things", 2016, 4, "tv")
    """
    if not raw_title:
        return None, None, None, None

    s = raw_title.strip()

    # forced type
    forced_type = None
    low = s.lower()
    if "(movie)" in low or " movie" in low and low.endswith(")"):
        forced_type = "movie"
    if "(tv)" in low or "(series)" in low or " tv" in low:
        forced_type = "tv"

    # year
    year_match = re.search(r"\b(19|20)\d{2}\b", s)
    year = int(year_match.group()) if year_match else None

    # season detection: S02, S2, Season 2, season02
    season = None
    s_match = re.search(r"(?:season\s*|s)(\d{1,3})", s, flags=re.I)
    if s_match:
        try:
            season = int(s_match.group(1))
        except:
            season = None

    # Remove bracketed parts and common noise (resolutions, codecs etc.)
    # Keep letters, numbers and spaces
    cleaned = re.sub(r"\[.*?\]|\(.*?\)", " ", s)             # remove (...) and [...]
    cleaned = re.sub(r"\b(720p|1080p|480p|4k|2160p|HD|WEB-?DL|WEBRIP|HDRip|BLURAY|BRRip|x264|x265|HEVC|10bit|Dual Audio|Hindi|English|ORG|NF)\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"[^A-Za-z0-9\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # If cleaned is empty fallback to raw_title stripped
    if not cleaned:
        cleaned = re.sub(r"\s+", " ", raw_title).strip()

    return cleaned, year, season, forced_type


def tmdb_get(path: str, params: dict):
    """
    Helper to call TMDb REST endpoints. Returns parsed JSON or None
    """
    url = f"{TMDB_BASE}{path}"
    params = params.copy() if params else {}
    params["api_key"] = TMDB_API_KEY
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def similarity(a: str, b: str) -> float:
    """Normalized similarity (0..1) using SequenceMatcher"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def score_result(item: dict, search_title: str, search_year: int):
    """
    Score a result dict (movie or tv) to get best match.
    Uses:
     - title similarity (major)
     - year match (bonus)
     - popularity & vote_count (boost)
    Accepts both TMDb /search responses and some tmdbv3api shapes if converted to dict.
    """
    # title fields: "title" (movie) or "name" (tv)
    title = item.get("title") or item.get("name") or ""
    title_sim = similarity(search_title, title)

    # year extraction
    r_year = None
    rdate = item.get("release_date") or item.get("first_air_date") or ""
    if isinstance(rdate, str) and len(rdate) >= 4:
        try:
            r_year = int(rdate[:4])
        except:
            r_year = None

    year_bonus = 0
    if search_year and r_year and search_year == r_year:
        year_bonus = 0.35  # 35% boost

    # popularity/vote_count normalized
    pop = item.get("popularity") or 0.0
    vote_count = item.get("vote_count") or 0

    # scale popularity/vote_count to small contribution
    pop_score = math.log1p(float(pop)) / 10.0   # small scale
    vote_score = math.log1p(float(vote_count)) / 20.0

    # final combined score
    # base: similarity weighted heavily
    score = (title_sim * 0.6) + year_bonus + pop_score + vote_score
    return score


def choose_best(results: list, search_title: str, search_year: int):
    """
    Returns the best item (dict) from results list using scoring; returns None if no valid items.
    Each result expected as dict from TMDb search results.
    """
    if not results:
        return None

    best = None
    best_score = -999.0
    for r in results:
        if not isinstance(r, dict):
            # TMDB search returns dicts; if some library returns objects convert to dict
            try:
                r = dict(r)
            except:
                continue

        # ensure r has at least a title/name
        if not (r.get("title") or r.get("name")):
            continue

        s = score_result(r, search_title, search_year)
        if s > best_score:
            best_score = s
            best = r

    return best


# ---------- SEARCH FUNCTIONS ----------
def search_tmdb_movie(query: str, year: int = None):
    """
    Search TMDb movie endpoint, optionally use 'year' as primary_release_year for filtering
    Returns list of result dicts (may be empty)
    """
    params = {"query": query, "include_adult": "false", "page": 1}
    # TMDb movie search supports 'year' param but recommend 'primary_release_year'
    if year:
        params["year"] = year  # TMDb accepts 'year' for search/movie too
    data = tmdb_get("/search/movie", params)
    return data.get("results", []) if data else []


def search_tmdb_tv(query: str, year: int = None):
    """
    Search TMDb tv endpoint. TMDb doesn't have a formal 'year' query param for TV search,
    so we search and filter by first_air_date year later in scoring.
    """
    params = {"query": query, "page": 1}
    data = tmdb_get("/search/tv", params)
    return data.get("results", []) if data else []


def get_tv_season_poster(tv_id: int, season: int):
    """
    Fetch the season endpoint for a tv show and return season poster (or None)
    Official endpoint: /tv/{tv_id}/season/{season}
    """
    if not tv_id or not season:
        return None
    data = tmdb_get(f"/tv/{tv_id}/season/{season}", {"language": "en-US"})
    if data and data.get("poster_path"):
        return f"{POSTER_BASE}{data['poster_path']}"
    return None


def build_poster_url(path: str):
    if not path:
        return None
    return f"{POSTER_BASE}{path}"


# ---------- MAIN FUNCTION ----------
def get_poster_for_title(raw_title: str) -> str:
    """
    Main entry: given raw_title like "Stranger Things S04 (2016) (Tv)",
    returns best poster URL (season poster if applicable), or fallback.
    """
    try:
        clean_title, year, season, forced_type = clean_and_extract(raw_title)

        # If nothing usable, return fallback
        if not clean_title:
            return FALLBACK_POSTER

        # Prefer exact-type if forced
        if forced_type == "movie":
            movies = search_tmdb_movie(clean_title, year)
            best = choose_best(movies, clean_title, year)
            if best:
                poster = best.get("poster_path")
                return build_poster_url(poster) or FALLBACK_POSTER

            return FALLBACK_POSTER

        if forced_type == "tv":
            shows = search_tmdb_tv(clean_title, year)
            best = choose_best(shows, clean_title, year)
            if best:
                # if season requested -> try season endpoint for season poster
                if season:
                    season_poster = get_tv_season_poster(best.get("id"), season)
                    if season_poster:
                        return season_poster
                # fallback to show poster
                poster = best.get("poster_path")
                return build_poster_url(poster) or FALLBACK_POSTER

            return FALLBACK_POSTER

        # No forced type -> try movie first (prefer movies for ambiguous titles)
        movies = search_tmdb_movie(clean_title, year)
        best_movie = choose_best(movies, clean_title, year)
        if best_movie and best_movie.get("poster_path"):
            return build_poster_url(best_movie.get("poster_path"))

        # Try TV
        shows = search_tmdb_tv(clean_title, year)
        best_show = choose_best(shows, clean_title, year)
        if best_show:
            if season:
                season_poster = get_tv_season_poster(best_show.get("id"), season)
                if season_poster:
                    return season_poster
            if best_show.get("poster_path"):
                return build_poster_url(best_show.get("poster_path"))

        # final fallback
        return FALLBACK_POSTER

    except Exception:
        return FALLBACK_POSTER
