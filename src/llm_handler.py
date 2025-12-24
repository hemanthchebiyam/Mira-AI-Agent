import os
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any

from openai import OpenAI, OpenAIError
from .prompts import STATUS_REPORT_PROMPT, PROJECT_PLAN_PROMPT
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
            
from .tools import create_agent_tools

class LLMHandler:
    """
    Original LLM Handler - preserved for backward compatibility.
    Used by the existing Project Planning and Status Reports tabs.
    """
    def __init__(self, api_key=None, model="gpt-4o-mini"):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None

        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception:
                pass  # Client will remain None

    def _ensure_client(self):
        if not self.client and self.api_key:
             self.client = OpenAI(api_key=self.api_key)
        return self.client

    def generate_status_report(self, trello_data):
        """Generate weekly status report from Trello data"""
        if not self._ensure_client():
            return "Error: OpenAI API Key is missing or invalid."

        formatted_data = "\n".join([
            f"## {list_name}\n" + "\n".join(cards) 
            for list_name, cards in trello_data.items()
        ])
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        prompt = STATUS_REPORT_PROMPT.format(trello_data=formatted_data, date=current_date)
        
        return self._call_llm(prompt, "You are a helpful Technical Program Manager assistant.")

    def generate_project_plan(self, documents_text):
        """Generate project plan from documents"""
        if not self._ensure_client():
            return "Error: OpenAI API Key is missing or invalid."

        prompt = PROJECT_PLAN_PROMPT.format(documents_text=documents_text)
        return self._call_llm(prompt, "You are an expert Technical Program Manager.")

    def _call_llm(self, user_prompt, system_prompt):
        if not self.client:
             return "Error: OpenAI Client not initialized. Check API Key."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"


# ============================================================================
# LangChain Agentic Handler - New Implementation
# ============================================================================

AGENT_SYSTEM_PROMPT = """You are Mira, an intelligent Technical Program Management (TPM) AI assistant.

**CRITICAL: ALWAYS SEARCH DOCUMENTS FIRST**
When a user asks ANY question about their project (milestones, timeline, team, scope, requirements, etc.), you MUST use the `search_project_documents` tool FIRST to find the answer. Do NOT ask for clarification - just search the documents.

**Your Tools:**
1. `search_project_documents` - Search uploaded documents. USE THIS FIRST for any project question.
2. `fetch_trello_board` - Get live Trello data (needs board URL/ID)
3. `generate_project_plan` - Create a full project plan from documents
4. `generate_status_report` - Create status report from Trello board

**Rules:**
- For questions like "What are the milestones?" → Use search_project_documents immediately
- ALWAYS cite source documents: "According to `filename.pdf`..."
- Never make up information - only use what's in the search results
- If search returns no results, tell the user you couldn't find that information
- Be concise but thorough

**Examples:**
- User: "What are the key milestones?" → Call search_project_documents("key milestones timeline")
- User: "Who is the project lead?" → Call search_project_documents("project lead manager team")
- User: "Generate a project plan" → Call generate_project_plan()"""


class AgenticLLMHandler:
    """
    LangChain-based Agentic LLM Handler with RAG capabilities.
    This is the "Brain" of the new AI Assistant tab.
    """
    
    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-4o-mini",
        trello_api_key: str = None,
        trello_token: str = None,
        session_state_callback: Callable = None,
        get_content_callback: Callable = None
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.trello_api_key = trello_api_key
        self.trello_token = trello_token
        self.session_state_callback = session_state_callback
        self.get_content_callback = get_content_callback
        
        # LangChain components
        self.llm = None
        self.agent = None
        self.agent_executor = None
        self.memory = None
        self.vector_store = None
        self.tools = []
        
        # Initialize if API key is available
        if self.api_key:
            self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the LangChain ChatOpenAI instance."""
        try:
            from langchain_openai import ChatOpenAI
            
            self.llm = ChatOpenAI(
                model=self.model,
                api_key=self.api_key,
                temperature=0.7
            )
        except Exception as e:
            print(f"Error initializing LLM: {e}")
            self.llm = None
    
    def set_vector_store(self, vector_store):
        """Set the vector store for document retrieval."""
        self.vector_store = vector_store
        self._rebuild_agent()
    
    def update_credentials(
        self, 
        trello_api_key: str = None, 
        trello_token: str = None,
        email_sender: str = None,
        email_password: str = None
    ):
        """Update API credentials and rebuild the agent."""
        if trello_api_key:
            self.trello_api_key = trello_api_key
        if trello_token:
            self.trello_token = trello_token
        
        self.email_sender = email_sender
        self.email_password = email_password
        self._rebuild_agent()
    
    def _rebuild_agent(self):
        """Rebuild the agent with updated tools and configuration."""
        if not self.llm:
            return
        
        try:
            
            
            # Create tools with current configuration
            self.tools = create_agent_tools(
                vector_store=self.vector_store,
                llm=self.llm,
                trello_api_key=self.trello_api_key,
                trello_token=self.trello_token,
                session_state_callback=self.session_state_callback,
                get_content_callback=self.get_content_callback,
                email_sender=getattr(self, 'email_sender', None),
                email_password=getattr(self, 'email_password', None)
            )
            
            # Create the prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", AGENT_SYSTEM_PROMPT),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ])
            
            # Initialize memory if not exists
            if self.memory is None:
                self.memory = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True
                )
            
            # Create the agent
            self.agent = create_tool_calling_agent(self.llm, self.tools, prompt)
            
            # Create the executor
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                memory=self.memory,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=10
            )
            
        except Exception as e:
            print(f"Error building agent: {e}")
            self.agent_executor = None
    
    def chat(self, user_message: str) -> str:
        """
        Process a user message through the agent.
        
        Args:
            user_message: The user's input message
            
        Returns:
            The agent's response as a string
        """
        if not self.api_key:
            return "⚠️ **OpenAI API Key Required!** Please enter your API key in the sidebar configuration."
        
        if not self.llm:
            self._initialize_llm()
            if not self.llm:
                return "❌ **Failed to initialize LLM.** Please check your API key."
        
        # Ensure agent is built
        if not self.agent_executor:
            self._rebuild_agent()
        
        if not self.agent_executor:
            return "❌ **Agent not initialized.** Please try again."
        
        try:
            result = self.agent_executor.invoke({"input": user_message})
            return result.get("output", "I couldn't generate a response. Please try again.")
        except Exception as e:
            error_msg = str(e)
            if "api_key" in error_msg.lower():
                return "⚠️ **Invalid API Key.** Please check your OpenAI API key in the sidebar."
            return f"❌ **Error:** {error_msg}"
    
    def clear_memory(self):
        """Clear the conversation memory."""
        if self.memory:
            self.memory.clear()
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get the chat history as a list of messages."""
        if not self.memory:
            return []
        
        messages = []
        try:
            history = self.memory.load_memory_variables({})
            for msg in history.get("chat_history", []):
                if hasattr(msg, 'type') and hasattr(msg, 'content'):
                    messages.append({
                        "role": "user" if msg.type == "human" else "assistant",
                        "content": msg.content
                    })
        except:
            pass
        
        return messages
    
    def is_ready(self) -> bool:
        """Check if the agent is ready to process messages."""
        return self.llm is not None and self.agent_executor is not None
