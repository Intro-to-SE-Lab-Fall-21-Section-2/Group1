# Main application script

import base64
from logging import error
import os
from flask import Flask, render_template, redirect, session, url_for, request
from google.oauth2 import credentials
from googleapiclient.discovery import build 
from googleapiclient import errors
from requests.sessions import Request


import auth
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
import mimetypes

# CONSTANTS
SYSTEM_LABELS = ['CHAT', 'SENT', 'INBOX', 'IMPORTANT', 'TRASH', 'DRAFT', 'SPAM', 'STARRED', 'UNREAD']
UPLOAD_FOLDER = "./uploads/"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
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
        return redirect(url_for('clear'))
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
    

    labels = getLabels()

    return render_template('api_playground.html', labels=labels)

@app.route("/inbox")
def inbox():
    # Get user's email address
    if not 'profile' in session:
        buildService(session['credentials'])
        session['profile'] = service.users().getProfile(userId='me').execute()
    
    session['current_inbox'] = "INBOX" if not request.args.get('label') else request.args.get('label')
    session['current_page'] = '' if not request.args.get('page') else request.args.get('page')
    session['query'] = "" if not request.args.get('q') else request.args.get('q')
    
    buildService(session['credentials'])

    try:
        if session['current_inbox']:
            if session['current_page']:
                if session['query']: # inbox, page, and query
                    message_id_dict = service.users().messages().list(userId='me', maxResults=25, labelIds = [session['current_inbox']], pageToken = session['current_page'], q = str(session['query'])).execute()
                else: # inbox and page
                    # Call
                    message_id_dict = service.users().messages().list(userId='me', maxResults=25, labelIds = [session['current_inbox']], pageToken = session['current_page']).execute()
            else:
                if session['query']: # inbox and query
                    message_id_dict = service.users().messages().list(userId='me', maxResults=25, labelIds = [session['current_inbox']], q=str(session['query'])).execute()
                else: # inbox only
                    # Call
                    message_id_dict = service.users().messages().list(userId='me', maxResults=25, labelIds = [session['current_inbox']]).execute()

        else: # is not inbox
            if session['current_page']:
                if session['query']: # page and query
                    message_id_dict = service.users().messages().list(userId='me', maxResults=25, pageToke = session['current_page'], q=session['query']).execute()
                else: # page
                    # Call
                    message_id_dict = service.users().messages().list(userId='me', maxResults=25, pageToke = session['current_page']).execute()
            else: # is not page and inbox
                if session['query']: # query
                    message_id_dict = service.users().messages().list(userId='me', maxResults=25, q=session['query']).execute()
                else: # none
                    # Call
                    message_id_dict = service.users().messages().list(userId='me', maxResults=25).execute()
                    
    except errors.HttpError as error:
        return render_template("error.html", error)
    
    # Construct list of `Message`s
    messages =  []
    if message_id_dict['resultSizeEstimate'] == 0: # no results returned
        messages.append( {
            'Subject' : 'No results for ' + session['query'],
            'From'  : '',
            'snippet' : ''
        } )
    else: # business as usual
        session['next_page'] = message_id_dict.get('nextPageToken') if message_id_dict.get('nextPageToken') else ''
        for message in message_id_dict.get("messages"):
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
    return render_template("inbox.html", messages=messages, labels=user_labels)

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

    return render_template("view.html", message=message_data, labels=getLabels())

@app.route("/compose", methods=['GET', 'POST'])
def compose():
    # Populate some empty variables for compose
    error = ""
    message_parameters = {
        'to': "",
        'Subject': "",
        'body': ""
    }
    if request.method == 'POST':
        message_parameters = request.form
        print(message_parameters)

        # Print error on page        
        if error:
            return render_template('compose.html', message=message_parameters, error=error)
        else: # Process message and send

            if request.files.get('attachment').filename == '': # No attachment
                message = MIMEText(str(message_parameters['body']))
                message['to'] = str(message_parameters['to'])
                message['from'] = str(session['profile']['emailAddress'])
                message['subject'] = str(message_parameters['Subject'])
                raw_message =  {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
            
            else:
                attachment = request.files['attachment']
                attachment.save(os.path.join(app.config['UPLOAD_FOLDER'], attachment.filename))
                attachment_name = os.path.join(app.config['UPLOAD_FOLDER'], attachment.filename)

                message = MIMEMultipart('aternative')
                message['to'] = str(message_parameters['to'])
                message['from'] = str(session['profile']['emailAddress'] )
                message['subject'] = str(message_parameters.get('Subject'))

                content_type, encoding = mimetypes.guess_type(attachment_name)

                if content_type is None or encoding is not None:
                    content_type = 'application/octet-stream'
                main_type, sub_type = content_type.split('/', 1)
                if main_type == 'text':
                    fp = open(attachment_name, 'rb')
                    msg = MIMEText(fp.read(), _subtype=sub_type)
                    fp.close()
                elif main_type == 'image':
                    fp = open(attachment_name, 'rb')
                    msg = MIMEImage(fp.read(), _subtype=sub_type)
                    fp.close()
                elif main_type == 'audio':
                    fp = open(attachment_name, 'rb')
                    msg = MIMEAudio(fp.read(), _subtype=sub_type)
                    fp.close()
                else:
                    fp = open(attachment_name, 'rb')
                    msg = MIMEBase(main_type, sub_type)
                    msg.set_payload(fp.read())
                    fp.close()
                filename = os.path.basename(attachment_name)
                msg.add_header('Content-Disposition', 'attachment', filename=filename)
                
                message.attach(MIMEText(str(message_parameters['body'])))
                message.attach(msg)
            
            raw_message =  {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

            buildService(session['credentials'])
            service.users().messages().send(userId='me', body=raw_message).execute()
            return redirect(url_for('inbox'))
    else:    
        return render_template('compose.html', message=message_parameters, error=error, labels=getLabels())

# API Methods
def buildService(session_creds):
    global service
        
    if service:
        print("main.py: buildService(): buildService() called but service already created")
        return 
    print("main.py: buildService(): Building new service resource for API")
    # Create credentials object from credentials dict stored in session
    try:
        creds = credentials.Credentials(**session_creds)
    
        # Build service object for API
        service = build(
            auth.API_SERVICE_NAME,
            auth.API_VERSION, 
            credentials = creds
        )
        print("main.py: buildService(): New service resource built")
    
    except:
        redirect( url_for('clear') )

def getLabels():
    # Returns array of labels
    # API Call
    buildService(session['credentials'])
    
    try:
        results = service.users().labels().list(userId='me').execute()
    except errors.HttpError as error:
        return 0
        
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

    message['From'] = headers.get('From') or headers.get('from') or headers.get('FROM')
    message['Subject'] = headers.get('Subject') or headers.get('SUBJECT') or headers.get('subject')
    message['Date'] = headers.get('Date')

    return message

def getFullMessage(message_id):
    # Get raw mime data
    try:
        message_raw = service.users().messages().get(userId='me',id=message_id,format='raw').execute()
    except errors.HttpError as error:
        render_template('error.html', error)

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