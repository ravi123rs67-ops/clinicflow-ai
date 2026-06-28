# ClinicFlow AI — Multi-Agent Healthcare Booking System

A 4-agent AI system built with Google ADK 2.0 and Antigravity for automating clinic appointment booking.

## Agents
- Agent 1: Intake Agent — extracts patient name, symptoms, preferred date
- Agent 2: Scheduling Agent — books appointment slot, sends WhatsApp confirmation
- Agent 3: Reminder Agent — sends 24h reminder before appointment
- Agent 4: Return Visit Agent — sends 7-day follow-up to bring patients back

## Tech Stack
- Google ADK 2.0 + Antigravity
- FastAPI + Python
- Twilio WhatsApp
- Google Gemini API

## Setup
1. Clone the repo
2. Create .env file with GEMINI_API_KEY and TWILIO credentials
3. Run: pip install -r requirements.txt
4. Run: python main.py
5. Open: http://127.0.0.1:8000
