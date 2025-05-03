import flask
from flask import url_for, redirect, request, render_template, session
import dotenv
import os
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_auth_requests
import googleapiclient.discovery
from google.auth.transport.requests import Request
import google.oauth2.credentials

app = flask.Flask(__name__)
app.secret_key = os.urandom(24)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

SCOPES = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/calendar.readonly"
        ]

@app.route('/')
def index():
    return render_template('index.html'), 200

@app.route("/google_login")
def google_login():
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }, 
        scopes=SCOPES
    )
    flow.redirect_uri = "http://localhost:5000/google_login/oauth2callback"
    authorization_url, state = (
        flow.authorization_url(
            access_type="offline",
            prompt="select_account",
            include_granted_scopes="true"
            )
        )
    session["state"] = state
    session['final_redirect'] = "http://localhost:5000/logged_in"
    return redirect(authorization_url)

@app.route("/google_login/oauth2callback")
def oauth2callback():
    session_state = session['state']
    redirect_uri = request.base_url
    auth_response = request.url
    flow = flow = Flow.from_client_config(
        client_config={ 
            "web":
            {
                "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
                "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        ,scopes=SCOPES, state=session_state
    )
    flow.redirect_uri = redirect_uri
    flow.fetch_token(authorization_response=auth_response)
    credentials = flow.credentials
    creds = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    session['credentials'] = creds
    id_info = id_token.verify_oauth2_token(
        id_token=credentials.id_token,
        request=google_auth_requests.Request(),
        audience=os.environ.get("GOOGLE_CLIENT_ID")
    )
    session['id_info'] = id_info
    redirect_response = redirect(session['final_redirect'])
    return redirect_response, 200

@app.route('/logged_in')
def logged_in():
    picture = session['id_info']['picture']
    email = session['id_info']['email']
    name = session['id_info']['name']
    return f"""
    <h1>Logged in</h1>
    <h2>Welcome {name}</h2>
    <img src="{picture}" alt="Profile Picture">
    <h3>Email: {email}</h3>
    """, 200



@app.route('/join/<code>')
def join(code):
    return render_template('join.html', code=code)

@app.route('/time', methods=['GET', 'POST'])
def time():
    return render_template('time.html')
        
        
        
@app.route('/<code>/location')
def location(code):
    return render_template('location.html')

@app.route('/ingredient')
def ingredient():
    ingredients = ["potato", "tomato", "tofu", "sausage", "luncheon meat", "rice", "maggi", "cheese tofu", "cabbage"]

    return render_template('ingredient.html', ingredients=ingredients)

@app.route('/spice')
def spice():
    return render_template('spice.html')

@app.route('/waiting')
def waiting():
    return render_template('waiting.html')

@app.route('/results')
def results():
    return render_template('results.html')

if __name__ == '__main__':
    app.run()
