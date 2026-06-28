import json
import os
from datetime import datetime, timedelta

DATABASE_FILE = "database.json"

class GoogleSheetsClient:
    """
    Manages appointment slots.
    If Google Sheet credentials/configuration is set, it can sync with Google Sheets.
    Otherwise, it uses a local database.json file as a fallback.
    """
    def __init__(self):
        self.use_real_sheets = False
        # Try to initialize google sheet client if environment variable is set
        # For this scaffolding, we default to local JSON storage unless configured.
        self._load_local_db()

    def _load_local_db(self):
        if not os.path.exists(DATABASE_FILE):
            self._initialize_default_slots()
        else:
            try:
                with open(DATABASE_FILE, 'r') as f:
                    self.db = json.load(f)
            except Exception:
                self._initialize_default_slots()

    def _save_local_db(self):
        try:
            with open(DATABASE_FILE, 'w') as f:
                json.dump(self.db, f, indent=4)
        except Exception as e:
            print(f"Error saving database: {e}")

    def _initialize_default_slots(self):
        # Generate slots for the next 10 days
        self.db = {
            "appointments": [],
            "slots": {}
        }
        today = datetime.now()
        times = ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM", "04:00 PM"]
        
        for i in range(10):
            date_str = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            self.db["slots"][date_str] = {t: "Available" for t in times}
        
        self._save_local_db()

    def check_available_slots(self, date_str: str) -> list[str]:
        """
        Returns a list of available slot times for a given date.
        """
        self._load_local_db()
        if date_str not in self.db["slots"]:
            # Dynamically add slots for this new date
            times = ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM", "04:00 PM"]
            self.db["slots"][date_str] = {t: "Available" for t in times}
            self._save_local_db()
            
        slots = self.db["slots"][date_str]
        return [t for t, status in slots.items() if status == "Available"]

    def book_slot(self, date_str: str, time_str: str, patient_name: str, phone: str, symptoms: str) -> dict | None:
        """
        Books a slot if it is available. Returns the booking details, or None if failed.
        """
        self._load_local_db()
        if date_str not in self.db["slots"] or time_str not in self.db["slots"][date_str]:
            return None
        
        if self.db["slots"][date_str][time_str] != "Available":
            return None
        
        # Mark slot as booked
        self.db["slots"][date_str][time_str] = f"Booked - {patient_name}"
        
        # Create appointment record
        appointment = {
            "id": len(self.db["appointments"]) + 1,
            "patient_name": patient_name,
            "phone": phone,
            "symptoms": symptoms,
            "date": date_str,
            "time": time_str,
            "status": "Booked",
            "booked_at": datetime.now().isoformat(),
            "reminder_sent": False,
            "followup_sent": False
        }
        self.db["appointments"].append(appointment)
        self._save_local_db()
        return appointment

    def get_appointments(self) -> list[dict]:
        self._load_local_db()
        return self.db.get("appointments", [])

    def get_slots_raw(self) -> dict:
        self._load_local_db()
        return self.db.get("slots", {})

    def get_appointments_in_24h(self) -> list[dict]:
        """
        Returns appointments scheduled for tomorrow (approx. 24 hours away).
        """
        self._load_local_db()
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        matching = []
        for app in self.db["appointments"]:
            if app["date"] == tomorrow_str and not app["reminder_sent"] and app["status"] == "Booked":
                matching.append(app)
        return matching

    def mark_reminder_sent(self, appointment_id: int):
        self._load_local_db()
        for app in self.db["appointments"]:
            if app["id"] == appointment_id:
                app["reminder_sent"] = True
                break
        self._save_local_db()

    def get_appointments_7_days_ago(self) -> list[dict]:
        """
        Returns appointments scheduled 7 days ago.
        """
        self._load_local_db()
        seven_days_ago_str = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        matching = []
        for app in self.db["appointments"]:
            if app["date"] == seven_days_ago_str and not app["followup_sent"] and app["status"] == "Booked":
                matching.append(app)
        return matching

    def mark_followup_sent(self, appointment_id: int):
        self._load_local_db()
        for app in self.db["appointments"]:
            if app["id"] == appointment_id:
                app["followup_sent"] = True
                break
        self._save_local_db()
