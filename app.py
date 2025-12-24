# Fix OpenMP conflict on Windows (must be before other imports)
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import streamlit as st
import time
import re
from datetime import datetime
from dotenv import load_dotenv
from src.trello_client import TrelloClient
from src.llm_handler import LLMHandler, AgenticLLMHandler
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
    st.markdown("v2.0.0 - LangChain Agentic RAG")

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
plan_tab, report_tab, ai_tab = st.tabs(["📋 Project Planning", "📊 Status Reports", "🤖 AI Assistant"])

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
    with st.expander("📁 Upload Project Documents", expanded=('vector_store' not in st.session_state)):
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
        else:
            # No files uploaded - clear vector store
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
