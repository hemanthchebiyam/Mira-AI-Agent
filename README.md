# Mira AI Agent 🤖

Mira is a Technical Program Management (TPM) assistant built with Streamlit. It helps streamline project planning and status reporting using AI.

## Features

- **Project Planning**: Upload PRDs and Timeline documents (PDF, DOCX, TXT) to generate execution plans.
- **Status Reporting**: Connects to Trello to generate weekly status reports, executive summaries, and risk assessments.
- **Export & Share**: Save reports as Markdown/PDF or email them directly.

## Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Mira-AI-Agent
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     # On Windows: copy .env.example .env
     ```
   - Open `.env` and fill in your API keys:
     - `OPENAI_API_KEY`: Your OpenAI API key.
     - `TRELLO_API_KEY` & `TRELLO_TOKEN`: From [Trello Power-Ups](https://trello.com/power-ups/admin).
     - `TRELLO_BOARD_ID`: (Optional) Default board ID to load.
     - `EMAIL_SENDER` & `EMAIL_PASSWORD`: (Optional) For sending reports via email.

## Run the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

