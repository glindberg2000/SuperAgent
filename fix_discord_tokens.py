#!/usr/bin/env python3
"""
Discord Token Cleanup Script
Standardizes .env file Discord tokens according to DISCORD_BOT_REGISTRY.md
"""

import os
import re
import shutil
from datetime import datetime

def backup_env_file(env_path):
    """Create timestamped backup of .env file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{env_path}.backup_{timestamp}"
    shutil.copy2(env_path, backup_path)
    print(f"✅ Created backup: {backup_path}")
    return backup_path

def standardize_discord_tokens(env_path):
    """
    Standardize Discord tokens in .env file according to registry
    """
    if not os.path.exists(env_path):
        print(f"❌ Error: {env_path} not found")
        return False
    
    # Create backup first
    backup_path = backup_env_file(env_path)
    
    # Read current .env file
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Track changes
    changes_made = []
    new_lines = []
    seen_tokens = set()
    
    # Token mapping (old -> new)
    token_mapping = {
        'DISCORD_TOKEN_CLAUDE': 'DISCORD_TOKEN_CODERDEV1',
        'DISCORD_TOKEN2': 'DISCORD_TOKEN_DEVOPS',
        'DISCORD_TOKEN_1': 'DISCORD_TOKEN_GROK4',
        'DISCORD_TOKEN_3': 'DISCORD_TOKEN_GEMINI'
    }
    
    # Standard tokens we want to keep
    standard_tokens = {
        'DISCORD_TOKEN_CODERDEV1': 'CryptoTax CoderDev1 bot (fullstack development)',
        'DISCORD_TOKEN_DEVOPS': 'SuperAgent DevOps bot (container management)', 
        'DISCORD_TOKEN_GROK4': 'SuperAgent Grok4 bot (research and analysis)',
        'DISCORD_TOKEN_GEMINI': 'SuperAgent Gemini bot (creative tasks)'
    }
    
    # Process each line
    for line in lines:
        original_line = line
        
        # Skip comments and empty lines
        if line.strip().startswith('#') or not line.strip():
            new_lines.append(line)
            continue
            
        # Check for Discord token lines
        if line.strip().startswith('DISCORD_TOKEN'):
            # Extract token name and value
            match = re.match(r'^(DISCORD_TOKEN[^=]*)\s*=\s*(.*)$', line.strip())
            if match:
                old_token_name = match.group(1)
                token_value = match.group(2).strip()
                
                # Remove any inline comments from token value
                token_value = re.sub(r'\s*#.*$', '', token_value)
                
                # Check if this is a token we want to rename
                if old_token_name in token_mapping:
                    new_token_name = token_mapping[old_token_name]
                    changes_made.append(f"Renamed {old_token_name} → {new_token_name}")
                    token_name = new_token_name
                else:
                    token_name = old_token_name
                
                # Only add if it's a standard token and we haven't seen it yet
                if token_name in standard_tokens and token_name not in seen_tokens:
                    comment = standard_tokens[token_name]
                    new_line = f"{token_name}={token_value}  # {comment}\n"
                    new_lines.append(new_line)
                    seen_tokens.add(token_name)
                    
                    if original_line.strip() != new_line.strip():
                        changes_made.append(f"Standardized {token_name} with comment")
                else:
                    # Skip duplicates or non-standard tokens
                    if token_name in seen_tokens:
                        changes_made.append(f"Removed duplicate {token_name}")
                    else:
                        changes_made.append(f"Removed non-standard token {token_name}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    # Report changes
    print(f"\n🔧 Discord Token Standardization Complete")
    print(f"📁 Backup created: {backup_path}")
    print(f"🎯 Standard tokens configured: {len(seen_tokens)}")
    
    if changes_made:
        print("\n📝 Changes made:")
        for change in changes_made:
            print(f"  • {change}")
    else:
        print("\n✨ No changes needed - tokens already standardized")
    
    print(f"\n📋 Active Discord tokens:")
    for token in sorted(seen_tokens):
        print(f"  • {token}: {standard_tokens[token]}")
    
    return True

def main():
    """Main cleanup function"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, '.env')
    
    print("🧹 Discord Token Cleanup Script")
    print("=" * 40)
    print("Standardizing Discord tokens according to DISCORD_BOT_REGISTRY.md")
    print()
    
    success = standardize_discord_tokens(env_path)
    
    if success:
        print("\n🎉 Cleanup completed successfully!")
        print("💡 Next steps:")
        print("  1. Review the updated .env file")
        print("  2. Update your Discord bot tokens with real values")
        print("  3. Test container startup with new token names")
    else:
        print("\n❌ Cleanup failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())