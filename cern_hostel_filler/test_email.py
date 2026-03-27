from pathlib import Path
from gmail_notifier import GmailNotifier

GMAIL_CRED_PATH = Path.home() / "Desktop/creds/gmail_cred.txt"
NOTIFY_EMAIL = "dyn040294@gmail.com"

notifier = GmailNotifier(str(GMAIL_CRED_PATH))
notifier.send_email(NOTIFY_EMAIL, "CERN Hostel Notifier – test email", "If you're reading this, the email notifier is working correctly.")
print("Email sent.")
