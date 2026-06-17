# 🎓 Brains College — AI Chatbot

A floating AI chatbot widget with a FastAPI backend, Groq LLM, and Google Sheets logging.

---

## 📁 File Structure

```
chatbot/
├── main.py                          # FastAPI backend
├── requirements.txt                 # Python dependencies
├── .env                             # Your secrets (copy from .env.example)
├── google_credentials.json          # Your GCP service account key
├── .env.example                     # Template for .env
├── google_credentials.example.json  # Template for GCP credentials
└── static/
    ├── index.html                   # Main HTML (embed this in your site)
    ├── style.css                    # All styles
    └── chatbot.js                   # Chatbot logic
```

---

## 🚀 Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in GROQ_API_KEY and GOOGLE_SHEET_ID
```

### 3. Set up Google Sheets
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → Download JSON key → save as `google_credentials.json`
4. Create a Google Sheet with columns: `Timestamp | User Message | Bot Reply`
5. Share the sheet with your service account email (Editor access)
6. Copy the Sheet ID from the URL into `.env`

### 4. Run the server
```bash
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000` — the chatbot widget appears at the bottom-right.

---

## 🌐 Embedding in Your Existing Website

Instead of using `index.html` as a full page, copy just these 3 things into your existing site:

**In `<head>`:**
```html
<link rel="stylesheet" href="/static/style.css" />
```

**Before `</body>`:**
```html
<!-- Chatbot trigger button -->
<button class="chat-trigger" id="chatTrigger" ...> ... </button>
<!-- Chatbot panel -->
<aside class="chat-panel" id="chatPanel" ...> ... </aside>
<!-- Overlay -->
<div class="chat-overlay" id="chatOverlay"></div>

<script src="/static/chatbot.js"></script>
```

The widget background is **fully transparent** (`backdrop-filter: blur`) so your website shows through.

---

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Send a message, get AI reply |
| `GET`  | `/api/sheet-data` | Fetch all conversation logs |
| `GET`  | `/api/health` | Health check |

### Chat request body
```json
{
  "messages": [
    { "role": "user", "content": "What are the admission requirements?" }
  ],
  "temperature": 0.7,
  "max_tokens": 1024
}
```

---

## 🎨 Customization

Edit `style.css` CSS variables at the top to change colors:

```css
:root {
  --g-brand: linear-gradient(135deg, #7C3AED 0%, #2563EB 55%, #06B6D4 100%);
  --c-accent: #7C3AED;
  --panel-w: 380px;   /* chatbot width */
  --panel-h: 580px;   /* chatbot height */
}
```

Edit the `SYSTEM_PROMPT` in `main.py` to customize the AI's personality and knowledge.
