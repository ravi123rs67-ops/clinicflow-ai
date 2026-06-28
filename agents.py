import os
from pydantic import BaseModel, Field
from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
from sheets import GoogleSheetsClient
from twilio_client import TwilioClient

# Create shared instances for the tools
sheets_client = GoogleSheetsClient()
twilio_client = TwilioClient()

# ==========================================
# Pydantic Schemas for Agent Outputs
# ==========================================

class PatientIntake(BaseModel):
    patient_name: str = Field(description="The full name of the patient.")
    phone: str = Field(description="The patient's phone number.")
    symptoms: str = Field(description="Brief summary of symptoms or reason for visit.")
    preferred_date: str = Field(description="Preferred appointment date in YYYY-MM-DD format. Resolve strings like 'tomorrow' or 'next Monday' to actual YYYY-MM-DD string using current date context.")

# ==========================================
# Tool definitions for Agent 2: Scheduling Agent
# ==========================================

def check_available_slots(date: str) -> list[str]:
    """
    Check the available appointment slot times for a given date in YYYY-MM-DD format.
    
    Args:
        date: The date to check in YYYY-MM-DD format.
        
    Returns:
        A list of available time slot strings (e.g. ['09:00 AM', '10:00 AM']).
    """
    return sheets_client.check_available_slots(date)

def book_slot(patient_name: str, phone: str, symptoms: str, date: str, time: str) -> str:
    """
    Book an appointment slot on a specific date (YYYY-MM-DD) and time (e.g. '10:00 AM').
    
    Args:
        patient_name: The patient's full name.
        phone: The patient's phone number.
        symptoms: The patient's symptoms.
        date: The date of the slot in YYYY-MM-DD format.
        time: The time of the slot (e.g. '10:00 AM').
        
    Returns:
        A success/failure message string.
    """
    result = sheets_client.book_slot(date, time, patient_name, phone, symptoms)
    if result:
        return f"Successfully booked appointment ID {result['id']} for {patient_name} at {time} on {date}."
    return "Failed to book appointment. Slot may be unavailable."

def send_whatsapp_confirmation(to_number: str, message_body: str) -> str:
    """
    Send a WhatsApp booking confirmation message to the patient's phone number.
    
    Args:
        to_number: The patient's phone number.
        message_body: The content of the WhatsApp message.
        
    Returns:
        A status message indicating success or failure.
    """
    success = twilio_client.send_whatsapp(to_number, message_body, "Scheduling Agent")
    return "WhatsApp message sent successfully." if success else "Failed to send WhatsApp message."

# ==========================================
# Tool definitions for Agent 3: Reminder Agent
# ==========================================

def get_upcoming_appointments_in_24h() -> list[dict]:
    """
    Retrieve all appointments scheduled for tomorrow that have not received reminders yet.
    
    Returns:
        A list of appointment dictionaries.
    """
    return sheets_client.get_appointments_in_24h()

def mark_reminder_as_sent(appointment_id: int) -> str:
    """
    Mark an appointment ID as having received its 24-hour reminder.
    
    Args:
        appointment_id: The unique ID of the appointment.
        
    Returns:
        Status string.
    """
    sheets_client.mark_reminder_sent(appointment_id)
    return f"Appointment {appointment_id} marked as reminder sent."

def send_whatsapp_reminder(to_number: str, message_body: str) -> str:
    """
    Send a WhatsApp reminder message to the patient's phone number.
    
    Args:
        to_number: The patient's phone number.
        message_body: The reminder message content.
        
    Returns:
        Status string.
    """
    success = twilio_client.send_whatsapp(to_number, message_body, "Reminder Agent")
    return "Reminder sent successfully." if success else "Failed to send reminder."

# ==========================================
# Tool definitions for Agent 4: Return Visit Agent
# ==========================================

def get_past_appointments_7_days_ago() -> list[dict]:
    """
    Retrieve all appointments that were scheduled exactly 7 days ago and need a follow-up visit invitation.
    
    Returns:
        A list of appointment dictionaries.
    """
    return sheets_client.get_appointments_7_days_ago()

def mark_followup_as_sent(appointment_id: int) -> str:
    """
    Mark an appointment ID as having received its 7-day follow-up message.
    
    Args:
        appointment_id: The unique ID of the appointment.
        
    Returns:
        Status string.
    """
    sheets_client.mark_followup_sent(appointment_id)
    return f"Appointment {appointment_id} marked as follow-up sent."

def send_whatsapp_followup(to_number: str, message_body: str) -> str:
    """
    Send a WhatsApp follow-up invitation to the patient's phone number.
    
    Args:
        to_number: The patient's phone number.
        message_body: The follow-up message content.
        
    Returns:
        Status string.
    """
    success = twilio_client.send_whatsapp(to_number, message_body, "Return Visit Agent")
    return "Follow-up message sent successfully." if success else "Failed to send follow-up message."

# ==========================================
# Agent Configuration Factories
# ==========================================

def get_intake_agent_config(api_key: str = None) -> LocalAgentConfig:
    key = api_key or os.environ.get("GEMINI_API_KEY")
    return LocalAgentConfig(
        system_instructions=(
            "You are the Intake Agent (Agent 1) in a healthcare booking system. "
            "Your job is to parse the patient's message and extract the following: "
            "1. Patient Name "
            "2. Phone number "
            "3. Symptoms "
            "4. Preferred appointment date (e.g. YYYY-MM-DD). "
            "Note: Make sure to convert relative dates (like 'tomorrow', 'next Monday') "
            "into YYYY-MM-DD format using today's date."
        ),
        response_schema=PatientIntake,
        capabilities=CapabilitiesConfig(),
        api_key=key
    )

def get_scheduling_agent_config(api_key: str = None) -> LocalAgentConfig:
    key = api_key or os.environ.get("GEMINI_API_KEY")
    return LocalAgentConfig(
        system_instructions=(
            "You are the Scheduling Agent (Agent 2). "
            "You receive patient data (name, phone, symptoms, preferred date). "
            "Your workflow is: "
            "1. Call check_available_slots to see if any times are free on that date. "
            "2. If slots are available, select one (e.g. the earliest slot) and book it using book_slot. "
            "3. If no slots are available, check other days or notify the system. "
            "4. After booking, send a WhatsApp confirmation message using send_whatsapp_confirmation. "
            "The message should be polite and confirm the name, date, time, and doctor info."
        ),
        tools=[check_available_slots, book_slot, send_whatsapp_confirmation],
        capabilities=CapabilitiesConfig(),
        api_key=key
    )

def get_reminder_agent_config(api_key: str = None) -> LocalAgentConfig:
    key = api_key or os.environ.get("GEMINI_API_KEY")
    return LocalAgentConfig(
        system_instructions=(
            "You are the Reminder Agent (Agent 3). "
            "Your job is to send appointment reminders: "
            "1. Retrieve tomorrow's appointments using get_upcoming_appointments_in_24h. "
            "2. For each appointment, send a WhatsApp reminder using send_whatsapp_reminder. "
            "3. Mark the reminder as sent using mark_reminder_as_sent so they are not reminded again."
        ),
        tools=[get_upcoming_appointments_in_24h, mark_reminder_as_sent, send_whatsapp_reminder],
        capabilities=CapabilitiesConfig(),
        api_key=key
    )

def get_return_visit_agent_config(api_key: str = None) -> LocalAgentConfig:
    key = api_key or os.environ.get("GEMINI_API_KEY")
    return LocalAgentConfig(
        system_instructions=(
            "You are the Return Visit Agent (Agent 4). "
            "Your job is to follow up with patients 7 days after their appointment: "
            "1. Retrieve past appointments from 7 days ago using get_past_appointments_7_days_ago. "
            "2. For each appointment, send a WhatsApp follow-up using send_whatsapp_followup. "
            "Ask about their health, if the treatment helped, and invite them to book a return visit if needed. "
            "3. Mark the follow-up as sent using mark_followup_as_sent."
        ),
        tools=[get_past_appointments_7_days_ago, mark_followup_as_sent, send_whatsapp_followup],
        capabilities=CapabilitiesConfig(),
        api_key=key
    )
