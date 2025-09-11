#!/usr/bin/env python3
"""Test email notifications"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Test with your GitHub secrets
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") 
EMAIL_TO = os.getenv("EMAIL_TO")

def test_email():
    if not all([EMAIL_USER, EMAIL_PASSWORD, EMAIL_TO]):
        print("❌ Missing email environment variables")
        print(f"EMAIL_USER: {'✅' if EMAIL_USER else '❌'}")
        print(f"EMAIL_PASSWORD: {'✅' if EMAIL_PASSWORD else '❌'}")
        print(f"EMAIL_TO: {'✅' if EMAIL_TO else '❌'}")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_TO
        msg['Subject'] = "🧪 Museum Checker Test - Email Works!"
        
        body = """
🎉 Success! Your email notifications are working perfectly!

This is a test message from your Museum Availability Checker.

When Chichu or Teshima Art Museum tickets become available for October 7th, 
you'll receive an email just like this one with the booking link.

✅ Email configuration: WORKING
🤖 Monitoring: Every 20 minutes via GitHub Actions
📅 Target date: October 7th, 2025

Ready to catch those tickets! 🎫
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, EMAIL_TO, text)
        server.quit()
        
        print("✅ Test email sent successfully!")
        print(f"📧 Check your inbox: {EMAIL_TO}")
        return True
        
    except Exception as e:
        print(f"❌ Email test failed: {e}")
        return False

if __name__ == "__main__":
    test_email()
