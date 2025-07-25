#!/usr/bin/env python3
"""
Discord Claude Manager - Persistent Discord monitoring for Claude Code container
Runs continuously inside the Claude Code container to maintain Discord presence
"""

import subprocess
import time
import json
import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/workspace/discord_claude_manager.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DiscordClaudeManager:
    def __init__(self):
        self.running = True
        self.last_checkin = None
        self.check_interval = 30  # seconds
        
    def execute_claude_command(self, prompt, timeout=60):
        """Execute a Claude Code command safely with timeout"""
        try:
            cmd = [
                'claude',
                '--dangerously-skip-permissions',
                '--print',
                prompt
            ]
            
            logger.info(f"Executing Claude command: {prompt[:100]}...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                logger.info("Claude command executed successfully")
                return result.stdout.strip()
            else:
                logger.error(f"Claude command failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Claude command timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Claude command error: {e}")
            return None
    
    def check_for_messages(self):
        """Check for new Discord messages and respond"""
        prompt = """Check for any new Discord messages using get_unread_messages. 
        If you find any messages directed at the bot or mentioning it:
        1. Respond appropriately to each message
        2. Return a JSON summary of what you found and did
        
        Format response as: {"messages_found": N, "responses_sent": N, "summary": "description"}"""
        
        result = self.execute_claude_command(prompt, timeout=45)
        if result:
            try:
                # Try to parse JSON response
                if result.startswith('{'):
                    data = json.loads(result)
                    if data.get('messages_found', 0) > 0:
                        logger.info(f"Handled {data['messages_found']} messages: {data['summary']}")
                    return data
            except json.JSONDecodeError:
                # Non-JSON response is fine, just log it
                if "message" in result.lower() or "found" in result.lower():
                    logger.info(f"Discord activity: {result[:200]}...")
                    
        return {"messages_found": 0, "responses_sent": 0, "summary": "no activity"}
    
    def send_checkin(self):
        """Send periodic check-in message to Discord"""
        checkin_prompt = f"""Send a brief status update to the #general Discord channel:
        "🤖 Claude Code container active - {datetime.now().strftime('%H:%M')} UTC - Ready for tasks!"
        
        Keep it short and professional."""
        
        result = self.execute_claude_command(checkin_prompt, timeout=30)
        if result:
            logger.info("Check-in message sent successfully")
            self.last_checkin = datetime.now()
            return True
        return False
    
    def should_checkin(self):
        """Determine if we should send a check-in message"""
        if not self.last_checkin:
            return True  # First checkin
            
        # Check in every 2 hours
        time_since_checkin = (datetime.now() - self.last_checkin).total_seconds()
        return time_since_checkin > 7200  # 2 hours
    
    def run(self):
        """Main monitoring loop"""
        logger.info("🚀 Discord Claude Manager starting...")
        
        # Initial check-in
        logger.info("Sending initial check-in...")
        self.send_checkin()
        
        # Main monitoring loop
        while self.running:
            try:
                logger.info("Checking for Discord messages...")
                activity = self.check_for_messages()
                
                # Periodic check-in
                if self.should_checkin():
                    logger.info("Sending periodic check-in...")
                    self.send_checkin()
                
                # Wait before next check
                logger.info(f"Waiting {self.check_interval}s before next check...")
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(60)  # Wait longer on errors
                
        logger.info("Discord Claude Manager stopped")

if __name__ == "__main__":
    manager = DiscordClaudeManager()
    manager.run()