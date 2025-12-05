from tmdbv3api import TMDb, Movie, TV
import re
import requests

tmdb = TMDb()
tmdb.api_key = "68be78e728be4e86e934df1591d26c5b"
tmdb.language = 'en'

movie_api = Movie()
tv_api = TV()


def extract_title_info(title: str):
    """
    Extract cleaned_title, year, season_number, and media type (movie/tv)
    """
    # Extract year
    year_match = re.search(r"\b(19|20)\d{2}\b", title)
    year = int(year_match.group()) if year_match else None

    # Extract season number
    season_match = re.search(r"[Ss]eason\s?(\d+)", title) or re.search(r"[Ss](\d+)", title)
    season_number = int(season_match.group(1)) if season_match else None

    # Detect explicit type
    mtype = None
    if "(movie)" in title.lower():
        mtype = "movie"
    elif "(tv)" in title.lower() or "(series)" in title.lower() or "(show)" in title.lower():
        mtype = "tv"

    # Clean title
    cleaned = re.sub(r"\(.*?\)", "", title)     # remove () blocks
    cleaned = re.sub(r"[Ss]eason\s?\d+", "", cleaned)  # remove season text
    cleaned = re.sub(r"[Ss]\d+", "", cleaned)          # remove S01
    cleaned = cleaned.strip()

    return cleaned, year, season_number, mtype


def get_best_match(results, title, year=None):
    """
    Select best match using:
    - exact title similarity
    - year match
    - popularity score
    """
    if not results:
        return None

    title = title.lower()
    best = None
    best_score = -999

    for r in results:
        score = 0

        # Title similarity bonus
        if r.title and title in r.title.lower():
            score += 50

        if r.name and title in r.name.lower():
            score += 50

        # Year match bonus (if year exists)
        if year and hasattr(r, "release_date") and r.release_date:
            if str(year) in r.release_date:
                score += 40

        if year and hasattr(r, "first_air_date") and r.first_air_date:
            if str(year) in r.first_air_date:
                score += 40

        # Popularity score
        if hasattr(r, "popularity"):
            score += r.popularity

        if score > best_score:
            best_score = score
            best = r

    return best


def fetch_tmdb_season_poster(tv_id, season_number):
    """
    Fetch poster for specific TV season
    """
    try:
        season = tv_api.season(tv_id, season_number)
        if season and season.poster_path:
            return f"https://image.tmdb.org/t/p/w500{season.poster_path}"
    except:
        pass
    return None


def fetch_poster(title: str) -> str:
    cleaned_title, year, season_number, forced_type = extract_title_info(title)

    # -------------------------
    # If type is forced as movie
    # -------------------------
    if forced_type == "movie":
        movies = movie_api.search(cleaned_title)
        match = get_best_match(movies, cleaned_title, year)
        if match and match.poster_path:
            return f"https://image.tmdb.org/t/p/w500{match.poster_path}"

    # -------------------------
    # If type is forced as TV
    # -------------------------
    if forced_type == "tv":
        shows = tv_api.search(cleaned_title)
        match = get_best_match(shows, cleaned_title, year)

        if match:
            # If season requested, fetch season poster
            if season_number:
                season_poster = fetch_tmdb_season_poster(match.id, season_number)
                if season_poster:
                    return season_poster

            # Otherwise default TV poster
            if match.poster_path:
                return f"https://image.tmdb.org/t/p/w500{match.poster_path}"

    # -------------------------
    # Auto detect: try movie first
    # -------------------------
    movies = movie_api.search(cleaned_title)
    best_movie = get_best_match(movies, cleaned_title, year)
    if best_movie and best_movie.poster_path:
        return f"https://image.tmdb.org/t/p/w500{best_movie.poster_path}"

    # -------------------------
    # Auto detect: try TV
    # -------------------------
    shows = tv_api.search(cleaned_title)
    best_show = get_best_match(shows, cleaned_title, year)

    if best_show:
        # If season exists → return season poster
        if season_number:
            season_poster = fetch_tmdb_season_poster(best_show.id, season_number)
            if season_poster:
                return season_poster

        if best_show.poster_path:
            return f"https://image.tmdb.org/t/p/w500{best_show.poster_path}"

    # -------------------------
    # Final fallback
    # -------------------------
    return "https://cdn-icons-png.flaticon.com/512/565/565547.png"

