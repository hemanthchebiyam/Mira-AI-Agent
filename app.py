# Fix OpenMP conflict on Windows (must be before other imports)
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import streamlit as st
import time
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from src.trello_client import TrelloClient
from src.llm_handler import LLMHandler, AgenticLLMHandler
from src.output_generator import OutputGenerator
from src.email_service import EmailService
from src.document_processor import DocumentProcessor
from src.db import init_db, get_or_create_user
from src.auth import generate_login_token, verify_login_token, send_magic_link
from src.supabase_auth import verify_supabase_token
from src.secret_store import get_secret, set_secret, get_company_secret_value, set_company_secret
from src.storage import save_uploaded_files

# Load environment variables (use explicit path so .env is found regardless of cwd)
load_dotenv(Path(__file__).parent / ".env")

# Initialize database (if configured)
db_ready = True
db_error = None
try:
    init_db()
except Exception as e:
    db_ready = False
    db_error = str(e)

def set_current_user(user_row):
    st.session_state["current_user"] = {
        "id": user_row.id,
        "email": user_row.email,
        "company_id": user_row.company_id,
        "role": getattr(user_row, "role", None) or "member"
    }
    # Extract domain from email for company lookup
    if "@" in user_row.email:
        domain = user_row.email.split("@")[1].lower()
        st.session_state["current_user"]["domain"] = domain

def get_current_user():
    return st.session_state.get("current_user")

st.set_page_config(
    page_title="Mira Agent", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom theme font + CSS
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet">
    <script>
        // Hide icon names that appear as text - ultra aggressive approach
        const iconPatterns = [
            /keyboard_double_arrow_left/i,
            /keyboard_double_arrow_right/i,
            /keyboard_double/i,
            /board_double_arrow_left/i,
            /board_double_arrow_right/i,
            /key_double/i,
            /double_arrow/i
        ];
        
        function hideIconNames() {
            // Method 1: Find all text nodes and hide parent elements
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            let node;
            while (node = walker.nextNode()) {
                const text = node.textContent?.trim() || '';
                if (iconPatterns.some(pattern => pattern.test(text))) {
                    let parent = node.parentElement;
                    // Go up the tree to find a suitable element to hide
                    while (parent && parent !== document.body) {
                        const parentText = parent.textContent?.trim() || '';
                        // If parent only contains the icon name, hide it
                        if (iconPatterns.some(pattern => pattern.test(parentText) && parentText.length < 100)) {
                            parent.style.cssText = 'display: none !important; visibility: hidden !important; height: 0 !important; width: 0 !important; overflow: hidden !important; opacity: 0 !important;';
                            break;
                        }
                        parent = parent.parentElement;
                    }
                    // Also hide the text node's direct parent
                    if (node.parentElement) {
                        node.parentElement.style.cssText = 'display: none !important; visibility: hidden !important;';
                    }
                }
            }
            
            // Method 2: Find all elements and check their text content
            const allElements = document.querySelectorAll('*:not(script):not(style):not(noscript)');
            allElements.forEach(el => {
                const text = el.textContent?.trim() || '';
                // Hide if text exactly matches an icon name or is very short and contains icon pattern
                if (text.length > 0 && text.length < 100) {
                    if (iconPatterns.some(pattern => pattern.test(text))) {
                        el.style.cssText = 'display: none !important; visibility: hidden !important; height: 0 !important; width: 0 !important; overflow: hidden !important; opacity: 0 !important; position: absolute !important; left: -9999px !important;';
                    }
                }
            });
        }
        
        // Run immediately
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                hideIconNames();
                setInterval(hideIconNames, 500); // Run every 500ms
            });
        } else {
            hideIconNames();
            setInterval(hideIconNames, 500); // Run every 500ms
        }
        
        // Use MutationObserver to catch new content immediately
        const observer = new MutationObserver(function(mutations) {
            hideIconNames();
        });
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: false
        });
    </script>
""", unsafe_allow_html=True)
try:
    with open("mira-theme.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception:
    pass

# Process Supabase access token from welcome app
if 'current_user' not in st.session_state:
    access_token = st.query_params.get("access_token")
    if access_token and db_ready:
        try:
            sb_user = verify_supabase_token(access_token)
            if sb_user and sb_user.get("email"):
                email = sb_user["email"]
                domain = email.split("@")[1].lower() if "@" in email else None
                company_name = domain.split(".")[0].capitalize() if domain else "Default Company"
                user_row = get_or_create_user(email=email, company_name=company_name, domain=domain)
                set_current_user(user_row)
                st.query_params.clear()  # Remove token from URL
                st.rerun()
        except RuntimeError as e:
            # Supabase not configured - silently skip (not an error)
            if "not set" in str(e):
                pass  # Supabase auth is optional
            else:
                st.error(f"Supabase login failed: {str(e)}")
        except Exception as e:
            # Other errors - log but don't break the app
            pass

# Process login token from magic link URL
if 'current_user' not in st.session_state:
    login_token = st.query_params.get("login_token")
    if login_token and db_ready:
        try:
            user_row = verify_login_token(login_token)
            if user_row:
                set_current_user(user_row)
                st.query_params.clear()  # Remove token from URL for security
                st.rerun()
        except Exception as e:
            st.error(f"Login failed: {str(e)}")

# Custom CSS for cleaner look with chat styling
st.markdown("""
    <style>
    .stButton button {
        width: 100%;
        border-radius: 4px;
        font-weight: 600;
    }
    .block-container {
        padding-top: 2rem;
    }
    
    /* Chat styling */
    .chat-container {
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Upload zone styling for AI tab */
    .upload-zone {
        border: 2px dashed #4a4a4a;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    
    /* Agent status indicator */
    .agent-status {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        margin-bottom: 1rem;
    }
    .agent-ready {
        background: linear-gradient(90deg, #00b894, #00cec9);
        color: white;
    }
    .agent-not-ready {
        background: linear-gradient(90deg, #e17055, #d63031);
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Mira Agent")
st.caption("Technical Program Management Assistant")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Configuration")

    st.subheader("Login")
    current_user = get_current_user()
    if not db_ready:
        st.warning("Database not configured. Set DATABASE_URL to enable login.")
        if db_error:
            st.caption(f"Error: {db_error}")
    elif current_user:
        st.success(f"Logged in as {current_user['email']}")
    else:
        login_email = st.text_input("Email", placeholder="you@company.com")
        if st.button("Send Magic Link"):
            if not login_email:
                st.warning("Enter an email address.")
            else:
                sender = os.getenv("MAGIC_LINK_SENDER")
                password = os.getenv("MAGIC_LINK_PASSWORD")
                if not sender or not password:
                    st.error("Magic link email sender is not configured.")
                else:
                    try:
                        token, _user = generate_login_token(login_email)
                        success, msg = send_magic_link(login_email, token, sender, password)
                        if success:
                            st.success("Magic link sent. Check your email.")
                        else:
                            st.error(f"Failed to send link: {msg}")
                    except Exception as e:
                        st.error(f"Login error: {str(e)}")

    # LLM Selection
    st.subheader("AI Model")
    
    model_options = [
    "gpt-4o-mini",
    "gpt-3.5-turbo",
    "gpt-4o"
    ]

    selected_model_key = st.selectbox(
        "Select OpenAI Model", 
        options=model_options
    )

    if selected_model_key == "gpt-4o-mini":
        st.success("Cheapest & Fast (Recommended)")
    elif selected_model_key == "gpt-4o":
        st.success("High Intelligence (Premium)")
    elif selected_model_key == "gpt-3.5-turbo":
        st.success("Standard Legacy")

    # Load API keys: company-level first, then user-level
    saved_api_key = None
    api_key_source = None
    if current_user and db_ready:
        try:
            # Try company-level first
            company_api_key = get_company_secret_value(current_user["company_id"], "openai_api_key")
            if company_api_key:
                saved_api_key = company_api_key
                api_key_source = "company"
            else:
                # Fall back to user-level
                saved_api_key = get_secret(current_user["id"], "openai_api_key")
                if saved_api_key:
                    api_key_source = "user"
        except Exception:
            saved_api_key = None

    api_key = st.text_input(
        "OpenAI API Key", 
        type="password",
        placeholder="sk-...",
        value=saved_api_key or "",
        help=f"Currently using: {api_key_source.title()}-level key" if api_key_source else "No key configured"
    )
    
    if not api_key:
        st.warning("API Key required")
        
    st.divider()

    # Trello Configuration
    st.subheader("Connections")
    saved_trello_key = None
    saved_trello_token = None
    trello_source = None
    if current_user and db_ready:
        try:
            # Try company-level first
            company_trello_key = get_company_secret_value(current_user["company_id"], "trello_api_key")
            company_trello_token = get_company_secret_value(current_user["company_id"], "trello_token")
            if company_trello_key and company_trello_token:
                saved_trello_key = company_trello_key
                saved_trello_token = company_trello_token
                trello_source = "company"
            else:
                # Fall back to user-level
                saved_trello_key = get_secret(current_user["id"], "trello_api_key")
                saved_trello_token = get_secret(current_user["id"], "trello_token")
                if saved_trello_key or saved_trello_token:
                    trello_source = "user"
        except Exception:
            saved_trello_key = None
            saved_trello_token = None

    trello_key = st.text_input(
        "Trello API Key",
        type="password",
        placeholder="Enter Trello API Key",
        value=saved_trello_key or "",
        help=f"Currently using: {trello_source.title()}-level key" if trello_source else "No key configured"
    )
    trello_token = st.text_input(
        "Trello Token",
        type="password",
        placeholder="Enter Trello Token",
        value=saved_trello_token or "",
        help=f"Currently using: {trello_source.title()}-level key" if trello_source else "No key configured"
    )

    # Credential saving options
    if current_user and db_ready:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save as User Credentials", use_container_width=True):
                try:
                    if api_key:
                        set_secret(current_user["id"], "openai_api_key", api_key)
                    if trello_key:
                        set_secret(current_user["id"], "trello_api_key", trello_key)
                    if trello_token:
                        set_secret(current_user["id"], "trello_token", trello_token)
                    st.success("User credentials saved.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save: {str(e)}")
        
        with col2:
            is_admin = current_user.get("role") == "admin"
            if st.button("🏢 Save as Company Credentials", use_container_width=True, disabled=not is_admin):
                try:
                    if api_key:
                        set_company_secret(current_user["company_id"], "openai_api_key", api_key)
                    if trello_key:
                        set_company_secret(current_user["company_id"], "trello_api_key", trello_key)
                    if trello_token:
                        set_company_secret(current_user["company_id"], "trello_token", trello_token)
                    st.success("Company credentials saved. All users from your domain will use these keys.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save: {str(e)}")
            if not is_admin:
                st.info("Only admins can set company-level credentials.")
        
        if api_key_source == "company" or trello_source == "company":
            st.info("ℹ️ You're currently using company-level credentials. These are shared across all users from your domain.")
    
    st.divider()
    st.markdown("v2.2.0 - LangChain RAG")

# Initialize Utils
output_gen = OutputGenerator(output_dir='outputs')
doc_processor = DocumentProcessor()
# Initialize LLM Handler without crashing if key is missing (for existing tabs)
llm = LLMHandler(api_key=api_key, model=selected_model_key)

# ============================================================================
# Session State Callbacks for Agent Tools
# ============================================================================

def set_session_state(key: str, value):
    """Callback for tools to save content to session state."""
    st.session_state[key] = value
    # Also trigger file generation
    if key == 'current_plan' and value:
        st.session_state['plan_files'] = output_gen.generate_all_formats(
            clean_markdown_display(value), "project_plan"
        )
        st.session_state['agent_generated_plan'] = True
    elif key == 'current_report' and value:
        st.session_state['report_files'] = output_gen.generate_all_formats(
            clean_markdown_display(value), "status_report"
        )
        st.session_state['agent_generated_report'] = True

def get_session_state(key: str):
    """Callback for tools to retrieve content from session state."""
    return st.session_state.get(key)

# ============================================================================
# Initialize Agentic LLM Handler (for AI Assistant tab)
# ============================================================================

def get_agentic_handler():
    """Get or create the agentic handler in session state."""
    # Check if we need to create/recreate the handler
    current_config = f"{api_key}_{selected_model_key}_{trello_key}_{trello_token}"
    
    if 'agentic_llm' not in st.session_state or st.session_state.get('agentic_config') != current_config:
        if api_key:
            st.session_state.agentic_llm = AgenticLLMHandler(
                api_key=api_key,
                model=selected_model_key,
                trello_api_key=trello_key,
                trello_token=trello_token,
                session_state_callback=set_session_state,
                get_content_callback=get_session_state
            )
            st.session_state.agentic_config = current_config
        else:
            st.session_state.agentic_llm = None
    
    return st.session_state.get('agentic_llm')

# Get or create the agentic handler
agentic_llm = get_agentic_handler()

def clean_markdown_display(content):
    """Helper to remove ```markdown from the start for cleaner display"""
    cleaned = re.sub(r'^```markdown\s*', '', content)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'```$', '', cleaned)
    return cleaned

def parse_list_names(raw):
    """Parse comma-separated list names."""
    return [item.strip() for item in raw.split(",") if item.strip()] if raw else []

def download_actions(file_paths, content, prefix="report", key_prefix=""):
    """Reusable download actions component with Eager Generation paths"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        with st.popover("💾 Download Options"):
            st.write("Select format to download:")
            
            # Markdown (read from file or memory)
            # We use content directly for MD to avoid re-read
            st.download_button(
                label="Markdown (.md)",
                data=content,
                file_name=os.path.basename(file_paths['md']),
                mime="text/markdown",
                use_container_width=True,
                key=f"{key_prefix}_dl_md"
            )
            
            # Text - Read pre-generated file
            try:
                with open(file_paths['txt'], "r", encoding='utf-8') as f:
                    txt_data = f.read()
                st.download_button(
                    label="Plain Text (.txt)",
                    data=txt_data,
                    file_name=os.path.basename(file_paths['txt']),
                    mime="text/plain",
                    use_container_width=True,
                    key=f"{key_prefix}_dl_txt"
                )
            except Exception as e:
                st.error(f"TXT Error: {str(e)}")
            
            # PDF - Read pre-generated file
            try:
                with open(file_paths['pdf'], "rb") as f:
                    pdf_data = f.read()
                st.download_button(
                    label="PDF Document (.pdf)",
                    data=pdf_data,
                    file_name=os.path.basename(file_paths['pdf']),
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"{key_prefix}_dl_pdf"
                )
            except Exception as e:
                st.error(f"PDF Error: {str(e)}")
                        
            # DOCX - Read pre-generated file
            try:
                with open(file_paths['docx'], "rb") as f:
                    docx_data = f.read()
                st.download_button(
                    label="Word Document (.docx)",
                    data=docx_data,
                    file_name=os.path.basename(file_paths['docx']),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key=f"{key_prefix}_dl_docx"
                )
            except Exception as e:
                st.error(f"DOCX Error: {str(e)}")

    with col2:
        with st.popover("📧 Email"):
            st.markdown("### Email Settings")
            sender_email = st.text_input("Sender Email", placeholder="you@gmail.com", key=f"{key_prefix}_email_sender")
            sender_password = st.text_input("App Password", type="password", help="Use App Password for Gmail", key=f"{key_prefix}_email_pass")
            recipient = st.text_input("Recipient", placeholder="manager@company.com", key=f"{key_prefix}_email_recip")
            
            if st.button("Send Email", use_container_width=True, key=f"{key_prefix}_send_btn"):
                if not sender_email or not sender_password or not recipient:
                    st.warning("All fields required.")
                else:
                    with st.spinner("Sending..."):
                        email_service = EmailService(sender_email, sender_password)
                        success, msg = email_service.send_email(
                            recipient, 
                            f"{prefix.replace('_', ' ').title()} - {datetime.now().strftime('%Y-%m-%d')}", 
                            content
                        )
                        if success:
                            st.success("Email sent!")
                        else:
                            st.error(f"Failed: {msg}")

# --- Main Content ---
plan_tab, report_tab, ai_tab, actions_tab = st.tabs(["📋 Project Planning", "📊 Status Reports", "🤖 AI Assistant", "📋 Board Actions"])

# === TAB 1: PROJECT PLANNING (Unchanged) ===
with plan_tab:
    st.header("Project Planning")
    st.markdown("Upload requirements to generate execution plans.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Upload Documents", 
            accept_multiple_files=True,
            type=['pdf', 'docx', 'txt', 'xlsx', 'xls'],
            help="Supported formats: PDF, DOCX, TXT, Excel",
            key="plan_tab_uploader"
        )
    
    with col2:
        st.info("Upload PRDs and Timeline documents for best results.")

    if st.button("Generate Plan", type="primary", disabled=not uploaded_files, key="gen_plan_btn"):
        if not api_key:
            st.error("Please provide OpenAI API Key.")
        else:
            with st.status("Processing...", expanded=True) as status:
                st.write("Reading documents...")
                processed_data = doc_processor.process_files(uploaded_files)

                if current_user and db_ready:
                    try:
                        save_uploaded_files(
                            uploaded_files,
                            current_user["company_id"],
                            current_user["id"]
                        )
                    except Exception as e:
                        st.warning(f"Document storage skipped: {str(e)}")
                
                # Show details of processed files
                for text_file in processed_data['file_details']:
                    if "Error" in text_file['status']:
                        st.error(f"{text_file['name']}: {text_file['status']}")
                    else:
                        st.success(f"{text_file['name']}: {text_file['status']}")
                
                if not processed_data['combined_text']:
                    status.update(label="No valid text found", state="error")
                    st.stop()

                st.write("Analyzing content and drafting plan...")
                plan = llm.generate_project_plan(processed_data['combined_text'])
                clean_plan = clean_markdown_display(plan)
                
                st.session_state['current_plan'] = clean_plan
                
                st.write("Preparing downloads...")
                # Eager generation of all files
                st.session_state['plan_files'] = output_gen.generate_all_formats(clean_plan, "project_plan")
                
                status.update(label="Plan Generated", state="complete", expanded=False)

    if 'current_plan' in st.session_state:
        st.divider()
        st.markdown(st.session_state['current_plan'])
        st.divider()
        if 'plan_files' in st.session_state:
            download_actions(st.session_state['plan_files'], st.session_state['current_plan'], "project_plan", "plan")

# === TAB 2: STATUS REPORTS (Unchanged) ===
with report_tab:
    st.header("Status Reporting")
    st.markdown("Generate weekly reports from Trello activity.")
    
    # Input Section
    with st.container():
        col_input, col_btn = st.columns([3, 1])
        with col_input:
            board_input = st.text_input(
                "Board ID or URL", 
                placeholder="e.g. Qwertyui or https://trello.com/b/...",
                key="report_tab_board"
            )
        
        with col_btn:
            st.write("") 
            st.write("")
            generate_btn = st.button("Generate Report", type="primary", key="gen_report_btn")

    # Generation Logic
    if generate_btn:
        if not trello_key or not trello_token or not board_input:
            st.error("Please configure Trello credentials and Board ID/URL.")
        elif not api_key:
            st.error("OpenAI API Key is missing.")
        else:
            # Clear previous states
            if 'current_report' in st.session_state:
                del st.session_state['current_report']
            if 'report_files' in st.session_state:
                del st.session_state['report_files']

            with st.status("Initiating workflow...", expanded=True) as status:
                
                status.write("Connecting to Trello API...")
                time.sleep(1.0)
                trello = TrelloClient(trello_key, trello_token)
                
                status.write("Fetching Board Data...")
                try:
                    board_data = trello.fetch_board_data(board_input)
                except Exception as e:
                    status.update(label="Connection Failed", state="error")
                    st.error(f"Error: {str(e)}")
                    st.stop()

                if "error" in board_data:
                    status.update(label="Trello API Error", state="error")
                    st.error(f"Error: {board_data['error']}")
                    st.stop()
                
                list_count = len(board_data)
                card_count = sum(len(cards) for cards in board_data.values())
                
                status.write(f"Processing {list_count} lists and {card_count} cards...")
                status.write("Generating Executive Summary & Risks...")
                report = llm.generate_status_report(board_data)
                clean_report = clean_markdown_display(report)
                
                st.session_state['current_report'] = clean_report
                
                st.write("Preparing downloads...")
                # Eager generation of all files
                st.session_state['report_files'] = output_gen.generate_all_formats(clean_report, "status_report")
                
                status.update(label="Complete", state="complete", expanded=False)

    # Display Report
    if 'current_report' in st.session_state:
        st.divider()
        
        with st.container():
            st.markdown(st.session_state['current_report'])
        
        st.divider()
        
        # Actions
        if 'report_files' in st.session_state:
            download_actions(st.session_state['report_files'], st.session_state['current_report'], "status_report", "report")

# === TAB 3: AI ASSISTANT (New LangChain Agentic RAG) ===
with ai_tab:
    st.header("🤖 AI Assistant")
    st.markdown("Chat with Mira - your intelligent TPM assistant with RAG capabilities.")
    
    # Initialize chat history in session state
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    # -------------------------------------------------------------------------
    # Document Upload Section with AUTO-INDEXING
    # -------------------------------------------------------------------------
    with st.expander("📁 Project Documents", expanded=('vector_store' not in st.session_state)):
        
        ai_uploaded_files = st.file_uploader(
            "Upload documents for intelligent Q&A (auto-indexed)",
            accept_multiple_files=True,
            type=['pdf', 'docx', 'txt', 'xlsx', 'xls'],
            help="Supported: PDF, DOCX, TXT, Excel. Documents are automatically indexed when uploaded.",
            key="ai_tab_uploader"
        )
        
        # Auto-index when files are uploaded
        if ai_uploaded_files:
            # Create a hash of current files to detect changes
            current_files_hash = hash(tuple(f.name + str(f.size) for f in ai_uploaded_files))
            previous_hash = st.session_state.get('files_hash', None)
            
            # Only re-index if files changed
            if current_files_hash != previous_hash:
                if not api_key:
                    st.warning("⚠️ Enter your OpenAI API Key in the sidebar to enable document indexing.")
                else:
                    with st.spinner(f"📚 Indexing {len(ai_uploaded_files)} document(s)..."):
                        try:
                            # Create vector store using FAISS (simpler than ChromaDB)
                            if current_user and db_ready:
                                try:
                                    save_uploaded_files(
                                        ai_uploaded_files,
                                        current_user["company_id"],
                                        current_user["id"]
                                    )
                                except Exception as e:
                                    st.warning(f"Document storage skipped: {str(e)}")
                            use_pgvector = os.getenv("VECTOR_STORE", "").lower() == "pgvector"
                            if use_pgvector:
                                vector_store = doc_processor.create_vector_store_pgvector(
                                    ai_uploaded_files,
                                    api_key
                                )
                            else:
                                vector_store = doc_processor.create_vector_store_simple(ai_uploaded_files, api_key)
                            
                            if vector_store:
                                st.session_state.vector_store = vector_store
                                st.session_state.files_hash = current_files_hash
                                st.session_state.indexed_files = [f.name for f in ai_uploaded_files]
                                
                                # Update agent's vector store
                                current_handler = get_agentic_handler()
                                if current_handler:
                                    current_handler.set_vector_store(vector_store)
                                
                                st.success(f"✅ Indexed {len(ai_uploaded_files)} document(s). Ready to chat!")
                            else:
                                st.error("❌ No valid content found in the uploaded files.")
                        except Exception as e:
                            st.error(f"❌ Error indexing: {str(e)}")
            else:
                # Files already indexed
                st.success(f"✅ {len(ai_uploaded_files)} document(s) indexed: {', '.join(st.session_state.get('indexed_files', []))}")
        
        # Clear vector store if no files
        if not ai_uploaded_files:
            if 'vector_store' in st.session_state:
                del st.session_state['vector_store']
                st.session_state.pop('files_hash', None)
                st.session_state.pop('indexed_files', None)
    
    # -------------------------------------------------------------------------
    # Status Bar
    # -------------------------------------------------------------------------
    col_status1, col_status2 = st.columns(2)
    with col_status1:
        if api_key:
            st.success("🟢 Agent Ready")
        else:
            st.error("🔴 API Key Required")
    with col_status2:
        if 'vector_store' in st.session_state:
            st.info(f"📚 {len(st.session_state.get('indexed_files', []))} docs indexed")
        else:
            st.warning("📄 No documents loaded")

    # -------------------------------------------------------------------------
    # Trello Board Creation from Documents
    # -------------------------------------------------------------------------
    with st.expander("📋 Create Trello Board from Documents", expanded=False):
        st.markdown("Generate tasks from your documents and create a Trello board with lists and cards.")
        board_name_input = st.text_input(
            "Board Name (optional)",
            placeholder="e.g. Q3 AI Adoption Project"
        )
        list_names_input = st.text_input(
            "List Names (comma-separated)",
            value="To Do, In Progress, Done"
        )

        if st.button("Create Board & Cards", type="primary"):
            if not trello_key or not trello_token:
                st.error("Please configure Trello credentials in the sidebar.")
            elif not api_key:
                st.error("OpenAI API Key is missing.")
            elif not ai_uploaded_files:
                st.error("Please upload project documents in the section above.")
            else:
                with st.status("Creating Trello board...", expanded=True) as status:
                    status.write("Reading documents...")
                    processed_data = doc_processor.process_files(ai_uploaded_files)
                    combined_text = processed_data.get("combined_text", "")

                    if not combined_text:
                        status.update(label="No valid text found", state="error")
                        st.stop()

                    status.write("Generating task list from documents...")
                    truncated_text = combined_text[:12000]
                    spec = llm.generate_trello_board_spec(
                        truncated_text,
                        board_name=board_name_input or None,
                        list_names=list_names_input or None
                    )

                    if isinstance(spec, dict) and spec.get("error"):
                        status.update(label="Failed to generate tasks", state="error")
                        st.error(spec["error"])
                        st.stop()

                    list_names = parse_list_names(list_names_input) or spec.get("lists") or ["To Do", "In Progress", "Done"]
                    board_name = board_name_input or spec.get("board_name") or "Mira Project Board"

                    status.write(f"Creating board: {board_name}")
                    trello = TrelloClient(trello_key, trello_token)
                    board_resp = trello.create_board(board_name)
                    if isinstance(board_resp, dict) and board_resp.get("error"):
                        status.update(label="Board creation failed", state="error")
                        st.error(board_resp["error"])
                        st.stop()

                    board_id = board_resp.get("id")
                    board_url = board_resp.get("shortUrl") or board_resp.get("url")
                    if not board_id:
                        status.update(label="Board creation failed", state="error")
                        st.error("Trello did not return a board ID.")
                        st.stop()

                    status.write("Creating lists...")
                    list_id_map = {}
                    for list_name in list_names:
                        list_resp = trello.create_list(board_id, list_name)
                        if isinstance(list_resp, dict) and list_resp.get("error"):
                            st.warning(f"Failed to create list '{list_name}': {list_resp['error']}")
                            continue
                        list_id_map[list_name] = list_resp.get("id")

                    if not list_id_map:
                        status.update(label="List creation failed", state="error")
                        st.error("No lists were created. Check Trello credentials and permissions.")
                        st.stop()

                    status.write("Creating cards...")
                    created_cards = 0
                    failed_cards = 0
                    default_list_id = next(iter(list_id_map.values()))
                    for card in spec.get("cards", []):
                        title = (card or {}).get("title") or "Untitled Task"
                        description = (card or {}).get("description") or ""
                        due_date = (card or {}).get("due_date") or None
                        list_name = (card or {}).get("list") or ""
                        list_id = list_id_map.get(list_name, default_list_id)

                        resp = trello.create_card(
                            list_id=list_id,
                            name=title,
                            desc=description,
                            due=due_date
                        )
                        if isinstance(resp, dict) and resp.get("error"):
                            failed_cards += 1
                        else:
                            created_cards += 1

                    status.update(label="Trello board created", state="complete", expanded=False)
                    st.success(f"Board created: {board_name}")
                    if board_url:
                        st.markdown(f"Board link: {board_url}")
                    st.info(f"Lists: {len(list_id_map)} | Cards created: {created_cards} | Failed: {failed_cards}")

    st.divider()
    
    # -------------------------------------------------------------------------
    # Chat Interface
    # -------------------------------------------------------------------------
    chat_container = st.container()
    
    with chat_container:
        # Display chat messages
        for i, message in enumerate(st.session_state.chat_messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Show download actions if this message generated a plan or report
                if message["role"] == "assistant":
                    if message.get("has_plan") and 'plan_files' in st.session_state:
                        st.divider()
                        download_actions(
                            st.session_state['plan_files'], 
                            st.session_state.get('current_plan', ''), 
                            "project_plan", 
                            f"chat_plan_{i}"
                        )
                    elif message.get("has_report") and 'report_files' in st.session_state:
                        st.divider()
                        download_actions(
                            st.session_state['report_files'], 
                            st.session_state.get('current_report', ''), 
                            "status_report", 
                            f"chat_report_{i}"
                        )
    
    # Chat Input - Handle new prompts
    if prompt := st.chat_input("Ask Mira anything about your project...", key="chat_input"):
        if not api_key:
            st.error("⚠️ Please enter your OpenAI API Key in the sidebar.")
        else:
            # Add user message and set pending flag for response generation
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            st.session_state['pending_prompt'] = prompt
            st.rerun()  # Rerun to show user message immediately
    
    # Generate response if there's a pending prompt
    if st.session_state.get('pending_prompt'):
        current_handler = get_agentic_handler()
        if not current_handler:
            st.error("⚠️ Agent not initialized. Please check your API key.")
            st.session_state.pop('pending_prompt', None)
        else:
            # Reset generation flags
            st.session_state['agent_generated_plan'] = False
            st.session_state['agent_generated_report'] = False
            
            # Show thinking indicator and generate response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = current_handler.chat(st.session_state['pending_prompt'])
                st.markdown(response)
            
            # Check if plan or report was generated
            message_data = {"role": "assistant", "content": response}
            
            if st.session_state.get('agent_generated_plan'):
                message_data["has_plan"] = True
            
            if st.session_state.get('agent_generated_report'):
                message_data["has_report"] = True
            
            # Add assistant response to history and clear pending
            st.session_state.chat_messages.append(message_data)
            st.session_state.pop('pending_prompt', None)
            st.rerun()  # Rerun to properly display in chat history
    
    # Sidebar actions for AI tab
    with st.sidebar:
        st.divider()
        st.subheader("AI Assistant Actions")
        
        if st.button("🗑️ Clear Chat History", key="clear_chat_btn"):
            st.session_state.chat_messages = []
            current_handler = get_agentic_handler()
            if current_handler:
                current_handler.clear_memory()
            st.rerun()
        
        if st.button("🔄 Reset Knowledge Base", key="reset_kb_btn"):
            st.session_state.pop('vector_store', None)
            st.session_state.pop('files_hash', None)
            st.session_state.pop('indexed_files', None)
            current_handler = get_agentic_handler()
            if current_handler:
                current_handler.set_vector_store(None)
            st.rerun()
    
    # Example prompts for new users
    if not st.session_state.chat_messages:
        st.markdown("---")
        st.markdown("### 💡 Try asking Mira:")
        
        example_cols = st.columns(2)
        
        with example_cols[0]:
            st.markdown("""
            **📄 Document Questions:**
            - "What are the key milestones?"
            - "Who is responsible for phase 2?"
            - "Summarize the project scope"
            """)
            
        with example_cols[1]:
            st.markdown("""
            **📊 Actions:**
            - "Generate a project plan"
            - "Create a status report for [board URL]"
            - "What tasks are in progress?"
            """)
# === TAB 4: BOARD ACTIONS ===
with actions_tab:
    st.header("Trello Board Actions")
    st.markdown("Create/update cards, add comments/checklists, and archive items.")

    if not trello_key or not trello_token:
        st.warning("Enter Trello credentials in the sidebar to enable actions.")
        st.stop()

    trello = TrelloClient(trello_key, trello_token)
    default_board = board_input if 'board_input' in locals() else ""
    actions_board_input = st.text_input(
        "Board ID or URL",
        value=default_board,
        placeholder="e.g. abc123 or https://trello.com/b/abc123/board-name",
        key="actions_board_input"
    )

    def parse_csv(raw):
        return [item.strip() for item in raw.split(",") if item.strip()] if raw else None

    # Load lists for selectors
    col_lists_load = st.columns([1, 1, 2])
    with col_lists_load[0]:
        load_lists = st.button("Load Lists", use_container_width=True)

    if load_lists:
        with st.spinner("Fetching lists..."):
            lists_resp = trello.get_lists(actions_board_input)
        if isinstance(lists_resp, dict) and "error" in lists_resp:
            st.error(lists_resp["error"])
        else:
            st.session_state['trello_lists'] = lists_resp
            st.success(f"Loaded {len(lists_resp)} lists")

    list_options = st.session_state.get('trello_lists', [])

    def list_selector(label, key):
        if list_options:
            return st.selectbox(label, options=list_options, format_func=lambda l: l.get('name', ''), key=key)
        return None

    st.divider()
    st.subheader("Create Card")
    with st.form("create_card_form"):
        selected_list = list_selector("Choose List (optional)", "create_list_select")
        list_id_manual = st.text_input("List ID (if not selecting above)", key="create_list_manual")
        list_id = (selected_list or {}).get('id') if selected_list else list_id_manual
        card_name = st.text_input("Card Title", key="create_card_name")
        card_desc = st.text_area("Description", key="create_card_desc")
        due_text = st.text_input("Due Date (YYYY-MM-DD, optional)", key="create_card_due")
        label_ids = st.text_input("Label IDs (comma-separated, optional)", key="create_label_ids")
        member_ids = st.text_input("Member IDs (comma-separated, optional)", key="create_member_ids")
        submit_create = st.form_submit_button("Create Card", type="primary", use_container_width=True)

    if submit_create:
        if not list_id or not card_name:
            st.error("List ID and Card Title are required.")
        else:
            with st.spinner("Creating card..."):
                resp = trello.create_card(
                    list_id=list_id,
                    name=card_name,
                    desc=card_desc,
                    due=due_text or None,
                    label_ids=parse_csv(label_ids),
                    member_ids=parse_csv(member_ids)
                )
            if isinstance(resp, dict) and "error" in resp:
                st.error(resp["error"])
            else:
                st.success(f"Card created: {resp.get('name', '')} ({resp.get('id')})")

    st.divider()
    st.subheader("Update Card")
    with st.form("update_card_form"):
        card_id = st.text_input("Card ID", key="update_card_id")
        new_name = st.text_input("New Title (optional)", key="update_card_name")
        new_desc = st.text_area("New Description (optional)", key="update_card_desc")
        new_due = st.text_input("New Due Date (YYYY-MM-DD, optional)", key="update_card_due")
        move_list = list_selector("Move to List (optional)", "update_list_select")
        move_list_manual = st.text_input("Move to List ID (if not selecting above)", key="update_list_manual")
        move_list_id = (move_list or {}).get('id') if move_list else move_list_manual
        update_labels = st.text_input("Replace Label IDs (comma-separated, optional)", key="update_label_ids")
        update_members = st.text_input("Replace Member IDs (comma-separated, optional)", key="update_member_ids")
        submit_update = st.form_submit_button("Update Card", use_container_width=True)

    if submit_update:
        if not card_id:
            st.error("Card ID is required.")
        else:
            with st.spinner("Updating card..."):
                resp = trello.update_card(
                    card_id=card_id,
                    name=new_name or None,
                    desc=new_desc or None,
                    due=new_due or None,
                    list_id=move_list_id or None,
                    label_ids=parse_csv(update_labels),
                    member_ids=parse_csv(update_members)
                )
            if isinstance(resp, dict) and "error" in resp:
                st.error(resp["error"])
            else:
                st.success(f"Card updated: {resp.get('name', '')}")

    st.divider()
    st.subheader("Comments & Checklist")
    with st.form("comment_form"):
        comment_card_id = st.text_input("Card ID", key="comment_card_id")
        comment_text = st.text_area("Comment", key="comment_text")
        submit_comment = st.form_submit_button("Add Comment", use_container_width=True)

    if submit_comment:
        if not comment_card_id or not comment_text:
            st.error("Card ID and comment are required.")
        else:
            with st.spinner("Adding comment..."):
                resp = trello.add_comment(comment_card_id, comment_text)
            if isinstance(resp, dict) and "error" in resp:
                st.error(resp["error"])
            else:
                st.success("Comment added.")

    with st.form("checklist_form"):
        checklist_card_id = st.text_input("Card ID", key="checklist_card_id")
        checklist_name = st.text_input("Checklist Name", key="checklist_name")
        checklist_item = st.text_input("Checklist Item", key="checklist_item")
        checklist_checked = st.checkbox("Mark item complete", key="checklist_checked")
        submit_checklist = st.form_submit_button("Add Checklist Item", use_container_width=True)

    if submit_checklist:
        if not checklist_card_id or not checklist_name or not checklist_item:
            st.error("Card ID, checklist name, and item are required.")
        else:
            with st.spinner("Adding checklist item..."):
                resp = trello.add_checklist_item(
                    checklist_card_id,
                    checklist_name,
                    checklist_item,
                    checked=checklist_checked
                )
            if isinstance(resp, dict) and "error" in resp:
                st.error(resp["error"])
            else:
                st.success("Checklist item added.")

    st.divider()
    st.subheader("Archive / Restore")
    col_archive = st.columns(2)
    with col_archive[0]:
        with st.form("archive_card_form"):
            archive_card_id = st.text_input("Card ID", key="archive_card_id")
            archive_card = st.checkbox("Archive card (uncheck to restore)", value=True, key="archive_card_flag")
            submit_archive_card = st.form_submit_button("Update Card Archive State", use_container_width=True)
    if submit_archive_card:
        if not archive_card_id:
            st.error("Card ID is required.")
        else:
            with st.spinner("Updating card state..."):
                resp = trello.close_card(archive_card_id, closed=archive_card)
            if isinstance(resp, dict) and "error" in resp:
                st.error(resp["error"])
            else:
                st.success("Card state updated.")

    with col_archive[1]:
        with st.form("archive_list_form"):
            archive_list_id = st.text_input("List ID", key="archive_list_id")
            archive_list = st.checkbox("Archive list (uncheck to restore)", value=True, key="archive_list_flag")
            submit_archive_list = st.form_submit_button("Update List Archive State", use_container_width=True)
    if submit_archive_list:
        if not archive_list_id:
            st.error("List ID is required.")
        else:
            with st.spinner("Updating list state..."):
                resp = trello.close_list(archive_list_id, closed=archive_list)
            if isinstance(resp, dict) and "error" in resp:
                st.error(resp["error"])
            else:
                st.success("List state updated.")
