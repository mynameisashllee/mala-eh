import flask
from flask import url_for, redirect, request, render_template, session, jsonify
import dotenv
import os
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_auth_requests
import googleapiclient.discovery
from google.auth.transport.requests import Request
import google.oauth2.credentials
from flask_googlemaps import GoogleMaps, Map



app = flask.Flask(__name__)
app.secret_key = os.urandom(24)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

SCOPES = [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/calendar.readonly"
        ]

api_key = os.environ.get("GOOGLE_API_KEY")
GoogleMaps(app, key=api_key)
devices_data = {}
devices_location = {}

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
    <h1>mala-eh.</h1>
    <h2>welcome {name.lower()}!</h2>
    <button onclick="window.location.href='/create'">create group</button>
    <button onclick="window.location.href='/join'">join group</button>
    """, 200



@app.route('/join')
def join():
    return render_template('join.html')

@app.route('/create')
def create():
    return render_template('create.html')

@app.route('/time', methods=['GET', 'POST'])
def time():
    # Check if user is logged in
    if 'credentials' not in session or 'id_info' not in session:
        session['final_redirect'] = url_for('time', _external=True)
        return redirect(url_for('google_login'))
    
    try:
        # Load credentials
        creds_dict = session['credentials']
        credentials = google.oauth2.credentials.Credentials(
            token=creds_dict['token'],
            refresh_token=creds_dict['refresh_token'],
            token_uri=creds_dict['token_uri'],
            client_id=creds_dict['client_id'],
            client_secret=creds_dict['client_secret'],
            scopes=creds_dict['scopes']
        )
        
        # Refresh token if expired
        if credentials.expired:
            credentials.refresh(Request())
            # Update session with new token
            session['credentials'] = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            session.modified = True
        
        # Build service
        service = googleapiclient.discovery.build(
            'calendar', 
            'v3', 
            credentials=credentials,
            static_discovery=False
        )
        
        # Time range (now to 3 days from now)
        now = datetime.utcnow().isoformat() + 'Z'
        three_days_later = (datetime.utcnow() + timedelta(days=3)).isoformat() + 'Z'
        
        # Fetch events
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=three_days_later,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Process events
        event_durations = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            if 'T' in start:  # Timed event
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                duration = end_dt - start_dt
                duration_str = str(duration)
            else:  # All-day event
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                days = (end_dt - start_dt).days
                duration_str = f"{days} day(s)"
            
            event_durations.append({
                'summary': event.get('summary', '(No title)'),
                'duration': duration_str,
                'start': start,
                'end': end,
                'is_all_day': 'T' not in start
            })
        
        return render_template('time.html', 
                             events=event_durations,
                             user_name=session['id_info'].get('name', 'User'))
    
    except Exception as e:
        app.logger.error(f"Error in time endpoint: {str(e)}")
        # Clear invalid session if there's an auth error
        if isinstance(e, google.auth.exceptions.RefreshError):
            session.clear()
            return redirect(url_for('google_login'))
        return str(e), 500
        
@app.route('/location')
def location():
    return render_template('location.html')

@app.route('/ingredient')
def ingredient(mp):
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
    