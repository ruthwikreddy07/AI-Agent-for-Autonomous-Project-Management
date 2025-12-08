import os
import requests
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

# ==========================================
# 1. CONFIGURATION (Fill these in!)
# ==========================================
# PASTE YOUR GROQ API KEY HERE:

# PASTE YOUR n8n URL HERE (The same one you used before):
N8N_WEBHOOK_URL = "http://localhost:5678/webhook-test/test-connection"

# ==========================================
# 2. DEFINE THE TOOLS (The Hands)
# ==========================================
@tool
def create_task_in_trello(task_name: str, description: str = ""):
    """
    Creates a new card in the Trello Backlog.
    Use this when the user asks to add a task, fix a bug, or do work.
    """
    print(f"🛠️ TOOL CALLED: Creating task '{task_name}'...")
    
    payload = {
        "task_name": task_name,
        "description": description
    }
    
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            return "Success! Task created in Trello."
        else:
            return f"Error: n8n returned {response.status_code}"
    except Exception as e:
        return f"Connection Failed: {e}"

# ==========================================
# 3. INITIALIZE THE BRAIN
# ==========================================
# We use Llama3-70b because it is smart enough to use tools.
llm = ChatGroq(model="llama-3.3-70b-versatile")

# We verify the LLM knows about our tool
llm_with_tools = llm.bind_tools([create_task_in_trello])

# ==========================================
# 4. THE CHAT LOOP
# ==========================================
print("🤖 AI PROJECT MANAGER IS ONLINE.")
print("Type 'quit' to exit.\n")

messages = [
    SystemMessage(content="You are an autonomous Project Manager. You have tools to manage Trello. Use them whenever necessary.")
]

while True:
    user_input = input("You: ")
    if user_input.lower() in ["quit", "exit"]:
        break

    # Add user message to history
    messages.append(HumanMessage(content=user_input))

    # AI Thinks...
    response = llm_with_tools.invoke(messages)
    
    # Add AI response to history
    messages.append(response)

    # CHECK: Did the AI decide to use a tool?
    if response.tool_calls:
        print("🧠 AI Decided: I need to use a tool.")
        
        # Execute the tool(s)
        for tool_call in response.tool_calls:
            if tool_call["name"] == "create_task_in_trello":
                # Run our python function
                tool_result = create_task_in_trello.invoke(tool_call["args"])
                print(f"✅ Tool Result: {tool_result}")
                
                # NOTE: In a full app, we would feed this result back to the AI. 
                # For this test, we just print it.
    else:
        # If no tool needed, just print the text reply
        print(f"🤖 AI: {response.content}")