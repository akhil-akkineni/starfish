#Importing all the necessary libraries

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






@app.route("/spotify", methods = ["GET", "POST"])
def getSpotify():
    #Setting Up Variables
    playlistExists = False
    playlist_Name = "Yearly Rewind"
    playlist_Description = "This is a recap of the past year of listening. Brought to you by Akhil Akkineni :)"
    playlist_Created = False
    
    token_info = session.get("token_info")

    if not token_info:
        return redirect("/login")
        
    sp = spotipy.Spotify(auth=token_info["access_token"])
    playlists = sp.current_user_playlists()
    track_uri = []
    
    #Picks up the broadcast
    if request.method == "POST":
        print("Posted...")
        #Specifies which broadcast to act on
        if "createPlaylist" in request.form:
            print("Sequence Active.")
            #SpotifyAPI requests start.
            #Looks at users playlists
            for playlist in playlists["items"]:
                #Checks if the playlist was already created by matching with name(Need to change the matching process)
                if playlist["name"] == playlist_Name:
                    #Saves the playlist ID and uses the ID to check the track items
                    playlist_uri = playlist["uri"]
                    track_list = sp.playlist_items(playlist_id=playlist_uri)
                    #Ensures that another playlist isnt made
                    playlist_Created = True
                    for tag in track_list["items"]:
                        #Puts all the track IDs in a list
                        
                        track_uri.append(tag["item"]["uri"])
                        playlistExists = True
            if playlistExists == True:
                #If the playlist was already created, it removes all the tracks from the playlist.
                sp.playlist_remove_all_occurrences_of_items(playlist_id=playlist_uri,items=track_uri)

            if playlist_Created == False:
                #If the playlist name was not found it creates a new playlist
                new_playlist = sp.current_user_playlist_create(name= playlist_Name,public=False, description= playlist_Description)
                for playlist in playlists["items"]:
                    if playlist["name"] == playlist_Name:
                        playlist_uri = playlist["uri"]
            if playlistExists == False:
                #If playlist is there but there are no tracks the top 20 tracks are added to the playlist
                data = sp.current_user_top_tracks(limit= 20, time_range= "long_term")
                top_list = []
                for item in data["items"]:
                    song_uri = item["uri"]
                    top_list.append(song_uri)
                sp.playlist_add_items(playlist_id=playlist_uri,items=top_list)
                print("Passed Through...")
        else:
            print("Not fetching...")            
    return(render_template("index.html"))
#Runs the host site
if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
