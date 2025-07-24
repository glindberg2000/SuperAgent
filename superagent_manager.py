#!/usr/bin/env python3
"""
SuperAgent Manager - Main application for deploying and managing agents
Integrates single agent launcher with CLI dashboard
"""

import asyncio
import os
import subprocess
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
from datetime import datetime
import psutil

from dotenv import load_dotenv
from agent_dashboard import SuperAgentDashboard

# Load environment variables
load_dotenv()

class SuperAgentManager:
    """Main SuperAgent management system"""
    
    def __init__(self):
        self.running_agents = {}
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Available agent types and their configurations
        self.agent_configs = {
            "grok4_agent": {
                "name": "Grok4Agent",
                "token_env": "DISCORD_TOKEN_GROK",
                "api_key_env": "XAI_API_KEY",
                "description": "Expert AI researcher with live web search",
                "llm_type": "grok4"
            },
            "claude_agent": {
                "name": "ClaudeAgent", 
                "token_env": "DISCORD_TOKEN2",
                "api_key_env": "ANTHROPIC_API_KEY",
                "description": "Thoughtful reasoning and code analysis specialist",
                "llm_type": "claude"
            },
            "gemini_agent": {
                "name": "GeminiAgent",
                "token_env": "DISCORD_TOKEN3", 
                "api_key_env": "GOOGLE_AI_API_KEY",
                "description": "Creative collaborator and multimodal specialist",
                "llm_type": "gemini"
            },
            "o3_agent": {
                "name": "O3Agent",
                "token_env": "DISCORD_TOKEN4",
                "api_key_env": "OPENAI_API_KEY", 
                "description": "Logical reasoning and mathematical specialist",
                "llm_type": "openai"
            }
        }
    
    def validate_agent_config(self, agent_type: str) -> Tuple[bool, str]:
        """Validate agent configuration and tokens"""
        if agent_type not in self.agent_configs:
            return False, f"Unknown agent type: {agent_type}"
        
        config = self.agent_configs[agent_type]
        
        # Check Discord token
        token = os.getenv(config["token_env"])
        if not token:
            return False, f"Missing Discord token: {config['token_env']}"
        
        # Check API key
        api_key = os.getenv(config["api_key_env"]) 
        if not api_key:
            return False, f"Missing API key: {config['api_key_env']}"
        
        # Check server ID
        server_id = os.getenv("DEFAULT_SERVER_ID")
        if not server_id:
            return False, "Missing DEFAULT_SERVER_ID"
        
        return True, "Configuration valid"
    
    def deploy_agent(self, agent_type: str) -> Tuple[bool, str]:
        """Deploy a single agent"""
        # Validate configuration
        is_valid, msg = self.validate_agent_config(agent_type)
        if not is_valid:
            return False, msg
        
        # Check if agent is already running
        if agent_type in self.running_agents:
            return False, f"Agent {agent_type} is already running (PID: {self.running_agents[agent_type]['pid']})"
        
        try:
            # Get virtual environment python
            venv_python = Path(__file__).parent / ".venv" / "bin" / "python"
            if not venv_python.exists():
                venv_python = "python"
            
            # Create log file
            log_file = self.logs_dir / f"{agent_type}.log"
            
            # Start agent process
            with open(log_file, 'w') as log_handle:
                process = subprocess.Popen(
                    [str(venv_python), "launch_single_agent.py", agent_type],
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    cwd=str(Path(__file__).parent)
                )
            
            # Give it a moment to start
            import time
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                # Store process info
                self.running_agents[agent_type] = {
                    "pid": process.pid,
                    "process": process,
                    "started": datetime.now(),
                    "log_file": str(log_file),
                    "config": self.agent_configs[agent_type]
                }
                
                return True, f"Successfully deployed {agent_type} (PID: {process.pid})"
            else:
                # Process failed to start
                try:
                    with open(log_file, 'r') as f:
                        error_output = f.read()
                except:
                    error_output = "Could not read log file"
                
                return False, f"Agent failed to start. Check {log_file} for details"
                
        except Exception as e:
            return False, f"Failed to deploy agent: {e}"
    
    def stop_agent(self, agent_type: str) -> Tuple[bool, str]:
        """Stop a running agent"""
        if agent_type not in self.running_agents:
            return False, f"Agent {agent_type} is not running"
        
        try:
            agent_info = self.running_agents[agent_type]
            process = agent_info["process"]
            
            # Terminate the process gracefully
            process.terminate()
            
            # Wait for it to stop
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't stop
                process.kill()
                process.wait()
            
            # Remove from running agents
            del self.running_agents[agent_type]
            
            return True, f"Successfully stopped {agent_type}"
            
        except Exception as e:
            return False, f"Failed to stop agent: {e}"
    
    def list_agents(self) -> Dict:
        """List all available and running agents"""
        return {
            "available": self.agent_configs,
            "running": {
                name: {
                    "pid": info["pid"],
                    "started": info["started"].isoformat(),
                    "uptime": (datetime.now() - info["started"]).total_seconds(),
                    "log_file": info["log_file"],
                    "config": info["config"]
                }
                for name, info in self.running_agents.items()
            }
        }
    
    def get_agent_status(self, agent_type: str) -> Dict:
        """Get detailed status of a specific agent"""
        if agent_type not in self.running_agents:
            return {"status": "stopped"}
        
        agent_info = self.running_agents[agent_type]
        
        # Check if process is still alive
        try:
            process = psutil.Process(agent_info["pid"])
            return {
                "status": "running",
                "pid": agent_info["pid"],
                "started": agent_info["started"].isoformat(),
                "uptime": (datetime.now() - agent_info["started"]).total_seconds(),
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "log_file": agent_info["log_file"],
                "config": agent_info["config"]
            }
        except psutil.NoSuchProcess:
            # Process died, clean up
            del self.running_agents[agent_type]
            return {"status": "crashed"}
    
    def restart_agent(self, agent_type: str) -> Tuple[bool, str]:
        """Restart an agent"""
        # Stop if running
        if agent_type in self.running_agents:
            stop_success, stop_msg = self.stop_agent(agent_type)
            if not stop_success:
                return False, f"Failed to stop agent: {stop_msg}"
        
        # Wait a moment
        import time
        time.sleep(1)
        
        # Start again
        return self.deploy_agent(agent_type)
    
    def cleanup(self):
        """Clean up all running agents"""
        print("🛑 Stopping all agents...")
        for agent_type in list(self.running_agents.keys()):
            success, msg = self.stop_agent(agent_type)
            if success:
                print(f"   ✅ Stopped {agent_type}")
            else:
                print(f"   ❌ Failed to stop {agent_type}: {msg}")

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='SuperAgent Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy an agent')
    deploy_parser.add_argument('agent_type', choices=['grok4_agent', 'claude_agent', 'gemini_agent', 'o3_agent'])
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop an agent')
    stop_parser.add_argument('agent_type', choices=['grok4_agent', 'claude_agent', 'gemini_agent', 'o3_agent'])
    
    # Restart command
    restart_parser = subparsers.add_parser('restart', help='Restart an agent')
    restart_parser.add_argument('agent_type', choices=['grok4_agent', 'claude_agent', 'gemini_agent', 'o3_agent'])
    
    # List command
    subparsers.add_parser('list', help='List all agents')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Get agent status')
    status_parser.add_argument('agent_type', choices=['grok4_agent', 'claude_agent', 'gemini_agent', 'o3_agent'])
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Launch CLI dashboard')
    dashboard_parser.add_argument('--refresh', type=float, default=2.0, help='Refresh interval')
    
    # Interactive dashboard command
    interactive_parser = subparsers.add_parser('interactive', help='Launch interactive dashboard with real-time commands')
    interactive_parser.add_argument('--refresh', type=float, default=2.0, help='Refresh interval')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate agent configuration')
    validate_parser.add_argument('agent_type', choices=['grok4_agent', 'claude_agent', 'gemini_agent', 'o3_agent'])
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = SuperAgentManager()
    
    # Setup signal handler for cleanup
    def signal_handler(signum, frame):
        manager.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.command == 'deploy':
            success, msg = manager.deploy_agent(args.agent_type)
            if success:
                print(f"✅ {msg}")
                print(f"📋 Log file: logs/{args.agent_type}.log")
                print(f"🎯 Run 'python superagent_manager.py dashboard' to monitor")
            else:
                print(f"❌ {msg}")
                sys.exit(1)
        
        elif args.command == 'stop':
            success, msg = manager.stop_agent(args.agent_type)
            if success:
                print(f"✅ {msg}")
            else:
                print(f"❌ {msg}")
                sys.exit(1)
        
        elif args.command == 'restart':
            success, msg = manager.restart_agent(args.agent_type)
            if success:
                print(f"✅ {msg}")
            else:
                print(f"❌ {msg}")
                sys.exit(1)
        
        elif args.command == 'list':
            agents_info = manager.list_agents()
            print("🤖 SuperAgent Status")
            print("=" * 50)
            
            print("\n📋 Available Agents:")
            for agent_type, config in agents_info["available"].items():
                print(f"   • {agent_type}: {config['description']}")
            
            print(f"\n🟢 Running Agents ({len(agents_info['running'])}):")
            if agents_info["running"]:
                for agent_type, info in agents_info["running"].items():
                    uptime_min = info["uptime"] / 60
                    print(f"   • {agent_type}: PID {info['pid']}, uptime {uptime_min:.1f}m")
            else:
                print("   None")
        
        elif args.command == 'status':
            status = manager.get_agent_status(args.agent_type)
            print(f"🤖 {args.agent_type} Status:")
            
            if status["status"] == "running":
                uptime_min = status["uptime"] / 60
                print(f"   Status: 🟢 Running")
                print(f"   PID: {status['pid']}")
                print(f"   Uptime: {uptime_min:.1f} minutes")
                print(f"   CPU: {status['cpu_percent']:.1f}%")
                print(f"   Memory: {status['memory_percent']:.1f}%")
                print(f"   Log: {status['log_file']}")
            elif status["status"] == "crashed":
                print(f"   Status: 🔴 Crashed")
            else:
                print(f"   Status: ⚪ Stopped")
        
        elif args.command == 'validate':
            is_valid, msg = manager.validate_agent_config(args.agent_type)
            if is_valid:
                print(f"✅ {args.agent_type}: {msg}")
            else:
                print(f"❌ {args.agent_type}: {msg}")
                sys.exit(1)
        
        elif args.command == 'dashboard':
            print("🚀 Starting SuperAgent Dashboard...")
            print("   Press Ctrl+C to exit")
            dashboard = SuperAgentDashboard()
            asyncio.run(dashboard.run(args.refresh))
            
        elif args.command == 'interactive':
            print("🚀 Starting Interactive SuperAgent Dashboard...")
            print("   Type commands while dashboard runs, Press Ctrl+C to exit")
            from interactive_dashboard import InteractiveDashboard
            dashboard = InteractiveDashboard()
            asyncio.run(dashboard.run_interactive(args.refresh))
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        manager.cleanup()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()