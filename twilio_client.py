import json
import os
import requests
from datetime import datetime

MOCK_MESSAGES_FILE = "whatsapp_messages.json"

class TwilioClient:
    """
    Handles sending WhatsApp messages.
    If Twilio credentials are set in the environment, it uses the real Twilio HTTP API.
    Otherwise, it appends to a local whatsapp_messages.json log file for visualization.
    """
    def __init__(self):
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        self.auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        self.from_number = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886") # Default Twilio Sandbox
        
        self.use_real_twilio = bool(self.account_sid and self.auth_token)
        self._initialize_mock_file()

    def _initialize_mock_file(self):
        if not os.path.exists(MOCK_MESSAGES_FILE):
            with open(MOCK_MESSAGES_FILE, 'w') as f:
                json.dump([], f)

    def _log_mock_message(self, to_number: str, body: str, agent_sender: str):
        try:
            with open(MOCK_MESSAGES_FILE, 'r') as f:
                messages = json.load(f)
        except Exception:
            messages = []
            
        new_msg = {
            "timestamp": datetime.now().isoformat(),
            "to": to_number,
            "from": self.from_number,
            "body": body,
            "sender": agent_sender,
            "mode": "Real (Twilio API)" if self.use_real_twilio else "Mock (Sandbox Simulation)"
        }
        messages.append(new_msg)
        
        with open(MOCK_MESSAGES_FILE, 'w') as f:
            json.dump(messages, f, indent=4)
            
        print(f"[{agent_sender}] Sent WhatsApp message to {to_number}: '{body}'")

    def send_whatsapp(self, to_number: str, body: str, agent_sender: str = "System") -> bool:
        """
        Sends a WhatsApp message via Twilio API or appends to a local mock log file.
        """
        # Format destination number to include 'whatsapp:' prefix if not present
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
            
        if self.use_real_twilio:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            data = {
                "From": self.from_number,
                "To": to_number,
                "Body": body
            }
            try:
                response = requests.post(url, data=data, auth=(self.account_sid, self.auth_token))
                if response.status_code in [200, 201]:
                    self._log_mock_message(to_number, body, agent_sender)
                    return True
                else:
                    print(f"Twilio API Error: {response.status_code} - {response.text}")
                    # Fallback to mock on API failure to prevent system crash
                    self._log_mock_message(to_number, body, f"{agent_sender} (Twilio Fallback Mock)")
                    return False
            except Exception as e:
                print(f"Twilio HTTP exception: {e}")
                self._log_mock_message(to_number, body, f"{agent_sender} (Twilio Fallback Mock)")
                return False
        else:
            self._log_mock_message(to_number, body, agent_sender)
            return True

    def get_messages(self) -> list[dict]:
        self._initialize_mock_file()
        try:
            with open(MOCK_MESSAGES_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
