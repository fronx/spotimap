# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, ClientsideFunction
import webbrowser
import plotly.express as px

# ---

app = dash.Dash(__name__)

# ---

import numpy as np
import pandas as pd
import spotipy

from spotipy.oauth2 import SpotifyOAuth
scope = "user-library-read"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))


albums = sp.current_user_saved_albums()

# print(albums)

tracks = {t['uri']: {
	'name': t['name'],
	'uri': t['uri'],
	'preview_url': t['preview_url'],
	'href': t['external_urls']['spotify'],
	} for a in albums['items'] for t in a['album']['tracks']['items']}

chunk_size = 20
uris = list(tracks.keys())
chunked_uris = [uris[i:i + chunk_size] for i in range(0, len(uris), chunk_size)]

chunked_features = [sp.audio_features(uris) for uris in chunked_uris]
for features in chunked_features:
  for f in features:
    tracks[f['uri']].update({
        'instrumentalness': f['instrumentalness'],
        'danceability': f['danceability'],
        'energy': f['energy'],
        'tempo': f['tempo'],
        'valence': f['valence']
      })

tracks_data = list(tracks.values())
data = pd.DataFrame(tracks_data)

#------------------------------------

fig = px.scatter(data, x="instrumentalness", y="valence", color="danceability", custom_data=("href", "name", "preview_url", "uri",))
fig.update_traces(hovertemplate="""<a href="%{customdata[0]}">Name: %{customdata[1]}</a><br>URI: %{customdata[3]}<br>""")
fig.update_layout(clickmode='event+select')

# --

# <video controls="" autoplay="" name="media">
# 	<source src="https://p.scdn.co/mp3-preview/5c5623fee2333d3400d3face46fb72811b66b241?cid=c701bf448e4b4d609e92a50f462c3d8c" type="audio/mpeg">
# </video>

app.layout = html.Div(children=[
    html.H1(children='SpotiMap'),

    html.P(id='no-output-1'),
    html.P(id='no-output-2'),

    html.Video(id='preview-player', controls=True, autoPlay=False, children=[
    	html.Source(id='preview-source', src='https://p.scdn.co/mp3-preview/5c5623fee2333d3400d3face46fb72811b66b241?cid=c701bf448e4b4d609e92a50f462c3d8c', type="audio/mpeg"),
    ]),

    dcc.Graph(
        id='my-graph',
        figure=fig
    )
])

@app.callback(
    Output('no-output-1', 'children'),
    [Input('my-graph', 'clickData')]
)
def open_url(clickData):
    if clickData != None:
    	print(clickData)
    	url = clickData['points'][0]['customdata'][0]
    	webbrowser.open_new(url)

app.clientside_callback(
    ClientsideFunction(
        namespace='clientside',
        function_name='playPreview'
    ),
    Output('no-output-2', 'children'),
    Input('my-graph', 'hoverData'),
)

if __name__ == '__main__':
    app.run_server(debug=True, use_reloader=True)
