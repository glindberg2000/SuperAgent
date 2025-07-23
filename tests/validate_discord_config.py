#!/usr/bin/env python3
"""
Discord Configuration Validator
Validates that Discord tokens are properly configured for multi-bot functionality
"""

import os
from dotenv import load_dotenv
from typing import Dict, List, Set

def validate_discord_tokens() -> bool:
    """Validate Discord token configuration"""
    load_dotenv()
    
    print("🔍 Discord Configuration Validator")
    print("=" * 40)
    
    # Get all Discord tokens
    tokens = {
        'DISCORD_TOKEN_GROK': os.getenv('DISCORD_TOKEN_GROK'),
        'DISCORD_TOKEN2': os.getenv('DISCORD_TOKEN2'),
        'DISCORD_TOKEN3': os.getenv('DISCORD_TOKEN3'),
    }
    
    # Check for missing tokens
    missing_tokens = [name for name, token in tokens.items() if not token or not token.strip()]
    if missing_tokens:
        print(f"❌ Missing tokens: {', '.join(missing_tokens)}")
        return False
    
    # Check for duplicate tokens
    token_values = [token.strip() for token in tokens.values()]
    unique_tokens = set(token_values)
    
    print(f"📊 Token Analysis:")
    print(f"  Total tokens configured: {len(token_values)}")
    print(f"  Unique tokens found: {len(unique_tokens)}")
    
    # Show token endings for identification
    print(f"\n🔑 Token Identification:")
    for name, token in tokens.items():
        if token:
            print(f"  {name}: ...{token.strip()[-12:]}")
    
    if len(unique_tokens) == len(token_values):
        print(f"\n✅ SUCCESS: All {len(token_values)} tokens are unique!")
        print("   Multi-bot functionality should work correctly.")
        return True
    else:
        duplicates = len(token_values) - len(unique_tokens)
        print(f"\n❌ PROBLEM: {duplicates} duplicate token(s) detected!")
        print("   This will cause all agents to appear as the same Discord bot.")
        
        # Show which tokens are duplicated
        for token in unique_tokens:
            matching_names = [name for name, t in tokens.items() if t and t.strip() == token]
            if len(matching_names) > 1:
                print(f"   Shared token (...{token[-12:]}): {', '.join(matching_names)}")
        
        print(f"\n🔧 FIX REQUIRED:")
        print("   1. Create separate Discord bot applications at https://discord.com/developers/applications")
        print("   2. Get unique bot tokens for each application")
        print("   3. Update .env file with different tokens:")
        print("      DISCORD_TOKEN_GROK=bot1_token_here   # For Grok4 Agent")
        print("      DISCORD_TOKEN2=bot2_token_here       # For Claude Agent")
        print("      DISCORD_TOKEN3=bot3_token_here       # For Gemini Agent")
        print("   4. Run this validator again to confirm")
        
        return False

def show_bot_setup_instructions():
    """Show instructions for setting up multiple Discord bots"""
    print(f"\n📚 Multi-Bot Setup Instructions:")
    print("   1. Go to https://discord.com/developers/applications")
    print("   2. Create 3 separate bot applications:")
    print("      - SuperAgent-Grok4  (for DISCORD_TOKEN_GROK)")
    print("      - SuperAgent-Claude (for DISCORD_TOKEN2)")
    print("      - SuperAgent-Gemini (for DISCORD_TOKEN3)")
    print("   3. For each bot:")
    print("      - Go to Bot section")
    print("      - Copy the Bot Token")
    print("      - Enable 'Message Content Intent'")
    print("      - Invite to your Discord server with appropriate permissions")
    print("   4. Update .env file with the 3 different tokens")
    print("   5. Test with: python test_discord_identities.py")

if __name__ == "__main__":
    success = validate_discord_tokens()
    
    if not success:
        show_bot_setup_instructions()
    
    exit(0 if success else 1)