import asyncio
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from twilio.rest import Client
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

load_dotenv()

app = FastAPI()
from sheets import GoogleSheetsClient
from twilio_client import TwilioClient
sheets = GoogleSheetsClient()
twilio = TwilioClient()
agent_logs = []

def log_agent(agent_name, log_type, content):
    agent_logs.append({"agent": agent_name, "type": log_type, "content": content})
    print(f"[{agent_name}] [{log_type.upper()}] {content}")
base_dir = os.path.dirname(os.path.abspath(__file__))

class ChatRequest(BaseModel):
    message: str
    phone: str = "+1 (555) 019-9999"

@app.get("/api/config")
def get_config_status():
    has_api_key = bool(os.environ.get("GEMINI_API_KEY"))
    return {
        "gemini_api_key": "Configured" if has_api_key else "Missing (Using Simulation Mode)",
        "twilio": "Configured" if twilio.use_real_twilio else "Missing (Using Sandbox Simulator)",
        "google_sheets": "Configured" if sheets.use_real_sheets else "Missing (Using Local File Database)",
        "demo_mode": not has_api_key
    }

@app.get("/api/appointments")
def get_appointments():
    return sheets.get_appointments()

@app.get("/api/slots")
def get_slots():
    return sheets.get_slots_raw()

@app.get("/api/messages")
def get_messages():
    return twilio.get_messages()

@app.get("/api/agent-logs")
def get_agent_logs():
    agent_logs = []
    return agent_logs

@app.post("/api/clear-logs")
def clear_logs():
    agent_logs.clear()
    return {"status": "success"}
@app.post("/api/reset-db")
def reset_db():
    sheets.db = {"appointments": [], "slots": {}}
    sheets._save_local_db()
    return {"status": "success"}

@app.post("/api/chat")
async def chat_intake_and_schedule(req: ChatRequest):
    has_api_key = bool(os.environ.get("GEMINI_API_KEY"))
    
    log_agent("System", "info", f"Received message: '{req.message}' from phone: {req.phone}")
    
    if not has_api_key:
        # Run in Simulated Demo Mode
        return await simulate_multi_agent_flow(req.message, req.phone)
    
    try:
        from google.antigravity import Agent
        
        # 1. RUN AGENT 1 (Intake Agent)
        log_agent("Intake Agent", "info", "Initializing intake process...")
        intake_config = ags.get_intake_agent_config()
        
        extracted_data = None
        async with Agent(intake_config) as agent1:
            log_agent("Intake Agent", "info", "Sending prompt to extract details...")
            prompt = f"Today's date is {datetime.now().strftime('%Y-%m-%d')}. Patient message: {req.message}. Patient phone: {req.phone}"
            
            # Setup logging tasks
            response = await agent1.chat(prompt)
            
            async def log_thoughts():
                async for thought in response.thoughts:
                    log_agent("Intake Agent", "thought", thought)
            asyncio.create_task(log_thoughts())
            
            # Await final structured result
            extracted_data = await response.structured_output()
            
        if not extracted_data:
            log_agent("Intake Agent", "error", "Failed to extract structured data.")
            raise HTTPException(status_code=500, detail="Intake Agent extraction failed")
            
        log_agent("Intake Agent", "response", f"Extracted: Name: {extracted_data.patient_name}, Date: {extracted_data.preferred_date}, Symptoms: {extracted_data.symptoms}")
        
        # 2. RUN AGENT 2 (Scheduling Agent)
        log_agent("Scheduling Agent", "info", "Initializing booking workflow...")
        sched_config = ags.get_scheduling_agent_config()
        
        async with Agent(sched_config) as agent2:
            prompt_sched = (
                f"Schedule an appointment for: \n"
                f"Name: {extracted_data.patient_name}\n"
                f"Phone: {extracted_data.phone}\n"
                f"Symptoms: {extracted_data.symptoms}\n"
                f"Preferred Date: {extracted_data.preferred_date}\n"
            )
            response2 = await agent2.chat(prompt_sched)
            
            # Tasks to log thoughts and tool calls
            async def log_sched_thoughts():
                async for thought in response2.thoughts:
                    log_agent("Scheduling Agent", "thought", thought)
                    
            async def log_sched_tools():
                async for call in response2.tool_calls:
                    log_agent("Scheduling Agent", "tool_call", f"Executing {call.name}({call.args})")
                    
            asyncio.create_task(log_sched_thoughts())
            asyncio.create_task(log_sched_tools())
            
            final_text = await response2.text()
            log_agent("Scheduling Agent", "response", final_text)
            
        return {
            "status": "success",
            "extracted": extracted_data.dict(),
            "scheduling_response": final_text
        }
        
    except Exception as e:
        log_agent("System", "error", f"Execution error: {str(e)}")
        # If real agent fails due to API quota, connection, or setup error, fallback to simulation so the UI remains interactive
        log_agent("System", "info", "Falling back to simulation mode due to agent error.")
        return await simulate_multi_agent_flow(req.message, req.phone, was_fallback=True)

@app.post("/api/trigger-reminder")
async def trigger_reminder_agent():
    has_api_key = bool(os.environ.get("GEMINI_API_KEY"))
    log_agent("Reminder Agent", "info", "Starting scan for tomorrow's appointments...")
    
    if not has_api_key:
        return await simulate_reminder_flow()
        
    try:
        from google.antigravity import Agent
        config = ags.get_reminder_agent_config()
        async with Agent(config) as agent:
            response = await agent.chat("Scan database and send reminders for tomorrow's appointments.")
            
            async def log_thoughts():
                async for thought in response.thoughts:
                    log_agent("Reminder Agent", "thought", thought)
            async def log_tools():
                async for call in response.tool_calls:
                    log_agent("Reminder Agent", "tool_call", f"Executing {call.name}({call.args})")
                    
            asyncio.create_task(log_thoughts())
            asyncio.create_task(log_tools())
            
            result_text = await response.text()
            log_agent("Reminder Agent", "response", result_text)
            return {"status": "success", "response": result_text}
    except Exception as e:
        log_agent("Reminder Agent", "error", f"Failed with error: {e}. Falling back to simulation.")
        return await simulate_reminder_flow()

@app.post("/api/trigger-followup")
async def trigger_followup_agent():
    has_api_key = bool(os.environ.get("GEMINI_API_KEY"))
    log_agent("Return Visit Agent", "info", "Starting scan for completed appointments (7 days ago)...")
    
    if not has_api_key:
        return await simulate_followup_flow()
        
    try:
        from google.antigravity import Agent
        config = ags.get_return_visit_agent_config()
        async with Agent(config) as agent:
            response = await agent.chat("Scan database and send return visit followups for appointments 7 days ago.")
            
            async def log_thoughts():
                async for thought in response.thoughts:
                    log_agent("Return Visit Agent", "thought", thought)
            async def log_tools():
                async for call in response.tool_calls:
                    log_agent("Return Visit Agent", "tool_call", f"Executing {call.name}({call.args})")
                    
            asyncio.create_task(log_thoughts())
            asyncio.create_task(log_tools())
            
            result_text = await response.text()
            log_agent("Return Visit Agent", "response", result_text)
            return {"status": "success", "response": result_text}
    except Exception as e:
        log_agent("Return Visit Agent", "error", f"Failed with error: {e}. Falling back to simulation.")
        return await simulate_followup_flow()


# ========================================================
# Simulation Engine (Fallbacks / API key-less running)
# ========================================================

async def simulate_multi_agent_flow(message: str, phone: str, was_fallback: bool = False):
    suffix = " (Fallback Sim)" if was_fallback else " (Simulated)"
    
    # 1. Simulate Intake Agent
    log_agent(f"Intake Agent{suffix}", "thought", "Parsing patient message for details...")
    await asyncio.sleep(0.8)
    log_agent(f"Intake Agent{suffix}", "thought", "Resolving date expressions relative to today...")
    await asyncio.sleep(0.6)
    
    # Simple extraction heuristic for the demo
    words = message.lower()
    patient_name = "Jane Doe"
    for name in ["clara", "john", "alice", "bob", "david", "sarah", "emma", "clara oswald"]:
        if name in words:
            patient_name = name.title()
            break
            
    # Symptoms
    symptoms = "General checkup"
    for sym in ["headache", "throat", "fever", "cough", "pain", "stomach"]:
        if sym in words:
            symptoms = f"Sore {sym}" if sym == "throat" else f"Severe {sym}"
            break
            
    # Preferred Date
    pref_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d") # default tomorrow
    if "today" in words:
        pref_date = datetime.now().strftime("%Y-%m-%d")
    elif "day after tomorrow" in words:
        pref_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        
    log_agent(f"Intake Agent{suffix}", "response", f"Patient details extracted: Name='{patient_name}', Date='{pref_date}', Symptoms='{symptoms}'")
    
    # 2. Simulate Scheduling Agent
    log_agent(f"Scheduling Agent{suffix}", "thought", f"Checking slots for date: {pref_date}")
    await asyncio.sleep(0.7)
    
    available = sheets.check_available_slots(pref_date)
    log_agent(f"Scheduling Agent{suffix}", "tool_call", f"check_available_slots(date='{pref_date}')")
    await asyncio.sleep(0.4)
    log_agent(f"Scheduling Agent{suffix}", "tool_result", f"Slots found: {available}")
    
    if not available:
        log_agent(f"Scheduling Agent{suffix}", "thought", f"No slots on {pref_date}. Checking next day.")
        next_day = (datetime.strptime(pref_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        available = sheets.check_available_slots(next_day)
        pref_date = next_day
        
    selected_time = available[0] if available else "10:00 AM"
    
    log_agent(f"Scheduling Agent{suffix}", "thought", f"Selecting {selected_time} for booking.")
    await asyncio.sleep(0.5)
    log_agent(f"Scheduling Agent{suffix}", "tool_call", f"book_slot(patient_name='{patient_name}', phone='{phone}', symptoms='{symptoms}', date='{pref_date}', time='{selected_time}')")
    
    app_details = sheets.book_slot(pref_date, selected_time, patient_name, phone, symptoms)
    await asyncio.sleep(0.4)
    log_agent(f"Scheduling Agent{suffix}", "tool_result", f"Booking complete. Appointment ID: {app_details['id'] if app_details else 'Error'}")
    
    # Send WhatsApp Message
    msg_body = f"Hello {patient_name}, your healthcare appointment has been booked for {pref_date} at {selected_time}. Please reply if you need to reschedule."
    log_agent(f"Scheduling Agent{suffix}", "tool_call", f"send_whatsapp_confirmation(to='{phone}', body='{msg_body}')")
    twilio.send_whatsapp(phone, msg_body, f"Scheduling Agent{suffix}")
    await asyncio.sleep(0.5)
    
    log_agent(f"Scheduling Agent{suffix}", "response", f"Confirmed appointment slot {selected_time} on {pref_date} for {patient_name}.")
    
    return {
        "status": "success",
        "extracted": {
            "patient_name": patient_name,
            "phone": phone,
            "symptoms": symptoms,
            "preferred_date": pref_date
        },
        "scheduling_response": f"Successfully scheduled at {selected_time} on {pref_date}."
    }

async def simulate_reminder_flow():
    suffix = " (Simulated)"
    log_agent(f"Reminder Agent{suffix}", "thought", "Fetching tomorrow's appointments...")
    await asyncio.sleep(0.6)
    
    upcoming = sheets.get_appointments_in_24h()
    log_agent(f"Reminder Agent{suffix}", "tool_call", "get_upcoming_appointments_in_24h()")
    await asyncio.sleep(0.4)
    log_agent(f"Reminder Agent{suffix}", "tool_result", f"Found {len(upcoming)} pending reminders.")
    
    if not upcoming:
        log_agent(f"Reminder Agent{suffix}", "response", "No reminders to send today.")
        return {"status": "success", "message": "No reminders sent."}
        
    for app in upcoming:
        msg = f"Reminder: Hello {app['patient_name']}, you have an appointment tomorrow, {app['date']} at {app['time']}. Please remember to bring your prescription details."
        log_agent(f"Reminder Agent{suffix}", "tool_call", f"send_whatsapp_reminder(to='{app['phone']}', body='{msg}')")
        twilio.send_whatsapp(app["phone"], msg, f"Reminder Agent{suffix}")
        await asyncio.sleep(0.5)
        
        log_agent(f"Reminder Agent{suffix}", "tool_call", f"mark_reminder_as_sent(appointment_id={app['id']})")
        sheets.mark_reminder_sent(app["id"])
        await asyncio.sleep(0.3)
        
    log_agent(f"Reminder Agent{suffix}", "response", f"Successfully dispatched reminders for {len(upcoming)} appointments.")
    return {"status": "success", "count": len(upcoming)}

async def simulate_followup_flow():
    suffix = " (Simulated)"
    log_agent(f"Return Visit Agent{suffix}", "thought", "Fetching appointments from 7 days ago...")
    await asyncio.sleep(0.6)
    
    past = sheets.get_appointments_7_days_ago()
    log_agent(f"Return Visit Agent{suffix}", "tool_call", "get_past_appointments_7_days_ago()")
    await asyncio.sleep(0.4)
    log_agent(f"Return Visit Agent{suffix}", "tool_result", f"Found {len(past)} pending followups.")
    
    if not past:
        # Create a mock old appointment so testing the return visit flow is easy and doesn't require waiting 7 days!
        log_agent(f"Return Visit Agent{suffix}", "info", "No old appointments found. Generating a mock 7-day-old appointment record for demonstration.")
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        sheets.db["appointments"].append({
            "id": len(sheets.db["appointments"]) + 1,
            "patient_name": "Marcus Aurelius",
            "phone": "+1 (555) 777-8888",
            "symptoms": "Mild fever",
            "date": seven_days_ago,
            "time": "11:00 AM",
            "status": "Booked",
            "booked_at": datetime.now().isoformat(),
            "reminder_sent": True,
            "followup_sent": False
        })
        sheets._save_local_db()
        # Fetch again
        past = sheets.get_appointments_7_days_ago()
        
    for app in past:
        msg = f"Hello {app['patient_name']}, it has been 7 days since your appointment. We hope you are feeling better. If you need a follow-up or a return visit, please book using our platform!"
        log_agent(f"Return Visit Agent{suffix}", "tool_call", f"send_whatsapp_followup(to='{app['phone']}', body='{msg}')")
        twilio.send_whatsapp(app["phone"], msg, f"Return Visit Agent{suffix}")
        await asyncio.sleep(0.5)
        
        log_agent(f"Return Visit Agent{suffix}", "tool_call", f"mark_followup_as_sent(appointment_id={app['id']})")
        sheets.mark_followup_sent(app["id"])
        await asyncio.sleep(0.3)
        
    log_agent(f"Return Visit Agent{suffix}", "response", f"Successfully dispatched followups for {len(past)} appointments.")
    return {"status": "success", "count": len(past)}


# Serve static frontend dashboard
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Generate static files directory if not exists
    os.makedirs("static", exist_ok=True)
    uvicorn.run(app, host="127.0.0.1", port=8000)
