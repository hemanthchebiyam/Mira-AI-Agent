# Mira AI Agent 🤖

Mira is an intelligent Technical Program Management (TPM) assistant powered by **LangChain Agentic RAG**. It streamlines project planning, status reporting, and project knowledge retrieval using AI, allowing TPMs to focus on strategy rather than documentation.

**🔗 Live App:** [https://mira-ai-agent.streamlit.app/](https://mira-ai-agent.streamlit.app/)

---

## 🆕 Version 2.2.0 Updates

### 🤖 AI Assistant Tab (Enhanced)

The AI Assistant has been streamlined with a cleaner, more focused interface:

- **Simplified Document Upload:** Direct local file upload with automatic indexing
- **Agentic RAG Architecture:** LangChain-powered agent with tool-calling capabilities
- **Smart Document Search:** Semantic search across all uploaded project documents
- **Integrated Actions:** Generate project plans and status reports directly from chat
- **Conversation Memory:** Multi-turn conversations with context retention
- **Source Citations:** Every answer references the specific document it came from

### 📋 Board Actions Tab (New)

Full CRUD operations for Trello board management:

- **Create Cards:** Add new cards with titles, descriptions, due dates, labels, and members
- **Update Cards:** Modify existing cards, move between lists, update details
- **Comments:** Add comments to any card for team collaboration
- **Checklists:** Create checklists and add items with completion status
- **Archive/Restore:** Archive or restore both cards and lists
- **List Selector:** Load and select lists from dropdown for easier navigation

---

## 🛠️ Tech Stack

![Python](https://img.shields.io/badge/Python-3670A0?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?logo=openai&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?logo=langchain&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-00ADD8?logo=meta&logoColor=white)
![Trello](https://img.shields.io/badge/Trello-0052CC?logo=trello&logoColor=white)
![Gmail](https://img.shields.io/badge/Gmail-EA4335?logo=gmail&logoColor=white)

---

## ✨ Key Features

### 1. 🤖 AI Assistant (LangChain Agentic RAG)

**Chat with your project documents using natural language.** Upload files and Mira will intelligently answer questions with source citations.

- **Document Q&A:** "What are the key milestones?" / "Who is responsible for Phase 2?"
- **Auto-Indexing:** Documents are automatically vectorized using FAISS + OpenAI Embeddings
- **Source Citations:** Every answer cites the specific document it came from
- **Multi-turn Chat:** Follow-up questions with conversation memory
- **Integrated Tools:** Generate plans and reports directly from the chat interface

### 2. 📋 Intelligent Project Planning

Upload unstructured project documents to generate comprehensive, structured Project Plans.

- **Supported Formats:** PDF, DOCX, TXT, Excel
- **Output:** Executive Summary, Timeline, Risks, Resource Requirements
- **Downloads:** PDF, Word (DOCX), Markdown, Plain Text
- **Email:** Send directly to stakeholders

### 3. 📊 Automated Status Reporting

Connect your Trello board to instantly generate weekly status reports.

- **Trello Integration:** Works with Board IDs or URLs
- **Smart Analysis:** Categorizes Completed vs. In-Progress tasks
- **Risk Detection:** Automatically identifies blockers and risks
- **Export:** PDF, DOCX, Markdown with one-click email

### 4. 📋 Trello Board Actions

**Perform CRUD operations on your Trello boards directly from Mira.**

- Create new cards with descriptions, due dates, labels, and members
- Update existing cards (move between lists, edit details)
- Add comments and checklist items
- Archive/restore cards and lists

### 5. 📤 One-Click Sharing

- **Direct Email:** Send formatted reports to stakeholders via Gmail
- **Multi-Format Export:** PDF, DOCX, Markdown, Plain Text

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API Key
- (Optional) Trello API Key & Token

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Mira-AI-Agent.git
cd Mira-AI-Agent

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

### Configuration

#### Environment Variables (Optional)

Create a `.env` file in the project root for database and email configuration:

```bash
# Database Configuration (Optional - enables login and credential storage)
# For SQLite (local development - recommended):
DATABASE_URL=sqlite:///./mira.db

# For PostgreSQL (production):
# DATABASE_URL=postgresql://user:password@localhost:5432/mira_db

# Magic Link Email Configuration (Optional - for login via email)
MAGIC_LINK_SENDER=your_email@gmail.com
MAGIC_LINK_PASSWORD=your_app_password_here
```

**Note:** The database is optional. Without `DATABASE_URL`, the app will work but login features will be disabled. For local development, SQLite is the simplest option.

#### Sidebar Credentials

Enter your credentials in the sidebar:

| Credential             | Required For                  | How to Get                                                   |
| ---------------------- | ----------------------------- | ------------------------------------------------------------ |
| **OpenAI API Key**     | All AI features               | [OpenAI Platform](https://platform.openai.com/api-keys)      |
| **Trello Key & Token** | Status Reports, Board Actions | [Trello Power-Ups Admin](https://trello.com/power-ups/admin) |
| **Gmail App Password** | Email sending                 | Google Account > Security > App Passwords                    |

---

## 📖 How to Use

### AI Assistant (RAG Chat)

1. Go to the **AI Assistant** tab
2. Upload your project documents (PDF, DOCX, TXT, Excel)
3. Wait for auto-indexing to complete
4. Start chatting! Ask questions like:
   - "What are the key milestones?"
   - "Summarize the project scope"
   - "Generate a project plan"
   - "Create a status report for [Trello URL]"

### Project Planning

1. Go to **Project Planning** tab
2. Upload your project files (PRD, Timeline, etc.)
3. Click **Generate Plan**
4. Download as PDF/DOCX or send via email

### Status Reporting

1. Go to **Status Reports** tab
2. Enter your Trello Board URL
3. Click **Generate Report**
4. Review, download, or email to stakeholders

### Trello Board Actions

1. Go to **Board Actions** tab
2. Enter your Board ID/URL and click **Load Lists**
3. Create cards, add comments, manage checklists
4. Archive or restore cards and lists

---

## 🏗️ Architecture

```mermaid
flowchart TB
    subgraph Input["📥 Input Sources"]
        Local["💻 Local Upload"]
        Trello["📋 Trello API"]
    end

    subgraph Processing["⚙️ Processing"]
        DocProc["📄 Document Processor"]
        Splitter["✂️ Text Splitter"]
        Embeddings["🔢 OpenAI Embeddings"]
    end

    subgraph Storage["🗄️ Vector Store"]
        FAISS["FAISS Index"]
    end

    subgraph Agent["🤖 LangChain Agent"]
        LLM["GPT-4o-mini"]
        Tools["🔧 Tools"]
        Memory["💭 Memory"]
    end

    subgraph Output["📤 Output"]
        Chat["💬 Chat Response"]
        Plan["📋 Project Plan"]
        Report["📊 Status Report"]
        Email["📧 Email"]
    end

    Local --> DocProc
    DocProc --> Splitter
    Splitter --> Embeddings
    Embeddings --> FAISS

    Trello --> Agent
    FAISS --> Agent
    LLM --> Agent
    Tools --> Agent
    Memory --> Agent

    Agent --> Chat
    Agent --> Plan
    Agent --> Report
    Agent --> Email
```

---

## 📁 Project Structure

```
Mira-AI-Agent/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── src/
│   ├── document_processor.py # File parsing & vectorization
│   ├── llm_handler.py        # LangChain Agent & LLM logic
│   ├── tools.py              # LangChain Tools (RAG, Trello, etc.)
│   ├── prompts.py            # System prompts
│   ├── trello_client.py      # Trello API client
│   ├── output_generator.py   # PDF/DOCX generation
│   └── email_service.py      # SMTP email sending
└── outputs/                  # Generated files (gitignored)
```

---

## 🔧 Tech Details

| Component            | Technology                            |
| -------------------- | ------------------------------------- |
| **Frontend**         | Streamlit                             |
| **LLM**              | OpenAI GPT-4o-mini / GPT-4o / GPT-3.5 |
| **Agent Framework**  | LangChain (AgentExecutor)             |
| **Vector Store**     | FAISS (in-memory)                     |
| **Embeddings**       | OpenAI text-embedding-ada-002         |
| **Document Parsing** | pdfplumber, python-docx, pandas       |
| **Task Management**  | Trello REST API                       |
| **Deployment**       | Streamlit Community Cloud             |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

Built with ❤️ for TPMs who want to spend less time on documentation and more time driving projects forward.
