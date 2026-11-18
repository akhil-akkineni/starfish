import base64
import os
import secrets

import spotipy
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for
from spotipy.cache_handler import FlaskSessionCacheHandler
from spotipy.oauth2 import SpotifyOAuth

# Loads environment variables from .env (locally) or the host's config vars.
load_dotenv()

# Only the permissions this app actually uses (Spotify requires apps to
# request the minimum scopes they need):
#   playlist-read-private    find the user's existing "Yearly Rewind" playlist
#   playlist-modify-private  create the playlist and add/remove its tracks
#   user-top-read            read the user's top tracks
#   ugc-image-upload         set the playlist's cover image
SCOPE = "playlist-read-private playlist-modify-private user-top-read ugc-image-upload"

PLAYLIST_NAME = "Yearly Rewind"
PLAYLIST_DESCRIPTION = (
    "This is a recap of the past year of listening. Brought to you by Akhil Akkineni :)"
)
COVER_IMAGE_PATH = os.path.join("static", "playlist_ugc.jpg")
SPOTIFY_LOGO_FILE = "spotify-logo.png"

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or os.getenv("FLASK_SECRET_KEY")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("REDIRECT_URI", "").startswith("https://"),
)


def get_oauth(state=None):
    """Build an OAuth manager whose token is stored only in this user's session.

    The default spotipy file cache (.cache) is shared by every visitor, which
    would let one user's token be handed to another, so it is not used.
    """
    return SpotifyOAuth(
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        redirect_uri=os.getenv("REDIRECT_URI"),
        scope=SCOPE,
        state=state,
        show_dialog=True,
        cache_handler=FlaskSessionCacheHandler(session),
    )


def get_spotify_client():
    """Return a Spotify client for the logged-in user, or None if not logged in."""
    oauth = get_oauth()
    if not oauth.validate_token(oauth.cache_handler.get_cached_token()):
        return None
    return spotipy.Spotify(auth_manager=oauth)


def get_base64_image(image_path):
    with open(image_path, "rb") as img:
        return base64.b64encode(img.read()).decode("utf-8")


def find_playlist(sp, name):
    """Search all of the user's playlists (not just the first page) by name."""
    page = sp.current_user_playlists(limit=50)
    while page:
        for playlist in page["items"]:
            if playlist and playlist["name"] == name:
                return playlist
        page = sp.next(page) if page.get("next") else None
    return None


def playlist_track_uris(sp, playlist_id):
    uris = []
    page = sp.playlist_items(playlist_id=playlist_id)
    while page:
        for entry in page["items"]:
            item = entry.get("item") or entry.get("track")
            if item and item.get("uri"):
                uris.append(item["uri"])
        page = sp.next(page) if page.get("next") else None
    return uris


def render_page(**context):
    context.setdefault(
        "show_spotify_logo",
        os.path.exists(os.path.join(app.static_folder, SPOTIFY_LOGO_FILE)),
    )
    context.setdefault("spotify_logo_file", SPOTIFY_LOGO_FILE)
    return render_template("index.html", **context)


@app.route("/")
def landing():
    logged_in = get_spotify_client() is not None
    return render_page(logged_in=logged_in, event_status=request.args.get("msg", ""))


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/login")
def login():
    # Random state value protects the OAuth callback against CSRF.
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    return redirect(get_oauth(state=state).get_authorize_url())


@app.route("/callback")
def callback():
    expected_state = session.pop("oauth_state", None)
    if not expected_state or request.args.get("state") != expected_state:
        return redirect(url_for("landing", msg="Login failed. Please try again."))

    if request.args.get("error"):
        # The user declined the permissions on Spotify's consent screen.
        return redirect(url_for("landing", msg="Spotify login was cancelled."))

    code = request.args.get("code")
    if not code:
        return redirect(url_for("landing", msg="Login failed. Please try again."))

    get_oauth().get_access_token(code, as_dict=False, check_cache=False)
    return redirect(url_for("get_spotify"))


@app.route("/logout", methods=["POST"])
def logout():
    # The token lives only in the session cookie, so clearing it removes
    # everything this app holds about the user.
    session.clear()
    return redirect(
        url_for("landing", msg="You're logged out. This app no longer holds any of your Spotify data.")
    )


@app.route("/spotify", methods=["GET", "POST"])
def get_spotify():
    sp = get_spotify_client()
    if sp is None:
        return redirect(url_for("login"))

    event_status = ""
    playlist_url = None

    if request.method == "POST" and "createPlaylist" in request.form:
        try:
            playlist = find_playlist(sp, PLAYLIST_NAME)
            track_uris = []

            if playlist:
                playlist_id = playlist["id"]
                track_uris = playlist_track_uris(sp, playlist_id)
            else:
                playlist = sp.current_user_playlist_create(
                    name=PLAYLIST_NAME,
                    public=False,
                    description=PLAYLIST_DESCRIPTION,
                )
                playlist_id = playlist["id"]
                event_status = "Created new playlist!"

            playlist_url = playlist.get("external_urls", {}).get("spotify")

            if track_uris:
                sp.playlist_remove_all_occurrences_of_items(
                    playlist_id=playlist_id, items=track_uris
                )
                event_status = "All tracks removed. Click again to regenerate."
            else:
                data = sp.current_user_top_tracks(limit=20, time_range="long_term")
                top_tracks = [item["uri"] for item in data["items"]]
                sp.playlist_add_items(playlist_id=playlist_id, items=top_tracks)
                event_status = "Playlist updated with your top tracks!"

            try:
                sp.playlist_upload_cover_image(
                    playlist_id, get_base64_image(COVER_IMAGE_PATH)
                )
            except Exception as e:
                app.logger.warning("Cover upload failed: %s", e)

        except spotipy.SpotifyException as e:
            app.logger.warning("Spotify API error: %s", e)
            if e.http_status == 401:
                session.clear()
                return redirect(url_for("login"))
            event_status = "Something went wrong talking to Spotify. Please try again."

    return render_page(logged_in=True, event_status=event_status, playlist_url=playlist_url)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
