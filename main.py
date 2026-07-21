from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from groq import Groq
import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import time
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from prompt import SYSTEM_PROMPT

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# =====================================================
# SINGLETONS — created once at startup
# =====================================================
_groq_client = None
_gspread_client = None
_spreadsheet = None

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

LEADS_HEADERS = ["Timestamp", "Name", "Phone Number", "Campus", "Status"]

VALID_CAMPUSES = ["Walton Road", "Queen Road", "Darogwala", "Bhagbanpura"]


# ── Groq ──────────────────────────────────────────
def get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in .env file")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


# ── Google Sheets ──────────────────────────────────
import json

def get_gspread_client():
    global _gspread_client

    if _gspread_client is None:

        creds_json = os.getenv("GOOGLE_CREDENTIALS")

        if creds_json:
            creds_dict = json.loads(creds_json)

            creds = Credentials.from_service_account_info(
                creds_dict,
                scopes=SCOPES
            )

        else:
            creds_file = Path(__file__).parent / "google_credentials.json"

            if not creds_file.exists():
                raise FileNotFoundError(
                    "Neither GOOGLE_CREDENTIALS nor google_credentials.json found."
                )

            creds = Credentials.from_service_account_file(
                str(creds_file),
                scopes=SCOPES
            )

        _gspread_client = gspread.authorize(creds)

        logger.info("gspread client created successfully.")

    return _gspread_client


def get_spreadsheet():
    """Return a cached Spreadsheet object."""
    global _spreadsheet
    if _spreadsheet is None:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        if not sheet_id:
            raise ValueError("GOOGLE_SHEET_ID is not set in .env file")
        client = get_gspread_client()
        _spreadsheet = client.open_by_key(sheet_id)
        logger.info(f"Opened spreadsheet: {_spreadsheet.title}")
    return _spreadsheet


def get_leads_sheet():
    """
    Return the 'Leads' worksheet, creating it with correct headers if absent.
    Verifies headers are correct even if the sheet already exists.
    """
    ss = get_spreadsheet()

    # Get or create the worksheet
    try:
        ws = ss.worksheet("Leads")
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title="Leads", rows=1000, cols=len(LEADS_HEADERS))
        logger.info("Created 'Leads' worksheet.")

    # Check / fix headers
    existing = ws.row_values(1)
    if existing != LEADS_HEADERS:
        if existing:
            logger.warning(
                f"Header mismatch. Found: {existing}. Re-writing headers."
            )
            ws.update("A1", [LEADS_HEADERS])
        else:
            ws.append_row(LEADS_HEADERS)
        logger.info("Headers written to 'Leads' worksheet.")

    return ws


def _retry(fn, retries: int = 3, delay: float = 2.0):
    """Simple retry wrapper for Google Sheets API calls."""
    last_err = None
    for attempt in range(retries):
        try:
            return fn()
        except APIError as e:
            last_err = e
            if e.response.status_code == 429:          # rate-limited
                wait = delay * (2 ** attempt)
                logger.warning(f"Rate limited by Sheets API. Retrying in {wait}s…")
                time.sleep(wait)
            else:
                raise                                  # non-retriable error
    raise last_err


def log_lead_to_sheet(name: str, phone: str, campus: str) -> tuple[bool, str]:
    """Append one lead row. Returns (success, message)."""
    try:
        ws = get_leads_sheet()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, name, phone, campus, "New"]
        _retry(lambda: ws.append_row(row, value_input_option="USER_ENTERED"))
        logger.info(f"Lead saved: {name} | {phone} | {campus}")
        return True, "Lead saved successfully"
    except FileNotFoundError as e:
        logger.error(str(e))
        return False, str(e)
    except ValueError as e:
        logger.error(str(e))
        return False, str(e)
    except SpreadsheetNotFound:
        logger.error("Spreadsheet not found. Check GOOGLE_SHEET_ID.")
        return False, "Spreadsheet not found. Check GOOGLE_SHEET_ID."
    except Exception as e:
        logger.exception("Unexpected error saving lead.")
        return False, str(e)


# =====================================================
# STARTUP — verify connections early
# =====================================================
@app.on_event("startup")
async def startup_checks():
    # Groq
    try:
        get_groq_client()
        logger.info("✅ Groq client ready.")
    except ValueError as e:
        logger.error(f"❌ Groq setup failed: {e}")

    # Google Sheets
    try:
        get_leads_sheet()
        logger.info("✅ Google Sheets ready. 'Leads' worksheet verified.")
    except Exception as e:
        logger.error(f"❌ Google Sheets setup failed: {e}")


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
            model="openai/gpt-oss-120b",
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        return ChatResponse(reply=response.choices[0].message.content, success=True)

    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Chat API error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/lead", response_model=LeadResponse)
async def submit_lead(request: LeadRequest):
    """Save a lead (name, phone, campus) to the Leads tab in Google Sheets."""
    # Validation
    name = request.name.strip()
    phone = request.phone.strip()
    campus = request.campus.strip()

    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number is required")
    if not campus:
        raise HTTPException(status_code=400, detail="Campus selection is required")
    if campus not in VALID_CAMPUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid campus. Choose from: {', '.join(VALID_CAMPUSES)}",
        )

    success, message = log_lead_to_sheet(name, phone, campus)
    if not success:
        logger.error(f"Lead submission failed: {message}")
        raise HTTPException(status_code=500, detail=f"Could not save lead: {message}")

    return LeadResponse(success=True, message="Thank you! We'll contact you soon.")


@app.get("/api/health")
async def health():
    sheets_ok = False
    sheets_msg = "not checked"
    try:
        get_leads_sheet()
        sheets_ok = True
        sheets_msg = "connected"
    except Exception as e:
        sheets_msg = str(e)

    return {
        "status": "ok",
        "service": "Brains College Chatbot",
        "groq_key_set": bool(os.getenv("GROQ_API_KEY")),
        "google_sheet_id_set": bool(os.getenv("GOOGLE_SHEET_ID")),
        "sheets_status": sheets_msg,
        "sheets_ok": sheets_ok,
    }


@app.get("/api/sheet-data")
async def get_sheet_data():
    try:
        ws = get_leads_sheet()
        records = ws.get_all_records()
        return {"leads": records, "count": len(records)}
    except Exception as e:
        logger.exception("Error fetching sheet data")
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")