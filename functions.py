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
def login():
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




ejdkerhf

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
