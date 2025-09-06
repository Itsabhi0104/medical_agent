import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def test_email_setup():
    """Test email configuration"""
    email_user = os.getenv('EMAIL_USER')
    email_password = os.getenv('EMAIL_PASSWORD')
    email_host = os.getenv('EMAIL_HOST')
    email_port = int(os.getenv('EMAIL_PORT', 587))
    
    print(f"Testing email setup for: {email_user}")
    print(f"SMTP Server: {email_host}:{email_port}")
    
    try:
        # Create test message
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = email_user  # Send to yourself for testing
        msg['Subject'] = "Medical Scheduler - Email Test"
        
        body = """
        <html>
        <body>
            <h2>Email Test Successful!</h2>
            <p>Your email configuration is working correctly.</p>
            <p>The Medical Appointment Scheduler can now send confirmation emails.</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Send email
        server = smtplib.SMTP(email_host, email_port)
        server.starttls()
        server.login(email_user, email_password)
        server.send_message(msg)
        server.quit()
        
        print("✅ Email test successful! Check your inbox.")
        return True
        
    except Exception as e:
        print(f"❌ Email test failed: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Make sure you're using an App Password for Gmail (not your regular password)")
        print("2. Enable 2-factor authentication on your Google account")
        print("3. Generate App Password: Google Account > Security > App passwords")
        print("4. Use the 16-character app password in your .env file")
        return False

if __name__ == "__main__":
    test_email_setup()