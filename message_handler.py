# Functions for message handling
import email
import base64

def getMessageData(message_id, service):
    message = {}
    message_data = service.user().messages().get(userId='me', id=message_id).execute()
    
    message['id'] = message_data['id']
    message['threadId'] = message_data['threadId']
    message['labelIds'] = message_data['labelIds']
    message['snippet'] = message_data['snippet']

    headers = headersToDict(message_data['headers'])

    message['From'] = headers.get('From')
    message['Subject'] = headers.get('Subject')
    message['Date'] = headers.get('Date')

    return message

def getFullMessage(message_id, service):
    # Get raw mime data
    message_raw = service.users().messages().get(userId='me',id=message_id,format='raw').execute()

    # decode raw body data
    message_string = base64.urlsafe_b64decode(message_raw.get('raw').encode('ASCII'))

    # Create mime email object
    mime_msg = email.message_from_bytes(message_string)
    return mime_msg

def headersToDict(headers):
    header_dict = {}
    for header in headers:
        header_dict[header['name']] = header['value']
    return header_dict


