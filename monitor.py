import os
import requests
from datetime import datetime, timezone, timedelta
from twilio.rest import Client
from github import Github

# --- Configuration ---
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")

RECIPIENT_WHATSAPP_NUMBER = 'whatsapp:+918886160680'
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'
# --- Set this to the real website when you are done testing ---
WEBSITE_URL = 'https://www.apollohospitals.com/' 
DOWNTIME_ISSUE_TITLE = "Automated Alert: Website is DOWN"
# --- End of Configuration ---

def check_website_status(url):
    """Checks a single website's status and returns True if up, False if down."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        
        if 200 <= response.status_code < 300:
            print(f"✅ Website {url} is UP.")
            return True
        else:
            print(f"🚨 Website {url} is DOWN. Status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"🚨 Website {url} is DOWN. Error: {e}")
        return False

def send_whatsapp_notification(message_body):
    """Sends a WhatsApp message via Twilio."""
    if not all([ACCOUNT_SID, AUTH_TOKEN]):
        print("❌ Twilio credentials not found in secrets. Skipping notification.")
        return
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message_body,
            to=RECIPIENT_WHATSAPP_NUMBER
        )
        print(f"✅ Successfully sent WhatsApp notification! SID: {message.sid}")
    except Exception as e:
        print(f"❌ Error sending WhatsApp notification: {e}")

def format_downtime(duration_seconds):
    """Formats the downtime duration."""
    seconds = int(duration_seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    
    duration_str = ""
    if days > 0: duration_str += f"{days}d "
    if hours > 0: duration_str += f"{hours}h "
    if minutes > 0: duration_str += f"{minutes}m "
    duration_str += f"{seconds}s"
    return duration_str.strip()

def manage_downtime_issue(repo):
    """Manages the state of the downtime issue on GitHub."""
    open_issues = repo.get_issues(state='open')
    for issue in open_issues:
        if issue.title == DOWNTIME_ISSUE_TITLE:
            print(f"Found existing downtime issue #{issue.number}.")
            return issue
    print("No existing downtime issue found.")
    return None

if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN not found.")
    else:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        is_up_now = check_website_status(WEBSITE_URL)
        downtime_issue = manage_downtime_issue(repo)
        
        ist_offset = timedelta(hours=5, minutes=30)
        
        if is_up_now:
            if downtime_issue:
                print("Site is back UP. Resolving the issue.")
                down_at_utc = downtime_issue.created_at
                up_at_utc = datetime.now(timezone.utc)
                total_downtime = up_at_utc - down_at_utc
                
                # --- NEW: Convert both times to IST for the message ---
                down_at_ist = down_at_utc + ist_offset
                up_at_ist = up_at_utc + ist_offset
                
                # --- UPDATED RECOVERY MESSAGE ---
                recovery_message = (
                    f"✅ **Server is UP!** ✅\n\n"
                    f"Website: {WEBSITE_URL}\n"
                    f"Status: **Back Online**\n\n"
                    f"The server went down at: *{down_at_ist.strftime('%Y-%m-%d %H:%M:%S IST')}*\n"
                    f"The server came back up at: *{up_at_ist.strftime('%Y-%m-%d %H:%M:%S IST')}*\n\n"
                    f"Total Downtime: *{format_downtime(total_downtime.total_seconds())}*"
                )
                
                send_whatsapp_notification(recovery_message)
                downtime_issue.create_comment(f"Resolved: Site came back online at {up_at_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}.")
                downtime_issue.edit(state='closed')
                print(f"Closed issue #{downtime_issue.number}.")
        else: # Site is DOWN
            if not downtime_issue:
                print("Site is DOWN. Creating a new issue and sending notification.")
                
                now_utc = datetime.now(timezone.utc)
                now_ist = now_utc + ist_offset
                
                down_message = (
                    f"🚨 **Server is DOWN!** 🚨\n\n"
                    f"Website: {WEBSITE_URL}\n"
                    f"Status: **Not Responding**\n\n"
                    f"Time of failure: *{now_ist.strftime('%Y-%m-%d %H:%M:%S IST')}*"
                )
                send_whatsapp_notification(down_message)
                repo.create_issue(
                    title=DOWNTIME_ISSUE_TITLE,
                    body=f"The monitor detected that {WEBSITE_URL} went down at {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}."
                )
                print("Created a new GitHub issue.")
            else:
                print("Site is still down. No new notification needed.")
