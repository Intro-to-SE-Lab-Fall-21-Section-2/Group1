# Functions specific to web Google OAUTH2 Auth necessary for Gmail API
# Most code modified from Google OAUTH2 docs
# https://developers.google.com/identity/protocols/oauth2/web-server#python

import requests
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

CLIENT_SECRETS_FILE_LOC = "../.secret/client_secret.json"
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
API_SERVICE_NAME = 'gmail'
API_VERSION = 'v1'
passthrough = "test" # This is used for something or rather
# SSL_CONTEXT # Tuple that holds SSL cert and key, used for SSL in flask
            # Shouldn't be an issue in prod

def authorize(callback_uri):
    print("auth.py: authorize(): authorize() called, beginning OAuth 2.0 authorization")

    print("auth.py: authorize(): creating `flow` object...")
    # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE_LOC, scopes=SCOPES)

    # The URI created here must exactly match one of the authorized redirect URIs
    # for the OAuth 2.0 client, which you configured in the API Console. If this
    # value doesn't match an authorized URI, you will get a 'redirect_uri_mismatch'
    # error.
    flow.redirect_uri = callback_uri
    print("auth.py: authorize(): `flow` object created")

    print("auth.py: authorize(): obtaining authorizatiun_url...")
    authorization_url = flow.authorization_url(
        # Enable offline access so that you can refresh an access token without
        # re-prompting the user for permission. Recommended for web server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true')
        
    print("auth.py: authorize(): authorization_url created, returning now")
    return authorization_url

def getCredentials(redirect_uri, state, authorization_response):
    print("auth.py: getCredentials(): getCredentials() called")
    print("auth.py: getCredentials(): Creating `flow`... ")
    
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE_LOC, scopes=SCOPES, state=state)
    flow.redirect_uri = redirect_uri

    print("auth.py: getCredentials(): `flow` object created, fetching credentials...")

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    flow.fetch_token(authorization_response=authorization_response)
    print("auth.py: getCredentials(): OAUTh2 credentials received, returning now")

    return credentials_to_dict(flow.credentials)

def revokeAuth(session):
    print("auth.py: revokeAuth(): revokaAuth() called")
    if 'credentials' not in session:
        print("NOTE: auth.py: revokeAuth(): Credentials not found, returning False")
        return False

    credentials = google.oauth2.credentials.Credentials(
        **session['credentials'])
    
    print("auth.py: revokeAuth(): Sending revoke request...")
    revoke = requests.post('https://oauth2.googleapis.com/revoke',
        params={'token': credentials.token},
        headers = {'content-type': 'application/x-www-form-urlencoded'})

    status_code = getattr(revoke, 'status_code')
    if status_code == 200:
        print("auth.py: revokeAuth(): Revoke request successful, returning True")
        return True
    else:
        print("ERROR: auth.py: revokeAuth(): Remote error revoking credentials, status_code=" + status_code + ", returning False")
        return False


def credentials_to_dict(credentials):
  return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
        }
