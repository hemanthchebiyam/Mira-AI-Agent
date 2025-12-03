import streamlit as st
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from src.trello_client import TrelloClient
from src.llm_handler import LLMHandler
from src.output_generator import OutputGenerator
from src.email_service import EmailService
from src.document_processor import DocumentProcessor

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Mira Agent", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for cleaner look
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
    </style>
""", unsafe_allow_html=True)

st.title("Mira Agent")
st.caption("Technical Program Management Assistant")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Configuration")
    
    # LLM Selection
    st.subheader("AI Model")
    llm_provider = st.selectbox(
        "Provider", 
        ["Ollama (Local)", "OpenAI"],
        help="Select 'OpenAI' for faster, high-quality results."
    )
    
    api_key = None
    if llm_provider == "OpenAI":
        default_key = os.getenv("OPENAI_API_KEY", "")
        api_key = st.text_input(
            "OpenAI API Key", 
            value=default_key, 
            type="password",
            placeholder="sk-..."
        )
        if not api_key:
            st.warning("API Key required for OpenAI")
    else:
        st.info("Model: qwen3:8b")
        
    st.divider()

    # Trello Configuration
    st.subheader("Connections")
    trello_key = st.text_input("Trello API Key", value=os.getenv("TRELLO_API_KEY", ""), type="password")
    trello_token = st.text_input("Trello Token", value=os.getenv("TRELLO_TOKEN", ""), type="password")
    
    st.divider()
    st.markdown("v1.0.0")

# Initialize Utils
output_gen = OutputGenerator(output_dir='outputs')
provider_code = "OpenAI" if llm_provider == "OpenAI" else "Ollama"
llm = LLMHandler(provider=provider_code, api_key=api_key)

# --- Main Content ---
plan_tab, report_tab = st.tabs(["Project Planning", "Status Reports"])

# === TAB 1: PROJECT PLANNING ===
with plan_tab:
    st.header("Project Planning")
    st.markdown("Upload requirements to generate execution plans.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Upload Documents", 
            accept_multiple_files=True,
            help="Supported formats: PDF, DOCX, TXT"
        )
    
    with col2:
        st.info("Upload PRDs and Timeline documents for best results.")

    if st.button("Generate Plan", type="primary", disabled=not uploaded_files):
        with st.status("Processing...", expanded=True) as status:
            st.write("Reading documents...")
            time.sleep(1.5)
            st.write("Analyzing constraints...")
            time.sleep(1.5)
            st.write("Drafting timeline...")
            time.sleep(1)
            status.update(label="Backend Pending", state="error", expanded=True)
        st.warning("Module under development.")

# === TAB 2: STATUS REPORTS ===
with report_tab:
    st.header("Status Reporting")
    st.markdown("Generate weekly reports from Trello activity.")
    
    # Input Section
    with st.container():
        col_input, col_btn = st.columns([3, 1])
        with col_input:
            default_board_id = os.getenv("TRELLO_BOARD_ID", "")
            board_id = st.text_input(
                "Board ID", 
                value=default_board_id, 
                placeholder="Board ID or URL"
            )
        
        with col_btn:
            # Vertical alignment spacer
            st.write("") 
            st.write("")
            generate_btn = st.button("Generate Report", type="primary")

    # Generation Logic
    if generate_btn:
        if not trello_key or not trello_token or not board_id:
            st.error("Please configure Trello credentials and Board ID.")
        elif llm_provider == "OpenAI" and not api_key:
            st.error("OpenAI API Key is missing.")
        else:
            if 'current_report' in st.session_state:
                del st.session_state['current_report']

            # Granular Status Updates with Delays
            with st.status("Initiating workflow...", expanded=True) as status:
                
                status.write("Connecting to Trello API...")
                time.sleep(1.2)
                trello = TrelloClient(trello_key, trello_token)
                
                status.write("Fetching Board Data...")
                time.sleep(1.5)
                try:
                    board_data = trello.fetch_board_data(board_id)
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
                time.sleep(1.5)
                
                status.write("Building context for LLM...")
                time.sleep(1.0)
                
                status.write("Generating Executive Summary & Risks...")
                report = llm.generate_status_report(board_data)
                
                st.session_state['current_report'] = report
                status.update(label="Complete", state="complete", expanded=False)

    # Display Report
    if 'current_report' in st.session_state:
        st.divider()
        
        with st.container():
            st.markdown(st.session_state['current_report'])
        
        st.divider()
        
        # Actions
        st.subheader("Export & Share")
        col_actions = st.columns(4)
        
        with col_actions[0]:
            if st.button("💾 Save Markdown"):
                path = output_gen.save_markdown(st.session_state['current_report'], "status_report")
                st.success(f"Saved MD: `{os.path.basename(path)}`")

        with col_actions[1]:
            if st.button("📄 Save PDF"):
                with st.spinner("Converting to PDF..."):
                    try:
                        path = output_gen.save_pdf(st.session_state['current_report'], "status_report")
                        st.success(f"Saved PDF: `{os.path.basename(path)}`")
                    except Exception as e:
                        st.error(f"PDF Error: {str(e)}")

        with col_actions[2]:
            with st.popover("📧 Email Report"):
                recipient = st.text_input("To:", placeholder="manager@company.com")
                if st.button("Send Email"):
                    if not recipient:
                        st.warning("Recipient required.")
                    else:
                        with st.spinner("Sending..."):
                            email_service = EmailService(
                                os.getenv("EMAIL_SENDER"), 
                                os.getenv("EMAIL_PASSWORD")
                            )
                            success, msg = email_service.send_email(
                                recipient, 
                                f"Weekly Status Report - {datetime.now().strftime('%Y-%m-%d')}", 
                                st.session_state['current_report']
                            )
                            if success:
                                st.success("Email sent!")
                            else:
                                st.error(f"Failed: {msg}")
