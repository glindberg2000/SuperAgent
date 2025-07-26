#!/usr/bin/env python3
"""
Actually test if Claude Code is working inside containers
Don't assume - verify with evidence
"""

import subprocess
import json
import sys

def test_container_claude_functionality():
    """Test if Claude Code actually works inside the containers"""
    print("🔍 TESTING ACTUAL CLAUDE CODE FUNCTIONALITY IN CONTAINERS")
    print("=" * 60)
    
    # Get list of Claude containers
    try:
        result = subprocess.run(['docker', 'ps', '--filter', 'name=claude', '--format', '{{.Names}}'], 
                               capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Failed to get container list")
            return
        
        containers = result.stdout.strip().split('\n') if result.stdout.strip() else []
        print(f"Found {len(containers)} Claude containers: {containers}")
        
    except Exception as e:
        print(f"❌ Error getting containers: {e}")
        return
    
    for container in containers:
        print(f"\n🧪 Testing container: {container}")
        print("-" * 40)
        
        # Test 1: Basic Claude version check
        print("1. Testing basic Claude availability...")
        try:
            result = subprocess.run(['docker', 'exec', container, 'claude', '--version'], 
                                   capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"   ✅ Claude version: {version}")
            else:
                print(f"   ❌ Claude version failed: {result.stderr}")
                continue
                
        except Exception as e:
            print(f"   ❌ Claude version error: {e}")
            continue
        
        # Test 2: Test Claude authentication/config
        print("2. Testing Claude configuration...")
        try:
            result = subprocess.run(['docker', 'exec', container, 'claude', 'auth', 'status'], 
                                   capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                auth_status = result.stdout.strip()
                print(f"   ✅ Auth status: {auth_status}")
            else:
                print(f"   ❌ Auth status failed: {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ Auth status error: {e}")
        
        # Test 3: Test MCP server status
        print("3. Testing MCP server connection...")
        try:
            result = subprocess.run(['docker', 'exec', container, 'claude', 'mcp', 'list'], 
                                   capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                mcp_output = result.stdout.strip()
                print(f"   ✅ MCP servers: {mcp_output}")
                
                # Check if Discord MCP is connected
                if 'Connected' in mcp_output and 'discord' in mcp_output.lower():
                    print("   ✅ Discord MCP server is connected")
                else:
                    print("   ⚠️  Discord MCP server may not be connected")
            else:
                print(f"   ❌ MCP list failed: {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ MCP list error: {e}")
        
        # Test 4: Try to execute a simple Claude command
        print("4. Testing Claude execution...")
        try:
            test_message = f"Container {container} test - respond with your status and capabilities"
            result = subprocess.run([
                'docker', 'exec', container, 'claude', 
                '--dangerously-skip-permissions', '--print', test_message
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                claude_response = result.stdout.strip()
                print(f"   ✅ Claude response: {claude_response[:200]}...")
                
                # Check if response looks valid (not empty, not just error)
                if len(claude_response) > 10 and 'error' not in claude_response.lower():
                    print("   ✅ Claude is responding properly")
                else:
                    print("   ❌ Claude response looks like an error")
                    
            else:
                print(f"   ❌ Claude execution failed: {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ Claude execution error: {e}")
        
        # Test 5: Check container environment and keys
        print("5. Testing container environment...")
        try:
            # Check for Discord token
            result = subprocess.run(['docker', 'exec', container, 'printenv', 'DISCORD_TOKEN'], 
                                   capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and result.stdout.strip():
                token = result.stdout.strip()
                print(f"   ✅ Discord token present: {token[:20]}...")
            else:
                print("   ❌ No Discord token found")
            
            # Check for Anthropic API key (should NOT be present in Claude Code containers)
            result = subprocess.run(['docker', 'exec', container, 'printenv', 'ANTHROPIC_API_KEY'], 
                                   capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and result.stdout.strip():
                api_key = result.stdout.strip()
                print(f"   ⚠️  PROBLEM: Anthropic API key present (interferes with subscription auth): {api_key[:20]}...")
            else:
                print("   ✅ No Anthropic API key found (correct for Claude Code subscription auth)")
                
        except Exception as e:
            print(f"   ❌ Environment check error: {e}")
        
        # Test 6: Check container workspace
        print("6. Testing container workspace...")
        try:
            result = subprocess.run(['docker', 'exec', container, 'ls', '-la', '/workspace'], 
                                   capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                workspace_contents = result.stdout.strip()
                print(f"   ✅ Workspace contents:")
                for line in workspace_contents.split('\n')[:5]:  # Show first 5 lines
                    print(f"     {line}")
            else:
                print(f"   ❌ Workspace check failed: {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ Workspace check error: {e}")
        
        print(f"\n{'='*40}")
        print(f"Container {container} test complete")

def main():
    print("🕵️ ACTUAL CLAUDE CODE CONTAINER VERIFICATION")
    print("=" * 60)
    print("Testing if Claude Code is actually working inside containers...")
    print("No assumptions - only evidence-based verification!")
    print("")
    
    test_container_claude_functionality()
    
    print("\n" + "=" * 60)
    print("🎯 CONCLUSION: Use this evidence to determine if containers actually work")
    print("Don't trust deployment success - trust actual Claude Code responses!")

if __name__ == "__main__":
    main()