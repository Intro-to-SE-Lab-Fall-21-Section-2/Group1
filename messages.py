# Message object file
import json

class Message:
    
    def __init__(self, email_id, service):

        msg = service.users().messages().get(userId='me',id=email_id).execute()

        self.id = msg['id']
        self.threadId = msg['threadId']
        self.labelIds = msg['labelIds']
        self.snippet = msg['snippet']
        self.historyId = msg['historyId']
        self.internalDate = msg['internalDate']
        self.payload = msg['payload']
        self.sizeEstimate = msg['sizeEstimate']

        self.headers = {}
        # Convert headers into dict
        for entry in self.payload['headers']:
            self.headers[entry['name']] = entry['value']
        
        # print(self.headers)

        # for i in range(len(self.payload['headers'])):
        #     print(str(i) + ": " + str(self.payload['headers'][i]))

        # Header info
        self.delivered_to = self.headers.get('Delivered-To')
        self.from_ = self.headers.get('From')
        self.subject = self.headers.get('Subject')
        # self.cc = self.payload['headers']['cc']
        # self.bcc = self.payload['headers']['bcc']

    
class MessagePart:

    def __init__(self, part):

        self.partId = part['partId']
        self.mimeType = part['mimeType']
        self.filename = part['filename']
        self.headers = part['headers']
        self.body = part['body']
        self.parts = part['parts']
