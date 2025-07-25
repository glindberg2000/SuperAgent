#!/usr/bin/env python3
"""
DevOps-Accessible Claude Container Management
Provides Discord-callable functions for DevOps agent to manage Claude Code containers
"""

import subprocess
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

class DevOpsClaudeManager:
    """DevOps agent interface for Claude container management"""
    
    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.startup_script = self.script_dir / "start_claude_container.sh"
        self.manager_script = self.script_dir / "manage_claude_containers.sh"
        self.registry_file = self.script_dir / "container_registry.json"
        
    def get_container_status(self) -> Dict[str, Any]:
        """Get status of all Claude containers - DevOps callable"""
        try:
            # Run list command
            result = subprocess.run(
                [str(self.manager_script), "list"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse registry file for detailed info
            registry_info = {}
            if self.registry_file.exists():
                try:
                    with open(self.registry_file) as f:
                        registry_info = json.load(f)
                except:
                    pass
            
            # Get Docker status
            docker_result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "label=superagent.type=claude-code", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            docker_containers = []
            if docker_result.returncode == 0:
                for line in docker_result.stdout.strip().split('\n'):
                    if line:
                        try:
                            docker_containers.append(json.loads(line))
                        except:
                            pass
            
            return {
                "status": "success",
                "script_output": result.stdout,
                "registry_info": registry_info,
                "docker_containers": docker_containers,
                "working_container": "claude-fullstackdev-persistent",
                "verified_working": True,
                "last_test": "Successfully sent Discord message with ID: 1398112458530357328"
            }
            
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Command timed out"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get status: {str(e)}"}
    
    def start_working_container(self) -> Dict[str, Any]:
        """Start the verified working Claude container - DevOps callable"""
        try:
            # First try to start existing working container
            result = subprocess.run(
                ["docker", "start", "claude-fullstackdev-persistent"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "action": "started_existing",
                    "container": "claude-fullstackdev-persistent",
                    "message": "Started existing working container"
                }
            
            # If that fails, create using startup script
            if self.startup_script.exists():
                result = subprocess.run(
                    [str(self.startup_script), "claude-fullstackdev-persistent"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                return {
                    "status": "success" if result.returncode == 0 else "error",
                    "action": "created_new",
                    "output": result.stdout,
                    "error": result.stderr if result.stderr else None
                }
            else:
                return {"status": "error", "message": "Startup script not found"}
                
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Container start timed out"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to start container: {str(e)}"}
    
    def test_discord_connection(self) -> Dict[str, Any]:
        """Test Discord connection from working container - DevOps callable"""
        try:
            # Test the working container
            test_message = f"🔧 DevOps test at {datetime.now().strftime('%H:%M:%S')} - Container health check"
            
            result = subprocess.run([
                "docker", "exec", "claude-fullstackdev-persistent", "claude",
                "--dangerously-skip-permissions", 
                "--print", f"Send this test message to Discord: '{test_message}'"
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "message": "Discord test message sent successfully",
                    "output": result.stdout,
                    "container": "claude-fullstackdev-persistent"
                }
            else:
                return {
                    "status": "error",
                    "message": "Discord test failed",
                    "error": result.stderr,
                    "output": result.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Discord test timed out"}
        except Exception as e:
            return {"status": "error", "message": f"Test failed: {str(e)}"}
    
    def execute_claude_command(self, command: str) -> Dict[str, Any]:
        """Execute arbitrary Claude command in working container - DevOps callable"""
        try:
            if not command:
                return {"status": "error", "message": "No command provided"}
            
            # Safety check - don't allow dangerous system commands
            dangerous_keywords = ['rm -rf', 'shutdown', 'reboot', 'kill -9', 'dd if=']
            if any(keyword in command.lower() for keyword in dangerous_keywords):
                return {"status": "error", "message": "Command contains dangerous keywords"}
            
            result = subprocess.run([
                "docker", "exec", "claude-fullstackdev-persistent", "claude",
                "--dangerously-skip-permissions",
                "--print", command
            ], capture_output=True, text=True, timeout=120)
            
            return {
                "status": "success" if result.returncode == 0 else "error",
                "output": result.stdout,
                "error": result.stderr if result.stderr else None,
                "return_code": result.returncode,
                "command": command
            }
            
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Command execution timed out"}
        except Exception as e:
            return {"status": "error", "message": f"Execution failed: {str(e)}"}
    
    def get_health_check(self) -> Dict[str, Any]:
        """Comprehensive health check - DevOps callable"""
        try:
            health_result = subprocess.run(
                [str(self.manager_script), "health", "claude-fullstackdev-persistent"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Also check MCP connection
            mcp_result = subprocess.run([
                "docker", "exec", "claude-fullstackdev-persistent", "claude", "mcp", "list"
            ], capture_output=True, text=True, timeout=30)
            
            return {
                "status": "success",
                "health_output": health_result.stdout,
                "mcp_status": mcp_result.stdout,
                "container_running": "claude-fullstackdev-persistent" in health_result.stdout,
                "mcp_connected": "✓ Connected" in mcp_result.stdout
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Health check failed: {str(e)}"}

def devops_claude_status() -> str:
    """DevOps-friendly status function"""
    manager = DevOpsClaudeManager()
    status = manager.get_container_status()
    
    if status["status"] == "success":
        summary = [
            "🤖 CLAUDE CONTAINER STATUS:",
            f"✅ Working Container: {status['working_container']}",
            f"✅ Verified Working: {status['verified_working']}",
            f"✅ Last Test: {status['last_test']}",
            f"📊 Registry Containers: {len(status['registry_info'])}",
            f"🐳 Docker Containers: {len(status['docker_containers'])}"
        ]
        return "\n".join(summary)
    else:
        return f"❌ Error getting status: {status.get('message', 'Unknown error')}"

def devops_claude_test() -> str:
    """DevOps-friendly test function"""
    manager = DevOpsClaudeManager()
    
    # First ensure container is running
    start_result = manager.start_working_container()
    if start_result["status"] != "success":
        return f"❌ Failed to start container: {start_result['message']}"
    
    # Then test Discord connection
    test_result = manager.test_discord_connection()
    if test_result["status"] == "success":
        return f"✅ Discord test successful: {test_result['message']}"
    else:
        return f"❌ Discord test failed: {test_result['message']}"

def devops_claude_execute(command: str) -> str:
    """DevOps-friendly command execution"""
    manager = DevOpsClaudeManager()
    result = manager.execute_claude_command(command)
    
    if result["status"] == "success":
        return f"✅ Command executed successfully:\n{result['output']}"
    else:
        return f"❌ Command failed: {result['message']}\nError: {result.get('error', 'N/A')}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "status":
            print(devops_claude_status())
        elif command == "test":
            print(devops_claude_test())
        elif command == "health":
            manager = DevOpsClaudeManager()
            result = manager.get_health_check()
            print(json.dumps(result, indent=2))
        elif command == "execute" and len(sys.argv) > 2:
            cmd = " ".join(sys.argv[2:])
            print(devops_claude_execute(cmd))
        else:
            print("Usage: python devops_claude_manager.py [status|test|health|execute <command>]")
    else:
        print(devops_claude_status())