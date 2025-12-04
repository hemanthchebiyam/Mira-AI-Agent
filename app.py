import streamlit as st
import os
import time
import re
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
    st.markdown("v1.2.0")

# Initialize Utils
output_gen = OutputGenerator(output_dir='outputs')
doc_processor = DocumentProcessor()
# Initialize LLM Handler without crashing if key is missing
llm = LLMHandler(api_key=api_key, model=selected_model_key)

def clean_markdown_display(content):
    """Helper to remove ```markdown from the start for cleaner display"""
    cleaned = re.sub(r'^```markdown\s*', '', content)
    cleaned = re.sub(r'^```\s*', '', cleaned)
    cleaned = re.sub(r'```$', '', cleaned)
    return cleaned

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

# === TAB 2: STATUS REPORTS ===
with report_tab:
    st.header("Status Reporting")
    st.markdown("Generate weekly reports from Trello activity.")
    
    # Input Section
    with st.container():
        col_input, col_btn = st.columns([3, 1])
        with col_input:
            board_input = st.text_input(
                "Board ID or URL", 
                placeholder="e.g. Qwertyui or https://trello.com/b/..."
            )
        
        with col_btn:
            st.write("") 
            st.write("")
            generate_btn = st.button("Generate Report", type="primary")

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
