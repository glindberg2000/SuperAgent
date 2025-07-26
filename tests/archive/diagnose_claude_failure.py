#!/usr/bin/env python3
"""
Diagnose exactly why Claude Code is failing in containers
Get the actual error messages
"""

import subprocess
import json

def diagnose_claude_failure():
    """Get detailed error messages from Claude Code failures"""
    print("🔍 DIAGNOSING CLAUDE CODE FAILURES IN CONTAINERS")
    print("=" * 60)
    
    containers = ['claude-isolated-discord', 'claude-fullstackdev-persistent']
    
    for container in containers:
        print(f"\n🩺 DIAGNOSING: {container}")
        print("-" * 50)
        
        # Test 1: Try claude command with full error output
        print("1. Testing basic claude command with full error output...")
        try:
            result = subprocess.run([
                'docker', 'exec', container, 'claude', '--help'
            ], capture_output=True, text=True, timeout=15)
            
            print(f"   Exit code: {result.returncode}")
            print(f"   STDOUT: {result.stdout[:500]}...")
            print(f"   STDERR: {result.stderr[:500]}...")
            
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 2: Try a simple claude print command with verbose errors
        print("\n2. Testing claude print command with detailed errors...")
        try:
            result = subprocess.run([
                'docker', 'exec', container, 'claude', 
                '--dangerously-skip-permissions', '--print', 'test message'
            ], capture_output=True, text=True, timeout=30)
            
            print(f"   Exit code: {result.returncode}")
            print(f"   STDOUT: {result.stdout}")
            print(f"   STDERR: {result.stderr}")
            
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 3: Check claude auth status with full output
        print("\n3. Checking claude auth status with full output...")
        try:
            result = subprocess.run([
                'docker', 'exec', container, 'claude', 'auth', 'status'
            ], capture_output=True, text=True, timeout=15)
            
            print(f"   Exit code: {result.returncode}")
            print(f"   STDOUT: {result.stdout}")
            print(f"   STDERR: {result.stderr}")
            
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 4: Check if Claude Code config exists
        print("\n4. Checking Claude Code configuration files...")
        try:
            result = subprocess.run([
                'docker', 'exec', container, 'find', '/home/node', '-name', '*.json', '-type', 'f'
            ], capture_output=True, text=True, timeout=10)
            
            print(f"   Config files found:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"     {line}")
            
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 5: Check contents of .claude directory
        print("\n5. Checking .claude directory contents...")
        try:
            result = subprocess.run([
                'docker', 'exec', container, 'ls', '-la', '/home/node/.claude'
            ], capture_output=True, text=True, timeout=10)
            
            print(f"   .claude directory:")
            print(f"   {result.stdout}")
            if result.stderr:
                print(f"   STDERR: {result.stderr}")
            
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 6: Try to read the .claude.json file
        print("\n6. Checking .claude.json file contents...")
        try:
            result = subprocess.run([
                'docker', 'exec', container, 'cat', '/home/node/.claude.json'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"   .claude.json contents:")
                try:
                    config = json.loads(result.stdout)
                    print(f"   Keys present: {list(config.keys())}")
                    if 'userID' in config:
                        print(f"   userID: {config['userID'][:20]}..." if config['userID'] else "   userID: EMPTY")
                    if 'history' in config:
                        print(f"   history entries: {len(config.get('history', []))}")
                except json.JSONDecodeError as e:
                    print(f"   JSON parse error: {e}")
                    print(f"   Raw content: {result.stdout[:200]}...")
            else:
                print(f"   Failed to read .claude.json: {result.stderr}")
            
        except Exception as e:
            print(f"   Exception: {e}")
        
        # Test 7: Check environment variables that might affect Claude
        print("\n7. Checking relevant environment variables...")
        env_vars = ['ANTHROPIC_API_KEY', 'DISCORD_TOKEN', 'HOME', 'USER']
        for env_var in env_vars:
            try:
                result = subprocess.run([
                    'docker', 'exec', container, 'printenv', env_var
                ], capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    value = result.stdout.strip()
                    if env_var in ['ANTHROPIC_API_KEY', 'DISCORD_TOKEN']:
                        print(f"   {env_var}: {value[:20]}..." if value else f"   {env_var}: EMPTY")
                    else:
                        print(f"   {env_var}: {value}")
                else:
                    print(f"   {env_var}: NOT SET")
                    
            except Exception as e:
                print(f"   {env_var}: Exception - {e}")
        
        # Test 8: Check if there are any running processes that might interfere
        print("\n8. Checking running processes in container...")
        try:
            result = subprocess.run([
                'docker', 'exec', container, 'ps', 'aux'
            ], capture_output=True, text=True, timeout=10)
            
            print(f"   Running processes:")
            for line in result.stdout.strip().split('\n'):
                if 'claude' in line.lower() or 'node' in line.lower():
                    print(f"     {line}")
            
        except Exception as e:
            print(f"   Exception: {e}")

def main():
    print("🩺 DETAILED CLAUDE CODE FAILURE DIAGNOSIS")
    print("=" * 60)
    print("Getting actual error messages - no assumptions!")
    print("")
    
    diagnose_claude_failure()
    
    print("\n" + "=" * 60)
    print("🎯 Use this detailed information to identify the exact problem")

if __name__ == "__main__":
    main()