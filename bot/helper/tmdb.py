from tmdbv3api import TMDb, Movie, TV

tmdb = TMDb()
tmdb.api_key = "68be78e728be4e86e934df1591d26c5b"
tmdb.language = 'en'

def fetch_poster(title: str) -> str:
    """Fetch poster URL from TMDb for a movie, TV show, or fallback image."""
    try:
        # Try as movie
        m = Movie()
        movies = m.search(title)
        if movies and movies[0].poster_path:
            return f"https://image.tmdb.org/t/p/w500{movies[0].poster_path}"

        # Try as TV show
        tv = TV()
        shows = tv.search(title)
        if shows and shows[0].poster_path:
            return f"https://image.tmdb.org/t/p/w500{shows[0].poster_path}"

    except Exception as e:
        print(f"TMDb fetch error for '{title}': {e}")

    # Fallback image
    return "https://cdn-icons-png.flaticon.com/512/565/565547.png"
