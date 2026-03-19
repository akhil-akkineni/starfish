import requests
import spotipy

from spotipy.oauth2 import SpotifyOAuth
CLIENT_ID = "2043b4b8ab3b44868bf8a524848f510a"
CLIENT_SECRET = "ceea5003351e4472b1c26a3d06a85179"
REDIRECT_URI = "http://127.0.0.1:8000/callback"
SCOPE = "user-read-playback-state user-modify-playback-state user-top-read"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE))


top_tracks = sp.current_user_top_tracks(limit=20, time_range='long_term')
top_uri=[]
for song in top_tracks['items']:
    sp.add_to_queue(uri=f"{song.get('uri')}")

