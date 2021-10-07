# Main application script

import os
from flask import Flask, render_template, redirect, session, url_for, request
from google.oauth2 import credentials
from googleapiclient.discovery import build
import auth

app = Flask(__name__)
app.secret_key = "CHANGE ME IN PRODUCTION" # TODO Needed for session 

@app.route("/")
def index():
    return render_template('index.html')

# Authenticate/authorize
@app.route("/auth")
def authorize():
    # Get authorization url to redirect to
    authorization_url, state = auth.authorize(url_for('oauth2callback', 
                                        _external=True))

    # Store the state so the callback can verify the auth server response.
    session['state'] = state

    # Eventually redirects to /oauth2callback
    return redirect(authorization_url)

@app.route("/oauth2callback")
def oauth2callback():
    # Get credientials from returned authorixation_url
    session['credentials'] = auth.getCredentials(
        url_for('oauth2callback', _external = True), # redirect_url
        session['state'],
        request.url # authorization_response
    )

    # Redirect to index
    return redirect(url_for('index'))

@app.route("/revoke")
def revoke():
    # Revokes credentials (not working)
    # FIXME
    revoke = auth.revokeAuth(session)
    if revoke:
        return redirect(url_for('index'))
    else: 
        return ("<p>Error revoking access<br><a href='/'>index</a></p>" + 
                "<p> You are most likely still logged in </p>")

@app.route("/clear")
def clear():
    # Clears creds from session (logs out)
    if 'credentials' in session:
        del session['credentials']
        return redirect(url_for('index'))
    else:
        return ("<p>No stored credentials<br><a href='/'>index</a></p>")

# Labels test
@app.route("/labels")
def labels():
    if 'credentials' not in session:
        return ("You're not logged in")

    # Create credentials object from credentials dict stored in session
    creds = credentials.Credentials(**session['credentials'])

    # Build service object for API
    service = build(
        auth.API_SERVICE_NAME,
        auth.API_VERSION, 
        credentials = creds
    )

    # API Call
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    if not labels:
        return ("No labels found")
    
    output = "<h1>Labels</h1><br>"
    for label in labels:
        output += (label['name'] + ":      " + str(label) + "<br>")
    
    output += "<a href='/'>Index</a"
    return output

@app.route("/start")
def star():
    return render_template('startPage.html')

@app.route("/login")
def login():
    return render_template('loginpage.html')

@app.route("/register")
def register():
    return render_template('emailCreator.html')

@app.route("/inbox_list")
def inboxList():
    return render_template('inboxlist.html')

@app.route("/drafts_list")
def draftsList():
    return render_template('draftslist.html')

@app.route("/edit_window")
def editWindow():
    return render_template('editwindow.html')

@app.route("/inbox_read")
def inboxRead():
    return render_template('inboxread.html')

@app.route("/outbox_list")
def outboxList():
    return render_template('outboxlist.html')

@app.route("/outbox_read")
def outboxRead():
    return render_template('outboxread.html')

@app.route("/signup")
def signUp():
    return render_template('signup.html')


if __name__ == "__main__":
    # DO NOT USE IN PRODUCTION
    # DISABLES HTTPS requirement for OAUTH2
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    # TODO enable SSL on httpd server

    # Set debug=False in production
    app.run(debug=True, host='127.0.0.1', port=5000) 