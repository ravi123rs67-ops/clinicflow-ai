import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load env variables from .env file relative to this file
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, '.env')
load_dotenv(dotenv_path=env_path)

from sheets import GoogleSheetsClient
from twilio_client import TwilioClient

def test_sheets_db():
    print("Testing Sheets/DB Module...")
    client = GoogleSheetsClient()
    
    # 1. Clean database.json if exists to start fresh
    if os.path.exists("database.json"):
        os.remove("database.json")
    client._load_local_db()
    
    # 2. Check slots for tomorrow
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    slots = client.check_available_slots(tomorrow)
    print(f"Available slots for tomorrow ({tomorrow}): {slots}")
    assert len(slots) > 0, "No available slots generated!"
    
    # 3. Book a slot
    time_to_book = slots[0]
    app = client.book_slot(tomorrow, time_to_book, "Test Patient", "+12345678", "Flu symptoms")
    print(f"Booked appointment: {app}")
    assert app is not None, "Booking failed!"
    assert app["patient_name"] == "Test Patient"
    
    # 4. Check available slots again
    slots_after = client.check_available_slots(tomorrow)
    assert time_to_book not in slots_after, "Booked slot is still available!"
    print("Slot booking verification successful.")
    
    # 5. Retrieve 24h reminders
    reminders = client.get_appointments_in_24h()
    assert len(reminders) == 1, f"Expected 1 reminder, got {len(reminders)}"
    print(f"Reminder to send: {reminders[0]}")
    
    # 6. Mark reminder sent
    client.mark_reminder_sent(reminders[0]["id"])
    reminders_after = client.get_appointments_in_24h()
    assert len(reminders_after) == 0, "Reminder was not marked as sent!"
    print("Reminder scan & mark sent successful.")


def test_twilio_client():
    print("\nTesting Twilio Client Module...")
    if os.path.exists("whatsapp_messages.json"):
        os.remove("whatsapp_messages.json")
        
    client = TwilioClient()
    success = client.send_whatsapp("+1987654321", "Test confirmation message", "Agent Test")
    # Note: success might be False if using real Twilio API with fake numbers (+1987654321 is invalid).
    # We verify that it is handled (either sent or logged to mock file).
    
    messages = client.get_messages()
    assert len(messages) == 1, "Message not logged in database!"
    assert messages[0]["body"] == "Test confirmation message"
    assert messages[0]["to"] == "whatsapp:+1987654321"
    print("Twilio Client check successful.")


def run_all_tests():
    print("==================================================")
    print("Starting Multi-Agent Booking System Scaffold Test")
    print("==================================================")
    
    test_sheets_db()
    test_twilio_client()
    
    print("\n==================================================")
    print("All component tests passed successfully!")
    print("==================================================")

if __name__ == "__main__":
    run_all_tests()
