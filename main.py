# Main application script

import base64
from email import message
from inspect import getmembers
import os
from flask import Flask, render_template, redirect, session, url_for, request
from google.oauth2 import credentials
from googleapiclient.discovery import build

import auth
import email

# CONSTANTS
SYSTEM_LABELS = ['CHAT', 'SENT', 'INBOX', 'IMPORTANT', 'TRASH', 'DRAFT', 'SPAM', 'STARRED', 'UNREAD']

app = Flask(__name__)
app.secret_key = "CHANGE ME IN PRODUCTION" # TODO Needed for session
service = False

@app.route("/")
def index():
    if 'credentials' in session:
        return inbox()
    else:
        return render_template('landing.html')

# Authenticate/authorize
@app.route("/auth")
def authorize():
    if session.get('credentials'):
        return ("<h1>Error</h1>" + 
                "<p> You are already logged in </p>" + 
                "<p><a href='/'>Return to index</a></p>")
    
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
    # ACTION ITEM: In a production app, you likely want to save these
    #              credentials in a persistent database instead.

    if not session['credentials']:
        return ("<p>An error has occured</p>")
     
    # Build API service object
    buildService(session['credentials'])

    # Redirect to index
    return redirect(url_for('index'))

@app.route("/revoke")
def revoke():
    global service
    # Revokes OATUH access, user must allow application to reaccess API
    service = False
    revoke = auth.revokeAuth(session)
    if revoke:
        return redirect(url_for('index'))
    else: 
        return ("<p>Error revoking access<br><a href='/'>index</a></p>" + 
                "<p> You were probably not logged in. </p>")

@app.route("/clear")
def clear(): 
    global service
    # Clears creds from session (logs out)
    service = False
    if 'credentials' in session:
        del session['credentials']
        return redirect(url_for('index'))
    else:
        return ("<p>No stored credentials<br><a href='/'>index</a></p>")

@app.route("/playground")
def api_playgroud():
    labels = getLabels()

    return render_template('api_playground.html', labels=labels)

@app.route("/inbox")
def inbox():
    # Get user's email address
    if not 'profile' in session:
        buildService(session['credentials'])
        session['profile'] = service.users().getProfile(userId='me').execute()
    
    label_arg = request.args.get('label')
    page = request.args.get('page')
    query = request.args.get('q')
    
    buildService(session['credentials'])

    if label_arg:
        message_id_dict = service.users().messages().list(userId='me', maxResults=25, labelIds = [label_arg]).execute()
    else:
        message_id_dict = service.users().messages().list(userId='me', maxResults=25).execute()
    
    # Construct list of `Message`s
    messages =  []
    for message in message_id_dict['messages']:
        messages.append(getMessageData(message['id']))
    
    # Remove default system label names from list of label names. These will be
    # hardcoded in the template
    
    all_labels = getLabels()
    user_labels = []
    for label in all_labels:
        if label['name'] not in SYSTEM_LABELS:
            # Remove CATEGORY_ Prefix from some user labels
            label['name'] = label['name'].replace('CATEGORY_', '').capitalize()
            user_labels.append(label)
    return render_template("inboxread.html", messages=messages, labels=user_labels)

@app.route("/view")
def view():

    message_id = request.args.get('id')

    buildService(session['credentials'])

    message = getFullMessage(message_id)

    body = message.get_body(('plain',))
    if body:
        body = body.get_content()
    print(body)
    
    message_data = getMessageData(message_id)
    message_data['Body'] = body

    return render_template("view.html", message=message_data)


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

# API Methods
def buildService(session_creds):
    global service
    if service:
        print("main.py: buildService(): buildService() called but service already created")
        return 
    print("main.py: buildService(): Building new service resource for API")
    # Create credentials object from credentials dict stored in session
    creds = credentials.Credentials(**session_creds)
    # Build service object for API
    service = build(
        auth.API_SERVICE_NAME,
        auth.API_VERSION, 
        credentials = creds
    )
    print("main.py: buildService(): New service resource built")

def getLabels():
    # Returns array of labels
    # API Call
    buildService(session['credentials'])
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    return labels

def getMessageData(message_id):
    message = {}
    message_data = service.users().messages().get(userId='me', id=message_id).execute()
    
    message['id'] = message_data['id']
    message['threadId'] = message_data['threadId']
    message['labelIds'] = message_data['labelIds']
    message['snippet'] = message_data['snippet']

    headers = headersToDict(message_data['payload']['headers'])

    message['From'] = headers.get('From')
    message['Subject'] = headers.get('Subject')
    message['Date'] = headers.get('Date')

    return message

def getFullMessage(message_id):
    # Get raw mime data
    message_raw = service.users().messages().get(userId='me',id=message_id,format='raw').execute()

    # decode raw body data
    message_string = base64.urlsafe_b64decode(message_raw.get('raw').encode('ASCII'))

    # Create mime email object
    mime_msg = email.message_from_bytes(message_string, policy=email.policy.default)
    return mime_msg

def headersToDict(headers):
    header_dict = {}
    for header in headers:
        header_dict[header['name']] = header['value']
    return header_dict

# Flask preferences
if __name__ == "__main__":
    # DO NOT USE IN PRODUCTION
    # DISABLES HTTPS requirement for OAUTH2
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    # TODO enable SSL on httpd server

    # Set debug=False in production
    app.run(debug=True, host='127.0.0.1', port=5000)