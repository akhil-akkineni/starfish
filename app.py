#Importing all the necessary libraries
import base64
import os
import gunicorn
import dotenv
import spotipy
from spotipy import SpotifyOAuth
from dotenv import load_dotenv
import flask
from flask import Flask, redirect, url_for, render_template, request, session

#Loads Environment variables
load_dotenv()


#Resets token to ensure authentication repeats for every run
# May need to be deleted for web deployment
# if os.path.exists(os.getenv('CACHE_PATH')):
#     os.remove(os.getenv('CACHE_PATH'))
#Creates a Spotify Client and defines API permissions.

sp_oauth = SpotifyOAuth(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    redirect_uri=os.getenv("REDIRECT_URI"),
    scope=os.getenv("SCOPE")
)

def get_token():
    token_info = session.get("token_info")

    if not token_info:
        return None

    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(
            token_info["refresh_token"]
        )
        session["token_info"] = token_info

    return token_info



def get_base64_image(image_path):
    with open(image_path, "rb") as img:
        encoded = base64.b64encode(img.read())
        return encoded.decode("utf-8")
image_b64 = get_base64_image("static/playlist_ugc.jpg")

#Setting up Flask
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")



@app.route("/")
def landing():
    return(render_template("index.html"))



@app.route("/login")
def login():
        
        
    auth_url = SpotifyOAuth(
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        redirect_uri=os.getenv("REDIRECT_URI"),
        scope=os.getenv("SCOPE")
    ).get_authorize_url()
    
    return redirect(auth_url)

@app.route("/callback")
def callback():

    sp_oauth = SpotifyOAuth(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    redirect_uri=os.getenv("REDIRECT_URI"),
    scope=os.getenv("SCOPE")
)
    
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    
    session["token_info"] = token_info
    
    return redirect("/spotify")






@app.route("/spotify", methods=["GET", "POST"])
def getSpotify():
    playlist_name = "Yearly Rewind"
    playlist_description = "This is a recap of the past year of listening. Brought to you by Akhil Akkineni :)"
    event_status = ""

    #  Get valid token (auto refresh)
    token_info = get_token()
    if not token_info:
        return redirect("/login")

    sp = spotipy.Spotify(auth=token_info["access_token"])

    #  Get playlists safely
    try:
        playlists = sp.current_user_playlists()
    except:
        return redirect("/login")

    if request.method == "POST" and "createPlaylist" in request.form:
        print("Sequence Active.")

        playlist_id = None
        track_uris = []

        #  Find existing playlist
        for playlist in playlists["items"]:
            if playlist["name"] == playlist_name:
                playlist_id = playlist["id"]

                track_list = sp.playlist_items(playlist_id=playlist_id)

                for item in track_list["items"]:
                    if item["item"]:
                        track_uris.append(item["item"]["uri"])

                break  # stop once found

        #  Create playlist if it doesn't exist
        if not playlist_id:
            new_playlist = sp.current_user_playlist_create(
                name=playlist_name,
                public=False,
                description=playlist_description
            )
            playlist_id = new_playlist["id"]
            event_status = "Created new playlist!"

        #  Toggle behavior
        if track_uris:
            # Remove all tracks
            sp.playlist_remove_all_occurrences_of_items(
                playlist_id=playlist_id,
                items=track_uris
            )
            event_status = "All tracks removed. Click again to regenerate."
        else:
            # Add top tracks
            data = sp.current_user_top_tracks(limit=20, time_range="long_term")
            top_tracks = [item["uri"] for item in data["items"]]

            sp.playlist_add_items(
                playlist_id=playlist_id,
                items=top_tracks
            )
            event_status = "Playlist updated with your top tracks!"

        #  Upload cover image (SAFE)
        try:
            image_b64 = get_base64_image("static/playlist_ugc.jpg")
            sp.playlist_upload_cover_image(playlist_id, image_b64)
        except Exception as e:
            print("Cover upload failed:", e)

    return render_template("index.html", event_status=event_status)
#Runs the host site
if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
