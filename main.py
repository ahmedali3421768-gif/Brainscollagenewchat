from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from groq import Groq
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from prompt import SYSTEM_PROMPT
load_dotenv()

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)



app = FastAPI(title="Brains College Chatbot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_groq_client = None

def get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in .env file")
        _groq_client = Groq(api_key=api_key)
    return _groq_client

# =====================================================
# GOOGLE SHEETS — Leads only
# Leads tab = form submissions (name, phone, campus)
# Chat messages are NOT stored.
# =====================================================
def get_spreadsheet():
    try:
        creds_file = Path(__file__).parent / "google_credentials.json"
        if not creds_file.exists():
            print("google_credentials.json not found")
            return None
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(str(creds_file), scopes=scopes)
        client = gspread.authorize(creds)
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            print("GOOGLE_SHEET_ID not set")
            return None
        return client.open_by_key(sheet_id)
    except Exception as e:
        print(f"Google Sheets connection error: {e}")
        return None

def ensure_leads_sheet(spreadsheet):
    """Make sure the Leads tab exists with correct headers."""
    try:
        try:
            leads_sheet = spreadsheet.worksheet("Leads")
        except gspread.WorksheetNotFound:
            leads_sheet = spreadsheet.add_worksheet(title="Leads", rows=1000, cols=5)
            leads_sheet.append_row(["Timestamp", "Name", "Phone Number", "Campus", "Status"])
        return leads_sheet
    except Exception as e:
        print(f"Header setup error: {e}")
        return None

def log_lead_to_sheet(name: str, phone: str, campus: str):
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return False, "Google Sheets not configured"
        leads_sheet = ensure_leads_sheet(spreadsheet)
        if not leads_sheet:
            return False, "Could not access Leads sheet"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        leads_sheet.append_row([timestamp, name, phone, campus, "New"])
        return True, "Lead saved successfully"
    except Exception as e:
        print(f"Lead log error: {e}")
        return False, str(e)

# =====================================================
# MODELS
# =====================================================
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    temperature: Optional[float] = 0.6
    max_tokens: Optional[int] = 1024

class ChatResponse(BaseModel):
    reply: str
    success: bool
    error: Optional[str] = None

class LeadRequest(BaseModel):
    name: str
    phone: str
    campus: str

class LeadResponse(BaseModel):
    success: bool
    message: str

# =====================================================
# ROUTES
# =====================================================
@app.get("/")
async def root():
    index_file = static_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found in static/")
    return FileResponse(str(index_file))

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        groq_client = get_groq_client()
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})

        response = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        bot_reply = response.choices[0].message.content

        return ChatResponse(reply=bot_reply, success=True)

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/lead", response_model=LeadResponse)
async def submit_lead(request: LeadRequest):
    """Save a lead (name, phone, campus) to the Leads tab in Google Sheets."""
    # Basic validation
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if not request.phone.strip():
        raise HTTPException(status_code=400, detail="Phone number is required")
    if not request.campus.strip():
        raise HTTPException(status_code=400, detail="Campus selection is required")

    valid_campuses = ["Walton Road", "Queen Road", "Darogwala", "Bhagbanpura"]
    if request.campus not in valid_campuses:
        raise HTTPException(status_code=400, detail=f"Invalid campus. Choose from: {', '.join(valid_campuses)}")

    success, message = log_lead_to_sheet(
        request.name.strip(),
        request.phone.strip(),
        request.campus
    )

    if not success:
        raise HTTPException(status_code=500, detail=message)

    return LeadResponse(success=True, message="Thank you! We'll contact you soon.")

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Brains College Chatbot", "groq_key_set": bool(os.getenv("GROQ_API_KEY"))}

@app.get("/api/sheet-data")
async def get_sheet_data():
    try:
        spreadsheet = get_spreadsheet()
        if not spreadsheet:
            return {"leads": [], "note": "Google Sheets not configured"}
        leads_sheet = ensure_leads_sheet(spreadsheet)
        leads_records = leads_sheet.get_all_records() if leads_sheet else []
        return {"leads": leads_records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")