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
import json

from dotenv import load_dotenv
# Dashboard import removed to avoid circular dependency

# Load environment variables
load_dotenv()

class SuperAgentManager:
    """Main SuperAgent management system"""
    
    def __init__(self):
        self.running_agents = {}
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Load agent and team configuration from agent_config.json
        self.config_file = Path(__file__).parent / "agent_config.json"
        self.load_config()
        
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
    
    def load_config(self):
        """Load teams and agent configuration from JSON file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                    self.teams_config = config_data.get('teams', {})
                    self.global_settings = config_data.get('global_settings', {})
            else:
                self.teams_config = {}
                self.global_settings = {}
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
            self.teams_config = {}
            self.global_settings = {}
    
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
    
    def _find_running_agent(self, agent_type: str) -> Optional[int]:
        """Find if an agent is already running by scanning processes"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and 'launch_single_agent.py' in ' '.join(cmdline) and agent_type in cmdline:
                        return proc.info['pid']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return None
        except ImportError:
            # Fallback to subprocess if psutil not available
            try:
                result = subprocess.run(['pgrep', '-f', f'launch_single_agent.py {agent_type}'], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    return int(result.stdout.strip().split('\n')[0])
            except:
                pass
            return None
    
    def deploy_agent(self, agent_type: str) -> Tuple[bool, str]:
        """Deploy a single agent"""
        # Validate configuration
        is_valid, msg = self.validate_agent_config(agent_type)
        if not is_valid:
            return False, msg
        
        # Check if agent is already running by scanning processes
        existing_pid = self._find_running_agent(agent_type)
        if existing_pid:
            return False, f"Agent {agent_type} is already running (PID: {existing_pid})"
        
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
        # Find the running process
        running_pid = self._find_running_agent(agent_type)
        if not running_pid:
            return False, f"Agent {agent_type} is not running"
        
        try:
            import psutil
            process = psutil.Process(running_pid)
            
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
        # Check if agent is actually running by scanning processes
        running_pid = self._find_running_agent(agent_type)
        if not running_pid:
            return {"status": "stopped"}
        
        # Get process info
        try:
            import psutil
            proc = psutil.Process(running_pid)
            create_time = datetime.fromtimestamp(proc.create_time())
            return {
                "status": "running",
                "pid": running_pid,
                "started": create_time.isoformat(),
                "uptime": (datetime.now() - create_time).total_seconds(),
                "memory_mb": round(proc.memory_info().rss / 1024 / 1024, 1),
                "cpu_percent": proc.cpu_percent()
            }
        except:
            return {
                "status": "running",
                "pid": running_pid,
                "started": "unknown",
                "uptime": 0
            }
    
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
    
    def list_teams(self) -> Dict:
        """List all available teams and their status"""
        teams_status = {}
        
        for team_id, team_config in self.teams_config.items():
            # Check which agents in the team are running
            running_agents = []
            stopped_agents = []
            
            for agent_type in team_config.get('agents', []):
                if self._find_running_agent(agent_type):
                    running_agents.append(agent_type)
                else:
                    stopped_agents.append(agent_type)
            
            teams_status[team_id] = {
                "name": team_config.get("name", team_id),
                "description": team_config.get("description", ""),
                "agents": team_config.get("agents", []),
                "running_agents": running_agents,
                "stopped_agents": stopped_agents,
                "status": "fully_running" if len(stopped_agents) == 0 else "partially_running" if len(running_agents) > 0 else "stopped",
                "server_id": team_config.get("default_server_id"),
                "gm_channel": team_config.get("gm_channel"),
                "auto_deploy": team_config.get("auto_deploy", False),
                "coordination_mode": team_config.get("coordination_mode", "parallel")
            }
        
        return teams_status
    
    def deploy_team(self, team_id: str) -> Tuple[bool, str]:
        """Deploy all agents in a team"""
        if team_id not in self.teams_config:
            return False, f"Unknown team: {team_id}"
        
        team_config = self.teams_config[team_id]
        agents = team_config.get("agents", [])
        
        if not agents:
            return False, f"Team {team_id} has no agents configured"
        
        results = []
        success_count = 0
        
        for agent_type in agents:
            success, msg = self.deploy_agent(agent_type)
            results.append(f"   • {agent_type}: {msg}")
            if success:
                success_count += 1
        
        team_name = team_config.get("name", team_id)
        if success_count == len(agents):
            return True, f"Successfully deployed team '{team_name}' ({success_count}/{len(agents)} agents):\n" + "\n".join(results)
        elif success_count > 0:
            return True, f"Partially deployed team '{team_name}' ({success_count}/{len(agents)} agents):\n" + "\n".join(results)
        else:
            return False, f"Failed to deploy team '{team_name}' (0/{len(agents)} agents):\n" + "\n".join(results)
    
    def stop_team(self, team_id: str) -> Tuple[bool, str]:
        """Stop all agents in a team"""
        if team_id not in self.teams_config:
            return False, f"Unknown team: {team_id}"
        
        team_config = self.teams_config[team_id]
        agents = team_config.get("agents", [])
        
        if not agents:
            return False, f"Team {team_id} has no agents configured"
        
        results = []
        success_count = 0
        
        for agent_type in agents:
            success, msg = self.stop_agent(agent_type)
            results.append(f"   • {agent_type}: {msg}")
            if success:
                success_count += 1
        
        team_name = team_config.get("name", team_id)
        if success_count == len(agents):
            return True, f"Successfully stopped team '{team_name}' ({success_count}/{len(agents)} agents):\n" + "\n".join(results)
        else:
            return True, f"Partially stopped team '{team_name}' ({success_count}/{len(agents)} agents):\n" + "\n".join(results)
    
    def show_agent_configs(self, agent_type: str = None, verbose: bool = False) -> str:
        """Show agent configurations in a compact, readable format"""
        if agent_type:
            # Show specific agent
            if agent_type not in self.agent_configs:
                return f"❌ Unknown agent: {agent_type}"
            
            config = self.agent_configs[agent_type]
            return self._format_agent_config(agent_type, config, verbose)
        else:
            # Show all agents
            output = ["🤖 Agent Configurations", "=" * 50]
            
            for agent_id, config in self.agent_configs.items():
                output.append("")
                output.append(self._format_agent_config(agent_id, config, verbose))
            
            return "\n".join(output)
    
    def _format_agent_config(self, agent_id: str, config: Dict, verbose: bool = False) -> str:
        """Format a single agent config"""
        # Get environment values
        token = os.getenv(config["token_env"], "❌ NOT SET")
        api_key = os.getenv(config["api_key_env"], "❌ NOT SET")
        server_id = os.getenv("DEFAULT_SERVER_ID", "❌ NOT SET")
        
        # Truncate tokens for security/readability
        token_display = f"✅ {token[:8]}..." if token != "❌ NOT SET" else token
        api_key_display = f"✅ {api_key[:8]}..." if api_key != "❌ NOT SET" else api_key
        
        # Check if running
        running_pid = self._find_running_agent(agent_id)
        status = f"🟢 Running (PID: {running_pid})" if running_pid else "⚪ Stopped"
        
        # LLM type icons
        llm_icons = {
            "grok4": "🧠",
            "claude": "🤖", 
            "gemini": "💎",
            "openai": "⚡"
        }
        llm_icon = llm_icons.get(config["llm_type"], "🔧")
        
        output = [
            f"{llm_icon} {config['name']} ({agent_id}) - {status}",
            f"   LLM: {config['llm_type'].upper()} | {config['description']}"
        ]
        
        if verbose:
            output.extend([
                f"   Discord Token ({config['token_env']}): {token_display}",
                f"   API Key ({config['api_key_env']}): {api_key_display}",
                f"   Server ID: {server_id}"
            ])
        else:
            # Compact status indicators
            token_status = "🟢" if token != "❌ NOT SET" else "❌"
            api_status = "🟢" if api_key != "❌ NOT SET" else "❌"
            server_status = "🟢" if server_id != "❌ NOT SET" else "❌"
            
            output.append(f"   Config: Token {token_status} | API {api_status} | Server {server_status}")
        
        return "\n".join(output)
    
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
    
    # Team commands
    teams_parser = subparsers.add_parser('teams', help='Team management commands')
    team_subparsers = teams_parser.add_subparsers(dest='team_command', help='Team commands')
    
    # List teams
    team_subparsers.add_parser('list', help='List all teams and their status')
    
    # Deploy team
    deploy_team_parser = team_subparsers.add_parser('deploy', help='Deploy a team')
    deploy_team_parser.add_argument('team_id', help='Team ID to deploy')
    
    # Stop team
    stop_team_parser = team_subparsers.add_parser('stop', help='Stop a team')
    stop_team_parser.add_argument('team_id', help='Team ID to stop')
    
    # Team status
    team_status_parser = team_subparsers.add_parser('status', help='Get team status')
    team_status_parser.add_argument('team_id', help='Team ID to check')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Show agent configurations')
    config_parser.add_argument('--agent', help='Show specific agent config')
    config_parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed config')
    
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
        
        elif args.command == 'teams':
            if not args.team_command:
                teams_parser.print_help()
                return
            
            if args.team_command == 'list':
                teams_status = manager.list_teams()
                print("🏢 SuperAgent Teams Status")
                print("=" * 60)
                
                if not teams_status:
                    print("No teams configured")
                    return
                
                for team_id, info in teams_status.items():
                    status_icon = "🟢" if info["status"] == "fully_running" else "🟡" if info["status"] == "partially_running" else "⚪"
                    print(f"\n{status_icon} {info['name']} ({team_id})")
                    print(f"   Description: {info['description']}")
                    print(f"   Status: {info['status']}")
                    print(f"   Agents: {', '.join(info['agents'])}")
                    if info['running_agents']:
                        print(f"   Running: {', '.join(info['running_agents'])}")
                    if info['stopped_agents']:
                        print(f"   Stopped: {', '.join(info['stopped_agents'])}")
                    print(f"   Server: {info['server_id']}")
                    print(f"   GM Channel: {info['gm_channel']}")
                    print(f"   Auto-deploy: {'Yes' if info['auto_deploy'] else 'No'}")
                    print(f"   Coordination: {info['coordination_mode']}")
            
            elif args.team_command == 'deploy':
                success, msg = manager.deploy_team(args.team_id)
                if success:
                    print(f"✅ {msg}")
                else:
                    print(f"❌ {msg}")
                    sys.exit(1)
            
            elif args.team_command == 'stop':
                success, msg = manager.stop_team(args.team_id)
                if success:
                    print(f"✅ {msg}")
                else:
                    print(f"❌ {msg}")
                    sys.exit(1)
            
            elif args.team_command == 'status':
                teams_status = manager.list_teams()
                if args.team_id not in teams_status:
                    print(f"❌ Unknown team: {args.team_id}")
                    sys.exit(1)
                
                info = teams_status[args.team_id]
                status_icon = "🟢" if info["status"] == "fully_running" else "🟡" if info["status"] == "partially_running" else "⚪"
                print(f"{status_icon} Team: {info['name']} ({args.team_id})")
                print(f"   Status: {info['status']}")
                print(f"   Running agents ({len(info['running_agents'])}): {', '.join(info['running_agents']) if info['running_agents'] else 'None'}")
                print(f"   Stopped agents ({len(info['stopped_agents'])}): {', '.join(info['stopped_agents']) if info['stopped_agents'] else 'None'}")
                print(f"   Server: {info['server_id']}")
                print(f"   GM Channel: {info['gm_channel']}")
                print(f"   Coordination: {info['coordination_mode']}")
        
        elif args.command == 'config':
            result = manager.show_agent_configs(args.agent, args.verbose)
            print(result)
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        manager.cleanup()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()