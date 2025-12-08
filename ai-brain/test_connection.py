import requests
import json

# 1. The Setup: Where are we sending the message?
# PASTE YOUR N8N TEST URL BELOW
n8n_url = "http://localhost:5678/webhook-test/test-connection"
# The "Order" we are giving the agent
task_payload = {
    "task_name": "Fix the Login Page CSS",
    "description": "The button is misaligned on mobile.",
    "priority": "High"
}

print(f"🤖 Agent is asking n8n to create task: '{task_payload['task_name']}'...")

try:
    response = requests.post(n8n_url, json=task_payload)
    
    if response.status_code == 200:
        print("✅ Command Sent! Check your Trello board now.")
    else:
        print(f"❌ Failed: {response.text}")

except Exception as e:
    print(f"❌ Error: {e}")