import argparse
from xai_sdk import Client
from xai_sdk.chat import user, system
import os
from dotenv import load_dotenv
from datetime import datetime
import hashlib

# --- Argument Parsing ---
parser = argparse.ArgumentParser(description="Query Grok4 with a prompt or prompt file and save the response with full metadata.")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--prompt', type=str, help='Prompt string to send to Grok4')
group.add_argument('--prompt-file', type=str, help='Path to file containing prompt text (e.g., PRD)')
parser.add_argument('--tag', type=str, required=True, help='Short tag for this request (e.g., fmv_research)')
parser.add_argument('--output-dir', type=str, default='grok4_responses', help='Directory to save Grok4 responses')
parser.add_argument('--system', type=str, default='You are a PhD-level technical research assistant. Answer with web research, best practices, and cite sources if possible.', help='System prompt for Grok4')
args = parser.parse_args()

# --- Load .env and API Key ---
load_dotenv()
api_key = os.getenv("XAI_API_KEY")
if not api_key:
    raise ValueError("XAI_API_KEY not set in environment.")

# --- Prepare Prompt ---
if args.prompt:
    prompt_text = args.prompt
    prompt_source = 'inline'
    prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()[:12]
else:
    with open(args.prompt_file, 'r') as f:
        prompt_text = f.read()
    prompt_source = os.path.basename(args.prompt_file)
    with open(args.prompt_file, 'rb') as f:
        prompt_hash = hashlib.sha256(f.read()).hexdigest()[:12]

# --- Prepare Output Filename ---
os.makedirs(args.output_dir, exist_ok=True)
timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
output_filename = f"{args.tag}_{timestamp}_{prompt_hash}.md"
output_path = os.path.join(args.output_dir, output_filename)

# --- Query Grok4 ---
client = Client(api_key=api_key)
chat = client.chat.create(model="grok-4-0709", temperature=0)
chat.append(system(args.system))
chat.append(user(prompt_text))
print(f"[INFO] Sending prompt to Grok4...\n---\n{prompt_text[:200]}{'...' if len(prompt_text) > 200 else ''}\n---")
response = chat.sample()

# --- Save Output ---
with open(output_path, 'w') as f:
    f.write(f"# Grok4 Response: {args.tag}\n")
    f.write(f"- **Tag:** {args.tag}\n")
    f.write(f"- **Timestamp:** {timestamp}\n")
    f.write(f"- **Originating Request:** {prompt_source} (SHA256: {prompt_hash})\n")
    f.write(f"\n## Prompt\n\n{prompt_text}\n\n")
    f.write(f"## Response\n\n{response.content}\n")

print(f"[SUCCESS] Grok4 response saved to: {output_path}\n")
print("[REVIEW] Please review the response for relevance before posting to Discord or sharing externally.")
print("[SUMMARY]\n---\n" + response.content[:500] + ("..." if len(response.content) > 500 else ""))
