from xai_sdk import Client
from xai_sdk.chat import user, system
import os
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()
api_key = os.getenv("XAI_API_KEY")
if not api_key:
    raise ValueError("XAI_API_KEY not set in environment.")

client = Client(api_key=api_key)

chat = client.chat.create(model="grok-4-0709", temperature=0)
chat.append(system("You are a PhD-level mathematician."))
chat.append(user("What is 2 + 2?"))

response = chat.sample()
print(response.content)
