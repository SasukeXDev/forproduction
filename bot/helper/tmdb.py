from tmdbv3api import TMDb, Movie, TV
import re
import requests

tmdb = TMDb()
tmdb.api_key = "68be78e728be4e86e934df1591d26c5b"
tmdb.language = 'en'


def parse_title_info(raw_title: str):
    """
    Extract clean title, year, and type (movie/tv) from filename/title.
    Example:
      "Animal (2023) (Movie)" → ("Animal", 2023, "movie")
    """
    title = raw_title

    # Extract year
    year_match = re.search(r"(19|20)\d{2}", title)
    year = int(year_match.group()) if year_match else None

    # Detect movie / tv
    type_match = re.search(r"(movie|film|tv|series|season|episode)", title, re.I)
    mtype = type_match.group().lower() if type_match else None
    if mtype in ["film", "movie"]:
        mtype = "movie"
    elif mtype in ["tv", "series", "season", "episode"]:
        mtype = "tv"

    # Clean title
    title = re.sub(r'\(.*?\)|\[.*?\]', '', title)  # remove (…)
    title = re.sub(r'\d{3,4}p|x264|x265|HEVC|HDRip|WEB-DL|Dual Audio|Hindi|English|ORG', '', title, flags=re.I)
    title = re.sub(r'[^a-zA-Z0-9\s]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()

    return title, year, mtype


def best_result(items):
    """
    Select best match based on:
    - vote_count (more popular = more accurate)
    - vote_average (backup)
    """
    if not items:
        return None
    return sorted(items, key=lambda x: (x.vote_count, x.vote_average), reverse=True)[0]


def fetch_poster(title: str) -> str:
    """
    Fetch the most accurate poster using title + year + type.
    """
    clean_title, year, mtype = parse_title_info(title)
    movie = Movie()
    tv = TV()

    try:
        results = []

        # SEARCH PRIORITY 1: exact match with year
        if year:
            if mtype in [None, "movie"]:
                results = movie.search(clean_title)
                results = [r for r in results if r.release_date and str(year) in r.release_date]

            if mtype == "tv":
                results = tv.search(clean_title)
                results = [r for r in results if r.first_air_date and str(year) in r.first_air_date]

            if results:
                best = best_result(results)
                if best and best.poster_path:
                    return f"https://image.tmdb.org/t/p/w500{best.poster_path}"

        # SEARCH PRIORITY 2: title only (wider match)
        if mtype in [None, "movie"]:
            results = movie.search(clean_title)
        elif mtype == "tv":
            results = tv.search(clean_title)

        if results:
            best = best_result(results)
            if best and best.poster_path:
                return f"https://image.tmdb.org/t/p/w500{best.poster_path}"

        # Fallback: try both if type unknown
        if not mtype:
            results = movie.search(clean_title) + tv.search(clean_title)
            best = best_result(results)
            if best and best.poster_path:
                return f"https://image.tmdb.org/t/p/w500{best.poster_path}"

    except Exception as e:
        pass

    # FINAL fallback
    return "https://cdn-icons-png.flaticon.com/512/565/565547.png"

