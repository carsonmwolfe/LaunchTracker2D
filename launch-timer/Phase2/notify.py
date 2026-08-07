#!/usr/bin/env python3
import smtplib
import sys
from email.mime.text import MIMEText

FROM = 'rangetrack551@gmail.com'
TO   = 'rangetrack551@gmail.com'
PASS_FILE = '/home/pi/.rangetrack_gmail_pass'

def send(body):
    try:
        with open(PASS_FILE) as f:
            password = f.read().strip()
        msg = MIMEText(body)
        msg['Subject'] = 'RangeTrack OS'
        msg['From']    = FROM
        msg['To']      = TO
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.starttls()
        s.login(FROM, password)
        s.sendmail(FROM, TO, msg.as_string())
        s.quit()
        print('Notification sent.')
    except Exception as e:
        print(f'Notification error: {e}')

if __name__ == '__main__':
    body = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'RangeTrack OS updated.'
    send(body)
