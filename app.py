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
    try:
        creds_dict = session['credentials']
        credentials = google.oauth2.credentials.Credentials(
            token=creds_dict['token'],
            refresh_token=creds_dict['refresh_token'],
            token_uri=creds_dict['token_uri'],
            client_id=creds_dict['client_id'],
            client_secret=creds_dict['client_secret'],
            scopes=creds_dict['scopes']
        )
        
        service = googleapiclient.discovery.build(
            'calendar', 'v3', credentials=credentials)
        
        now = datetime.utcnow().isoformat() + 'Z'
        end = (datetime.utcnow() + timedelta(days=3)).isoformat() + 'Z'
        
        result = service.freebusy().query(
            body={
                "timeMin": now,
                "timeMax": end,
                "items": [{"id": "primary"}]
            }
        ).execute()
        busy_slots = result.get('calendars', {}).get('primary', {}).get('busy', [])
        time_slots = []
        current_time = datetime.now().replace(second=0, microsecond=0)
        if current_time.minute < 30:
            current_time = current_time.replace(minute=30)
        else:
            current_time = current_time.replace(minute=0, hour=current_time.hour + 1)
        end_time = current_time + timedelta(days=3)
        while current_time < end_time:
            is_busy = False
            slot_start = current_time.isoformat() + 'Z'
            slot_end = (current_time + timedelta(minutes=30)).isoformat() + 'Z'
            for busy in busy_slots:
                busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))
                if (busy_start <= current_time < busy_end):
                    is_busy = True
                    break
            time_slots.append({
                'time': current_time,
                'formatted': current_time.strftime('%a %-I:%M %p'),
                'busy': is_busy
            })
            current_time += timedelta(minutes=30)
            if request.method == 'POST':
                selected_times = request.form.getlist('time_slot')
                session['selected_times'] = selected_times
                return redirect(url_for('location', code=123))
        return render_template('time.html', time_slots=time_slots, code=123)
    except Exception as e:
        print(f"An error occurred: {e}")
        return redirect(url_for('google_login'))

@app.route('/<code>/location')
def location(code):
    return render_template('location.html')

@app.route('/<code>/ingredient')
def ingredient(code):
    return render_template('ingredient.html')

@app.route('/<code>/spice')
def spice():
    return render_template('spice.html')

@app.route('/<code>/waiting')
def waiting():
    return render_template('waiting.html')

@app.route('/<code>/results')
def results():
    return render_template('results.html')

if __name__ == '__main__':
    app.run()







