import os
from twilio.rest import Client

def handler(event, context):
    """
    This is the Netlify Function that runs when called by UptimeRobot.
    """
    # Load credentials securely from environment variables
    account_sid = os.environ.get('ACCOUNT_SID')
    auth_token = os.environ.get('AUTH_TOKEN')
    
    # Your Twilio and personal WhatsApp numbers
    twilio_number = 'whatsapp:+14155238886'
    recipient_number = 'whatsapp:+918886160680'
    
    # Get the alert message from UptimeRobot's webhook
    # The 'queryStringParameters' will contain the data sent by UptimeRobot
    payload = event.get('queryStringParameters', {})
    monitor_name = payload.get('monitorFriendlyName', 'A monitor')
    alert_details = payload.get('alertDetails', 'changed status')
    
    # Create the notification message
    message_body = f"🚨 Website Alert! 🚨\n\n{monitor_name} {alert_details}."

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=twilio_number,
            body=message_body,
            to=recipient_number
        )
        print(f"Successfully sent message, SID: {message.sid}")
        return {
            'statusCode': 200,
            'body': 'Message sent successfully.'
        }
    except Exception as e:
        print(f"Error sending Twilio message: {e}")
        return {
            'statusCode': 500,
            'body': 'Failed to send message.'
        }

