# Cartly — Voice-Driven Shopping List & Natural Language Commerce

![Cartly Newspaper Edition](data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 120' fill='%23f6f2e8'><rect width='800' height='120' fill='%23f6f2e8'/><text x='400' y='75' font-family='Georgia,serif' font-size='48' font-weight='bold' text-anchor='middle' fill='%231b1917'>THE CARTLY GAZETTE</text></svg>)

**Cartly** is an independent, privacy-first, voice-driven shopping list and natural-language commerce app. Designed with a vintage **Newspaper Gazette layout**, Cartly allows users to speak naturally or type commands to manage household grocery lists, search product catalogs, and receive explainable market recommendations.

---

## Key Features

- 📰 **Vintage Newspaper UI ("The Cartly Gazette")**: Multi-column editorial front-page layout, telegraph microphone console, paper parchment palette, and classified-style household ledger.
- 🎙️ **Voice Dispatch & Web Speech Integration**: Seamless voice recognition with real-time telegraph transcript readout, support for multiple languages, and fallback typed input.
- 🧠 **Deterministic Natural Language Parser**: Fast Python intent parser that extracts items, quantities, units, brands, and price limits without mandatory external cloud APIs.
- 💡 **Explainable Market Recommendations**: Smart suggestions based on local purchase history, seasonal produce data, and item pairing rules.
- 🔒 **Privacy-First & Serverless Local Storage**: Shopping list data remains entirely inside your browser (`localStorage`). No user tracking or account required.
- 📖 **Built-in OpenAPI & Interactive Documentation**: Full REST API documentation automatically served by FastAPI at `/docs` and `/redoc`.

---

## Quickstart & Local Setup

### 1. Prerequisites
- **Python 3.11+** installed on your system.

### 2. Install Dependencies
```bash
# Optional: Create and activate a virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Run Development Server
```bash
uvicorn app.main:app --reload
```

Once running, open your browser and navigate to:
- **Application Web Interface**: `http://localhost:8000/`
- **Interactive API Documentation (Swagger)**: `http://localhost:8000/docs`
- **Alternative API Documentation (ReDoc)**: `http://localhost:8000/redoc`

---

## API Endpoints Overview

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/parse` | `POST` | Parse natural language voice/text commands into structured intent objects. |
| `/api/search` | `GET` | Search product catalog by query, category, price, and attributes. |
| `/api/suggestions` | `POST` | Get personalized item recommendations based on basket history and seasonal trends. |
| `/api/languages` | `GET` | Retrieve supported speech recognition languages and locale information. |
| `/healthz` | `GET` | Plain liveness check for hosting platforms. |
| `/docs` | `GET` | Interactive Swagger UI API Documentation for **Cartly**. |

---

## Running Unit & Integration Tests

Cartly includes a comprehensive test suite covering command parsing, catalog search, recommendation engine, multilingual support, and API endpoints.

```bash
# Run pytest test suite
pytest
```

---

## Pushing to Your Own GitHub Repository

Cartly has been completely decoupled from external remotes. To push this project to your personal GitHub account:

```bash
# Initialize a new git repository
git init

# Add all project files
git add .

# Create initial commit
git commit -m "Initial release of Cartly Newspaper Edition"

# Set main branch and link your personal GitHub remote
git branch -M main
git remote add origin https://github.com/<your-username>/cartly.git

# Push to your GitHub repository
git push -u origin main
```

---

## Project Structure

```text
unthinkable/
├── app/
│   ├── api/          # FastAPI routes and schemas
│   ├── catalog/      # Product catalog and search engine
│   ├── nlp/          # Natural language command parser & multilingual rules
│   ├── recommend/    # Recommendation engine & seasonal rules
│   ├── main.py       # FastAPI application entry point & API docs
│   └── models.py     # Pydantic data models
├── web/
│   ├── index.html    # Vintage Newspaper Gazette frontend
│   ├── styles.css    # Newspaper editorial stylesheet
│   └── js/           # Modular ES JS (app.js, speech.js, ui.js, store.js, api.js)
├── tests/            # Automated test suite (380+ tests)
├── pyproject.toml    # Python project configuration
├── requirements.txt  # Dependencies
└── README.md         # Project documentation
```

---

*Powered by FastAPI, Web Speech API, and Python.*
