import os
import requests
from datetime import datetime, timezone
from twilio.rest import Client
from github import Github

# --- Configuration ---
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")

RECIPIENT_WHATSAPP_NUMBER = 'whatsapp:+918886160680'
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'
WEBSITE_URL = 'https://www.thissitedoesnotexist12345.com/'
DOWNTIME_ISSUE_TITLE = "Automated Alert: Website is DOWN"
# --- End of Configuration ---

def check_website_status(url):
    """Checks a single website's status and returns True if up, False if down."""
    try:
        # --- FIX: Add a User-Agent header to mimic a real browser ---
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers) # Pass the headers here
        
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
        
        if is_up_now:
            if downtime_issue:
                print("Site is back UP. Resolving the issue.")
                down_at = downtime_issue.created_at
                up_at = datetime.now(timezone.utc)
                total_downtime = up_at - down_at
                
                recovery_message = (
                    f"✅ **Server is UP!** ✅\n\n"
                    f"Website: {WEBSITE_URL}\n"
                    f"Status: **Back Online**\n\n"
                    f"Recovered at: *{up_at.strftime('%Y-%m-%d %H:%M:%S UTC')}*\n"
                    f"Total Downtime: *{format_downtime(total_downtime.total_seconds())}*"
                )
                
                send_whatsapp_notification(recovery_message)
                downtime_issue.create_comment(f"Resolved: Site came back online at {up_at.strftime('%Y-%m-%d %H:%M:%S UTC')}.")
                downtime_issue.edit(state='closed')
                print(f"Closed issue #{downtime_issue.number}.")
        else: # Site is DOWN
            if not downtime_issue:
                print("Site is DOWN. Creating a new issue and sending notification.")
                down_message = (
                    f"🚨 **Server is DOWN!** 🚨\n\n"
                    f"Website: {WEBSITE_URL}\n"
                    f"Status: **Not Responding**\n\n"
                    f"Time of failure: *{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*"
                )
                send_whatsapp_notification(down_message)
                repo.create_issue(
                    title=DOWNTIME_ISSUE_TITLE,
                    body=f"The monitor detected that {WEBSITE_URL} went down at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}."
                )
                print("Created a new GitHub issue.")
            else:
                print("Site is still down. No new notification needed.")
