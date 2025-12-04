# Mira AI Agent 🤖

Mira is an intelligent Technical Program Management (TPM) assistant. It streamlines project planning and weekly status reporting using AI, allowing TPMs to focus on strategy rather than documentation.

**🔗 Live App:** [https://mira-ai-agent.streamlit.app/](https://mira-ai-agent.streamlit.app/)

---

## 🛠️ Tech Stack
![Python](https://img.shields.io/badge/Python-3670A0?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?logo=openai&logoColor=white)
![Trello](https://img.shields.io/badge/Trello-0052CC?logo=trello&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)
![Gmail](https://img.shields.io/badge/Gmail-EA4335?logo=gmail&logoColor=white)

---

## Key Features

### 1. 📅 Intelligent Project Planning
Upload unstructured project documents (PRDs, Timelines, Meeting Notes) to generate a comprehensive, structured Project Plan.
- **Supported Formats:** PDF, DOCX, TXT, Excel.
- **Output:** Professional Execution Plan including Executive Summary, Timeline, Risks, and Resource Requirements.
- **Downloads:** PDF, Word (DOCX), Markdown, Plain Text.

### 2. 📊 Automated Status Reporting
Connect your Trello board to instantly generate weekly status reports.
- **Integration:** Works with Trello Board IDs or direct URLs.
- **Analysis:** Categorizes Completed vs. In-Progress tasks.
- **Risk Detection:** Automatically identifies potential blockers and risks.
- **Output:** Executive-ready status emails and documents.

### 3. 📤 One-Click Sharing
- **Direct Email:** Send formatted reports directly to stakeholders from the app.
- **Multi-Format Export:** Download reports in the format that fits your workflow (PDF for sharing, DOCX for editing, MD for documentation).

---

## How to Use

### Setup API Keys
To use Mira, you simply need to enter your credentials in the sidebar configuration. No local setup required.

1.  **OpenAI API Key:** Required for AI generation.
2.  **Trello Credentials:** (For Status Reports)
    *   Get your Key & Token from [Trello Power-Ups Admin](https://trello.com/power-ups/admin).
3.  **Email App Password:** (For Sending Emails)
    *   Go to your Google Account > Security > 2-Step Verification > App Passwords.
    *   Generate a new password for "Mail" / "Mira Agent".
    *   Use this 16-character code in the "App Password" field in the UI.

### Generating a Project Plan
1.  Go to the **Project Planning** tab.
2.  Upload your project files (e.g., `Project_Scope.pdf`, any docx, xlsx, txt and pdf files).
3.  Click **Generate Plan**.
4.  Review the plan and download it as a PDF or Word Doc.

### Generating a Status Report
1.  Go to the **Status Reports** tab.
2.  Enter your **Trello Board URL** (e.g., `https://trello.com/b/ID/name`).
3.  Click **Generate Report**.
4.  Edit or review the output, then click **Send Email** to forward it to your team.

---

## Tech Stack
- **Frontend:** Streamlit
- **AI Logic:** OpenAI GPT-4o / GPT-3.5
- **Document Processing:** PyPDF2, python-docx, BeautifulSoup, Pandas
- **Integrations:** Trello API, SMTP (Gmail)
- **Deployment:** Streamlit Community Cloud
