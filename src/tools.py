"""
LangChain Tools for Mira Agent

This module defines tools using the simpler @tool decorator approach
which is more reliable than class-based tools for passing runtime data.
"""

from typing import Optional, Callable
from datetime import datetime
from langchain_core.tools import tool

from .prompts import PROJECT_PLAN_PROMPT, STATUS_REPORT_PROMPT
from .trello_client import TrelloClient


# ============================================================================
# Tool Factory Function - Creates tools with closures for runtime data
# ============================================================================

def create_agent_tools(
    vector_store=None,
    llm=None,
    trello_api_key: str = None,
    trello_token: str = None,
    session_state_callback: Callable = None,
    get_content_callback: Callable = None,
    email_sender: str = None,
    email_password: str = None
) -> list:
    """
    Factory function to create all tools with proper configuration.
    Uses closures to capture runtime data like vector_store.
    """
    
    # -------------------------------------------------------------------------
    # Document Search Tool
    # -------------------------------------------------------------------------
    @tool
    def search_project_documents(query: str) -> str:
        """Search through uploaded project documents to find relevant information.
        Use this tool FIRST when answering questions about:
        - Project requirements, scope, or specifications
        - Timeline, milestones, or deadlines  
        - Team members, roles, or responsibilities
        - Technical details from PRDs or design docs
        - Any information the user asks about their project
        
        Args:
            query: The search query to find relevant information
        """
        if vector_store is None:
            return "No documents have been uploaded yet. Please ask the user to upload project documents first."
        
        try:
            results = vector_store.similarity_search(query, k=4)
            
            if not results:
                return f"No relevant information found for query: '{query}'"
            
            output = f"📚 **Found {len(results)} relevant sections:**\n\n"
            
            for i, doc in enumerate(results, 1):
                source = doc.metadata.get("source", "Unknown Document")
                chunk_idx = doc.metadata.get("chunk_index", 0) + 1
                total_chunks = doc.metadata.get("total_chunks", 1)
                
                output += f"### 📄 Source {i}: `{source}`\n"
                output += f"**Section:** {chunk_idx} of {total_chunks}\n\n"
                output += f"> {doc.page_content}\n\n"
                output += f"---\n\n"
            
            output += "*💡 Use the information above to answer the user's question. Always cite the source document names.*"
            
            return output
            
        except Exception as e:
            return f"Error searching documents: {str(e)}"
    
    # -------------------------------------------------------------------------
    # Trello Board Tool
    # -------------------------------------------------------------------------
    @tool
    def fetch_trello_board(board_id_or_url: str) -> str:
        """Fetch live task data from a Trello board.
        Use this tool when you need to check task status or project progress.
        
        Args:
            board_id_or_url: Trello board ID or full URL (e.g., 'abc123' or 'https://trello.com/b/abc123/board-name')
        """
        if not trello_api_key or not trello_token:
            return "⚠️ **Trello credentials not configured!** Please enter your Trello API Key and Token in the sidebar."
        
        try:
            trello_client = TrelloClient(trello_api_key, trello_token)
            board_data = trello_client.fetch_board_data(board_id_or_url)
            
            if "error" in board_data:
                return f"Error fetching Trello data: {board_data['error']}"
            
            output = "**Trello Board Data:**\n\n"
            for list_name, cards in board_data.items():
                output += f"### {list_name}\n"
                if cards:
                    for card in cards:
                        output += f"{card}\n"
                else:
                    output += "- (No cards)\n"
                output += "\n"
            
            return output
            
        except Exception as e:
            return f"Error connecting to Trello: {str(e)}"
    
    # -------------------------------------------------------------------------
    # Project Plan Generator Tool
    # -------------------------------------------------------------------------
    @tool
    def generate_project_plan(additional_instructions: str = "") -> str:
        """Generate a comprehensive project execution plan from uploaded documents.
        Use this tool when the user asks to create a project plan, execution plan, or roadmap.
        
        Args:
            additional_instructions: Optional additional instructions or focus areas
        """
        if vector_store is None:
            return "❌ **No documents uploaded!** Please upload project documents (PRD, timeline, requirements) before generating a plan."
        
        if llm is None:
            return "❌ **LLM not configured!** Please ensure OpenAI API key is provided."
        
        try:
            # Retrieve all relevant documents
            all_docs = vector_store.similarity_search("project requirements timeline deliverables team milestones", k=20)
            
            if not all_docs:
                return "No document content found. Please upload valid project documents."
            
            # Combine document content
            combined_text = ""
            sources = {}
            for doc in all_docs:
                source = doc.metadata.get("source", "Unknown")
                if source not in sources:
                    sources[source] = []
                sources[source].append(doc.page_content)
            
            for source, chunks in sources.items():
                combined_text += f"\n\n--- Content from {source} ---\n"
                combined_text += "\n".join(chunks)
            
            if additional_instructions:
                combined_text += f"\n\n--- Additional Instructions ---\n{additional_instructions}"
            
            # Generate plan
            prompt = PROJECT_PLAN_PROMPT.format(documents_text=combined_text)
            response = llm.invoke(prompt)
            plan_content = response.content
            
            # Save to session state
            if session_state_callback:
                session_state_callback('current_plan', plan_content)
            
            return f"""✅ **Project Plan Generated Successfully!**

{plan_content}

---
📥 **Download Options Available:** Use the download buttons below to get this plan as PDF, DOCX, or Markdown."""
            
        except Exception as e:
            return f"Error generating project plan: {str(e)}"
    
    # -------------------------------------------------------------------------
    # Status Report Generator Tool
    # -------------------------------------------------------------------------
    @tool
    def generate_status_report(board_id_or_url: str) -> str:
        """Generate a weekly status report from a Trello board.
        Use this tool when the user asks to create a status report or weekly update.
        
        Args:
            board_id_or_url: Trello board ID or URL to generate the report from
        """
        if not trello_api_key or not trello_token:
            return "⚠️ **Trello credentials not configured!** Please enter your Trello API Key and Token in the sidebar."
        
        if llm is None:
            return "❌ **LLM not configured!** Please ensure OpenAI API key is provided."
        
        try:
            trello_client = TrelloClient(trello_api_key, trello_token)
            board_data = trello_client.fetch_board_data(board_id_or_url)
            
            if "error" in board_data:
                return f"Error fetching Trello data: {board_data['error']}"
            
            formatted_data = "\n".join([
                f"## {list_name}\n" + "\n".join(cards) 
                for list_name, cards in board_data.items()
            ])
            
            current_date = datetime.now().strftime("%Y-%m-%d")
            prompt = STATUS_REPORT_PROMPT.format(trello_data=formatted_data, date=current_date)
            
            response = llm.invoke(prompt)
            report_content = response.content
            
            if session_state_callback:
                session_state_callback('current_report', report_content)
            
            return f"""✅ **Status Report Generated Successfully!**

{report_content}

---
📥 **Download Options Available:** Use the download buttons below to get this report as PDF, DOCX, or Markdown."""
            
        except Exception as e:
            return f"Error generating status report: {str(e)}"
    
    # -------------------------------------------------------------------------
    # Return all tools
    # -------------------------------------------------------------------------
    return [
        search_project_documents,
        fetch_trello_board,
        generate_project_plan,
        generate_status_report,
    ]

