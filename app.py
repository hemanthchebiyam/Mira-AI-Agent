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
    
    model_options = {
    "gpt-4o-mini": "Cheapest & Fast",
    "gpt-3.5-turbo": "Standard Legacy",
    "gpt-4o": "High Intelligence"
    }

    selected_model_key = st.selectbox(
        "Select OpenAI Model", 
        options=list(model_options.keys()),
        format_func=lambda x: f"{x} - {model_options[x]}"
    )

    if selected_model_key == "gpt-4o-mini":
        st.success("Cheapest & Fast (Recommended)")
    elif selected_model_key == "gpt-4o":
        st.success("High Intelligence (Premium)")
    elif selected_model_key == "gpt-3.5-turbo":
        st.success("Standard Legacy")

    api_key = st.text_input(
        "OpenAI API Key", 
        type="password",
        placeholder="sk-..."
    )
    
    if not api_key:
        st.warning("API Key required")
        
    st.divider()

    # Trello Configuration
    st.subheader("Connections")
    trello_key = st.text_input("Trello API Key", type="password", placeholder="Enter Trello API Key")
    trello_token = st.text_input("Trello Token", type="password", placeholder="Enter Trello Token")
    
    st.divider()
    st.markdown("v1.1.0")

# Initialize Utils
output_gen = OutputGenerator(output_dir='outputs')
doc_processor = DocumentProcessor()
llm = LLMHandler(api_key=api_key, model=selected_model_key)

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
            type=['pdf', 'docx', 'txt', 'xlsx', 'xls'],
            help="Supported formats: PDF, DOCX, TXT, Excel"
        )
    
    with col2:
        st.info("Upload PRDs and Timeline documents for best results.")

    if st.button("Generate Plan", type="primary", disabled=not uploaded_files):
        if not api_key:
            st.error("Please provide OpenAI API Key.")
        else:
            with st.status("Processing...", expanded=True) as status:
                st.write("Reading documents...")
                processed_data = doc_processor.process_files(uploaded_files)
                
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
                
                st.session_state['current_plan'] = plan
                status.update(label="Plan Generated", state="complete", expanded=False)

    if 'current_plan' in st.session_state:
        st.divider()
        st.markdown(st.session_state['current_plan'])
        
        # Download button for Plan
        st.download_button(
            label="💾 Download Plan (Markdown)",
            data=st.session_state['current_plan'],
            file_name=f"project_plan_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown"
        )

# === TAB 2: STATUS REPORTS ===
with report_tab:
    st.header("Status Reporting")
    st.markdown("Generate weekly reports from Trello activity.")
    
    # Input Section
    with st.container():
        col_input, col_btn = st.columns([3, 1])
        with col_input:
            board_id = st.text_input(
                "Board ID", 
                placeholder="Board ID or URL"
            )
        
        with col_btn:
            st.write("") 
            st.write("")
            generate_btn = st.button("Generate Report", type="primary")

    # Generation Logic
    if generate_btn:
        if not trello_key or not trello_token or not board_id:
            st.error("Please configure Trello credentials and Board ID.")
        elif not api_key:
            st.error("OpenAI API Key is missing.")
        else:
            # Clear previous states
            if 'current_report' in st.session_state:
                del st.session_state['current_report']
            if 'report_pdf' in st.session_state:
                del st.session_state['report_pdf']

            with st.status("Initiating workflow...", expanded=True) as status:
                
                status.write("Connecting to Trello API...")
                time.sleep(1.0)
                trello = TrelloClient(trello_key, trello_token)
                
                status.write("Fetching Board Data...")
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
        col_actions = st.columns(3)
        
        with col_actions[0]:
            st.download_button(
                label="💾 Download Markdown",
                data=st.session_state['current_report'],
                file_name=f"status_report_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown"
            )

        with col_actions[1]:
            # PDF Generation
            if 'report_pdf' not in st.session_state:
                if st.button("📄 Prepare PDF"):
                    with st.spinner("Converting to PDF..."):
                        try:
                            pdf_path = output_gen.save_pdf(st.session_state['current_report'], "status_report")
                            with open(pdf_path, "rb") as f:
                                st.session_state['report_pdf'] = f.read()
                            st.rerun()
                        except Exception as e:
                            st.error(f"PDF Error: {str(e)}")
            
            if 'report_pdf' in st.session_state:
                st.download_button(
                    label="⬇️ Download PDF",
                    data=st.session_state['report_pdf'],
                    file_name=f"status_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

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
