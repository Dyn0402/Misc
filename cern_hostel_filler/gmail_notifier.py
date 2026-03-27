import smtplib
from email.mime.text import MIMEText


class GmailNotifier:
    def __init__(self, cred_path):
        self.cred_path = cred_path
        self.uname, self.pword = self.load_cred()

    def load_cred(self):
        with open(self.cred_path, 'r') as file:
            uname, pword = file.readlines()
        return uname.strip(), pword.strip()

    def smtp_send(self, recipient, message):
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(self.uname, self.pword)
            try:
                smtp_server.sendmail(self.uname, [recipient], message.as_string())
            except Exception as e:
                print(f'Error sending email:\n{e}')

    def send_email(self, recipient, subject, body):
        msg = MIMEText(body, 'plain')
        msg['Subject'] = subject
        msg['From'] = self.uname
        msg['To'] = recipient
        self.smtp_send(recipient, msg)
