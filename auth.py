from flask import Blueprint, redirect, url_for, session, request
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os

auth_blueprint = Blueprint('auth', __name__)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # ONLY for development
CLIENT_SECRETS_FILE = "C:\\Users\\SAM\\gmail-task-tracker\\credentials.json"
REDIRECT_URI = "http://localhost:5000/oauth2callback"
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly"
]


@auth_blueprint.route("/oauth/login")
def login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    print("Generated OAuth URL:", auth_url)  # Debug print to verify redirect_uri
    session['state'] = state
    return redirect(auth_url)

@auth_blueprint.route("/oauth2callback")
def oauth_callback():
    state = session.get('state')
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.url)

    if not flow.credentials:
        return "Authentication failed", 401

    creds = flow.credentials
    session['credentials'] = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }

    # Get user email using OAuth2 API
    userinfo_service = build('oauth2', 'v2', credentials=creds)
    user_info = userinfo_service.userinfo().get().execute()
    session['user_email'] = user_info.get('email')

    return redirect('/')

@auth_blueprint.route("/logout")
def logout():
    session.clear()
    return redirect('/')
