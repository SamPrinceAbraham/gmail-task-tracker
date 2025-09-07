import base64
import email
import re
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from email.header import decode_header
from email.utils import parseaddr
from models import db, Task
from app import app   # make sure this import does not cause circular import

# ✅ Decode MIME headers (handles UTF-8, encoded subjects, etc.)
def decode_mime_words(s):
    if not s:
        return ''
    decoded = ''
    for part, charset in decode_header(s):
        if isinstance(part, bytes):
            decoded += part.decode(charset or 'utf-8', errors='replace')
        else:
            decoded += part
    return decoded

# ✅ Extract "From" or fallback headers
def extract_sender(headers):
    sender_raw = None
    for header in headers:
        name = header['name'].lower()
        if name in ['from', 'reply-to', 'sender']:
            sender_raw = header['value']
            break

    if not sender_raw:
        return "Unknown Sender"

    # Decode & parse into (name, email)
    sender_raw = decode_mime_words(sender_raw)
    display_name, email_addr = parseaddr(sender_raw)
    return display_name if display_name else (email_addr if email_addr else "Unknown Sender")

# ✅ Fetch Gmail tasks
def get_task_emails(creds: Credentials, user_email: str):
    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(
        userId='me',
        q="task OR work OR to-do OR todo"
    ).execute()

    messages = results.get('messages', [])
    tasks = []

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        payload = msg_data.get('payload', {})
        headers = payload.get('headers', [])

        # Extract subject
        subject = decode_mime_words(
            next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
        )
        subject = subject.strip() if subject else "No Subject"

        # Extract sender ✅
        from_email = extract_sender(headers)

        # Extract body (prefer text/plain, fallback to stripped HTML)
        body = ''
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                    break
                elif part['mimeType'] == 'text/html' and 'data' in part['body']:
                    html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                    body = re.sub('<[^<]+?>', '', html_body)
                    break
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')

        tasks.append({
            'subject': subject,
            'from_email': from_email,  # ✅ consistent key
            'body': body.strip(),
            'user_email': user_email   # passed in
        })

    return tasks

# ✅ Store tasks in DB
def fetch_and_store_tasks(creds: Credentials, user_email: str):
    with app.app_context():
        fetched_tasks = get_task_emails(creds, user_email)
        new_tasks = 0

        for item in fetched_tasks:
            existing = Task.query.filter_by(
                subject=item['subject'],
                user_email=item['user_email']
            ).first()

            if not existing:
                task = Task(
                    subject=item['subject'],
                    from_email=item['from_email'],  # ✅ matches DB column
                    body=item['body'],
                    user_email=item['user_email']
                )
                db.session.add(task)
                new_tasks += 1

        db.session.commit()
        return new_tasks
