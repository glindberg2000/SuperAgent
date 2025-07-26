#!/usr/bin/env python3
"""
SuperAgent Diagnostic Dashboard
Clear separation of Discord Bot configuration and LLM API configuration
"""

import asyncio
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import psutil
import docker
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.box import ROUNDED, DOUBLE
from dotenv import load_dotenv

load_dotenv()

class DiagnosticDashboard:
    """Diagnostic dashboard with clear separation of concerns"""
    
    def __init__(self):
        self.console = Console()
        self.logs_dir = Path("logs")
        self.config_file = Path("agent_config.json")
        self.agent_config_data = self._load_config_data()
        self.docker_client = self._init_docker_client()
        
    def _init_docker_client(self):
        """Initialize Docker client with fallback options"""
        try:
            return docker.from_env()
        except Exception:
            return None
        
    def _load_config_data(self) -> Dict:
        """Load agent configuration data"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
        return {"agents": {}, "teams": {}}
    
    def get_discord_bot_name(self, agent_type: str) -> str:
        """Extract Discord bot name from agent logs"""
        log_files = {
            "grok4_agent": ["grok4_restart.log", "grok4_fixed.log", "grok4_single_new.log"],
            "claude_agent": ["claude_fixed_restart.log", "claude_restart.log", "claude_fixed.log"],
            "gemini_agent": ["gemini_single.log"],
            "devops_agent": ["mcp_devops_agent.log"],
            "o3_agent": ["o3_single.log"]
        }
        
        for log_file in log_files.get(agent_type, []):
            log_path = self.logs_dir / log_file
            if log_path.exists():
                try:
                    with open(log_path, 'r') as f:
                        content = f.read()
                        import re
                        matches = re.findall(r'Logged in as (.+)', content)
                        if matches:
                            return matches[-1].strip()
                except Exception:
                    continue
        return "Not Found"
    
    def get_agent_processes(self) -> Dict[str, Dict]:
        """Get running agent processes"""
        agents = {}
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    cmdline_list = proc.info.get('cmdline', [])
                    if not cmdline_list:
                        continue
                    
                    cmdline = ' '.join(cmdline_list)
                    
                    if 'launch_single_agent.py' in cmdline:
                        parts = cmdline.split()
                        agent_type = parts[-1] if len(parts) > 0 and parts[-1] in ['grok4_agent', 'claude_agent', 'gemini_agent', 'o3_agent'] else 'unknown'
                        
                        discord_name = self.get_discord_bot_name(agent_type)
                        
                        agents[agent_type] = {
                            "pid": proc.info['pid'],
                            "discord_name": discord_name,
                            "uptime": time.time() - proc.info['create_time'],
                            "status": "running",
                            "type": "process"
                        }
                    
                    elif 'mcp_devops_agent.py' in cmdline:
                        discord_name = self.get_discord_bot_name("devops_agent")
                        agents["devops_agent"] = {
                            "pid": proc.info['pid'],
                            "discord_name": discord_name,
                            "uptime": time.time() - proc.info['create_time'],
                            "status": "running",
                            "type": "process"
                        }
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, IndexError):
                    continue
        except Exception:
            pass
        return agents
    
    def get_container_agents(self) -> Dict[str, Dict]:
        """Get running container agents"""
        containers = {}
        if not self.docker_client:
            return containers
            
        try:
            for container in self.docker_client.containers.list(all=True):
                name = container.name
                labels = container.labels or {}
                
                # Check for Claude Code containers
                if ('claude-code' in container.image.tags[0] if container.image.tags else False) or \
                   labels.get('superagent.type') == 'claude-code':
                    
                    containers[f"container_{name}"] = {
                        "container_id": container.id[:12],
                        "discord_name": labels.get('superagent.discord_name', name),
                        "uptime": time.time() - container.attrs['Created'].timestamp() if container.status == 'running' else 0,
                        "status": container.status,
                        "type": "container",
                        "image": container.image.tags[0] if container.image.tags else 'unknown'
                    }
        except Exception:
            pass
        return containers
    
    def check_postgres_container(self) -> Dict[str, str]:
        """Check PostgreSQL container status"""
        if not self.docker_client:
            return {"status": "❌ Docker not available", "details": "Cannot connect to Docker"}
            
        try:
            # Look for superagent-postgres container
            containers = self.docker_client.containers.list(all=True, filters={"name": "superagent-postgres"})
            if containers:
                container = containers[0]
                if container.status == 'running':
                    ports = container.attrs['NetworkSettings']['Ports']
                    port_info = ""
                    if '5432/tcp' in ports and ports['5432/tcp']:
                        port_info = f" (port {ports['5432/tcp'][0]['HostPort']})"
                    return {
                        "status": "🟢 Running",
                        "details": f"Container: {container.name}{port_info}"
                    }
                else:
                    return {
                        "status": "🔴 Stopped", 
                        "details": f"Container: {container.name} ({container.status})"
                    }
            else:
                return {"status": "❌ Not Found", "details": "superagent-postgres container not found"}
        except Exception as e:
            return {"status": "❌ Error", "details": f"Docker error: {str(e)[:50]}..."}
    
    def check_api_keys(self) -> Dict[str, Dict]:
        """Check all API keys and their validity"""
        api_keys = {
            "XAI_API_KEY": {
                "name": "Grok4 (xAI)",
                "env_var": "XAI_API_KEY",
                "value": os.getenv("XAI_API_KEY", ""),
                "used_by": ["grok4_agent"]
            },
            "ANTHROPIC_API_KEY": {
                "name": "Claude (Anthropic)",
                "env_var": "ANTHROPIC_API_KEY", 
                "value": os.getenv("ANTHROPIC_API_KEY", ""),
                "used_by": ["claude_agent"]
            },
            "GEMINI_API_KEY": {
                "name": "Gemini (Google)",
                "env_var": "GEMINI_API_KEY",
                "value": os.getenv("GEMINI_API_KEY", ""),
                "used_by": ["gemini_agent"]
            },
            "OPENAI_API_KEY": {
                "name": "OpenAI",
                "env_var": "OPENAI_API_KEY",
                "value": os.getenv("OPENAI_API_KEY", ""),
                "used_by": ["o3_agent"]
            }
        }
        
        for key, info in api_keys.items():
            if info["value"]:
                info["status"] = "✅ Present"
                info["preview"] = f"{info['value'][:20]}...{info['value'][-4:]}"
                info["length"] = len(info["value"])
            else:
                info["status"] = "❌ Missing"
                info["preview"] = "Not Set"
                info["length"] = 0
                
        return api_keys
    
    def check_discord_tokens(self) -> Dict[str, Dict]:
        """Check all Discord bot tokens"""
        tokens = {
            "DISCORD_TOKEN_GROK4": {
                "bot_name": "Grok4",
                "env_var": "DISCORD_TOKEN_GROK4",
                "value": os.getenv("DISCORD_TOKEN_GROK4", ""),
                "agent": "grok4_agent"
            },
            "DISCORD_TOKEN_CLAUDE": {
                "bot_name": "CryptoTax_CoderDev1", 
                "env_var": "DISCORD_TOKEN_CLAUDE",
                "value": os.getenv("DISCORD_TOKEN_CLAUDE", ""),
                "agent": "claude_agent"
            },
            "DISCORD_TOKEN_GEMINI": {
                "bot_name": "Gemini Bot",
                "env_var": "DISCORD_TOKEN_GEMINI",
                "value": os.getenv("DISCORD_TOKEN_GEMINI", ""),
                "agent": "gemini_agent"
            },
            "DISCORD_TOKEN_OPENAI": {
                "bot_name": "OpenAI Bot",
                "env_var": "DISCORD_TOKEN_OPENAI",
                "value": os.getenv("DISCORD_TOKEN_OPENAI", ""),
                "agent": "o3_agent"
            },
            "DISCORD_TOKEN_DEVOPS": {
                "bot_name": "DevOps",
                "env_var": "DISCORD_TOKEN_DEVOPS",
                "value": os.getenv("DISCORD_TOKEN_DEVOPS", ""),
                "agent": "devops_agent"
            }
        }
        
        for key, info in tokens.items():
            if info["value"] and info["value"] != "DISCORD_TOKEN_OPENAI_NOT_SET":
                info["status"] = "✅ Set"
                info["preview"] = f"{info['value'][:25]}...{info['value'][-10:]}"
                info["length"] = len(info["value"])
            else:
                info["status"] = "❌ Not Set"
                info["preview"] = "Missing"
                info["length"] = 0
                
        return tokens
    
    def get_recent_errors(self, agent_type: str, lines: int = 5) -> List[str]:
        """Get recent error lines from agent logs"""
        log_files = {
            "grok4_agent": ["grok4_restart.log", "grok4_fixed.log"],
            "claude_agent": ["claude_fixed_restart.log", "claude_restart.log"],
            "gemini_agent": ["gemini_single.log"],
            "devops_agent": ["mcp_devops_agent.log"]
        }
        
        errors = []
        for log_file in log_files.get(agent_type, []):
            log_path = self.logs_dir / log_file
            if log_path.exists():
                try:
                    with open(log_path, 'r') as f:
                        content = f.read()
                        # Look for errors
                        import re
                        error_lines = re.findall(r'.*(?:ERROR|error|401|403|authentication).*', content)
                        errors.extend(error_lines[-lines:])
                except Exception:
                    continue
        return errors[-lines:] if errors else ["No recent errors found"]
    
    def create_discord_bots_panel(self) -> Panel:
        """Create Discord Bots configuration panel"""
        # Use expand=True to use full available width
        table = Table(show_header=True, box=ROUNDED, expand=True)
        table.add_column("Discord Bot", style="cyan", min_width=25, ratio=3)
        table.add_column("Agent ID", style="blue", min_width=15, ratio=2)
        table.add_column("Token Status", style="green", min_width=12, ratio=2)
        table.add_column("Token Env Var", style="yellow", min_width=22, ratio=3)
        table.add_column("Type", style="magenta", min_width=10, ratio=1)
        table.add_column("Running", style="white", min_width=12, ratio=2)
        
        tokens = self.check_discord_tokens()
        running_agents = self.get_agent_processes()
        container_agents = self.get_container_agents()
        
        for token_key, token_info in tokens.items():
            agent_id = token_info["agent"]
            is_running_process = agent_id in running_agents
            is_running_container = any(agent_id in key for key in container_agents.keys())
            is_running = is_running_process or is_running_container
            
            # Get actual Discord name if running
            if is_running_process:
                actual_name = running_agents[agent_id].get("discord_name", "Unknown")
                agent_type = "📱 Process"
            elif is_running_container:
                container_key = next((k for k in container_agents.keys() if agent_id in k), None)
                actual_name = container_agents[container_key].get("discord_name", "Unknown") if container_key else "Unknown"
                agent_type = "🐳 Container" 
            else:
                actual_name = "N/A"
                agent_type = "💤 Offline"
            
            bot_display = f"{token_info['bot_name']}\n[dim]({actual_name})[/dim]" if actual_name != "N/A" else token_info['bot_name']
            running_status = "🟢 Online" if is_running else "🔴 Offline"
            
            table.add_row(
                bot_display,
                agent_id,
                token_info["status"],
                token_info["env_var"],
                agent_type,
                running_status
            )
        
        return Panel(
            table,
            title="[bold cyan]🤖 Discord Bot Configuration[/bold cyan]",
            border_style="cyan",
            box=DOUBLE
        )
    
    def create_llm_api_panel(self) -> Panel:
        """Create LLM API configuration panel"""
        table = Table(show_header=True, box=ROUNDED, expand=True)
        table.add_column("LLM Provider", style="green", min_width=20, ratio=3)
        table.add_column("Used By", style="blue", min_width=15, ratio=2)
        table.add_column("API Key Env", style="yellow", min_width=22, ratio=3)
        table.add_column("Status", style="magenta", min_width=12, ratio=2)
        table.add_column("Key Preview", style="dim", min_width=35, ratio=4)
        
        api_keys = self.check_api_keys()
        
        for key, info in api_keys.items():
            table.add_row(
                info["name"],
                ", ".join(info["used_by"]),
                info["env_var"],
                info["status"],
                info["preview"]
            )
        
        return Panel(
            table,
            title="[bold green]🔑 LLM API Configuration[/bold green]",
            border_style="green",
            box=DOUBLE
        )
    
    def create_agent_status_panel(self) -> Panel:
        """Create detailed agent status panel"""
        table = Table(show_header=True, box=ROUNDED, expand=True)
        table.add_column("Agent", style="cyan", min_width=15, ratio=2)
        table.add_column("Discord Bot", style="blue", min_width=25, ratio=3)
        table.add_column("LLM", style="green", min_width=10, ratio=1)
        table.add_column("Type", style="yellow", min_width=12, ratio=2)
        table.add_column("Team", style="magenta", min_width=15, ratio=2)
        table.add_column("Status", style="white", min_width=12, ratio=2)
        table.add_column("Uptime", style="dim", min_width=10, ratio=1)
        
        running_agents = self.get_agent_processes()
        container_agents = self.get_container_agents()
        configs = self.agent_config_data.get("agents", {})
        teams = self.agent_config_data.get("teams", {})
        
        # Find team membership
        agent_teams = {}
        for team_name, team_config in teams.items():
            for agent_id in team_config.get("agents", []):
                agent_teams[agent_id] = team_name
        
        # Show all configured agents (processes)
        for agent_id, config in configs.items():
            is_running = agent_id in running_agents
            
            if is_running:
                discord_name = running_agents[agent_id].get("discord_name", "Unknown")
                status = "🟢 Running"
                uptime = f"{running_agents[agent_id]['uptime']/60:.1f}m"
                agent_type = "📱 Process"
            else:
                discord_name = "N/A"
                status = "🔴 Offline"
                uptime = "N/A"
                agent_type = "💤 Offline"
            
            table.add_row(
                agent_id,
                discord_name,
                config.get("llm_type", "unknown"),
                agent_type,
                agent_teams.get(agent_id, "None"),
                status,
                uptime
            )
        
        # Show container agents
        for container_key, container_info in container_agents.items():
            agent_name = container_key.replace('container_', '')
            status = "🟢 Running" if container_info['status'] == 'running' else f"🔴 {container_info['status']}"
            uptime = f"{container_info['uptime']/60:.1f}m" if container_info['uptime'] > 0 else "N/A"
            
            table.add_row(
                agent_name,
                container_info.get('discord_name', 'Unknown'),
                "claude-code",
                "🐳 Container",
                "None",
                status,
                uptime
            )
        
        return Panel(
            table,
            title="[bold magenta]📊 Agent Status Overview[/bold magenta]",
            border_style="magenta",
            box=DOUBLE
        )
    
    def create_error_diagnostics_panel(self) -> Panel:
        """Create error diagnostics panel"""
        content = []
        
        # Check for Claude API errors specifically
        claude_errors = self.get_recent_errors("claude_agent", 3)
        if any("401" in err or "authentication" in err for err in claude_errors):
            content.append("[bold red]⚠️  Claude Agent API Authentication Error Detected![/bold red]")
            content.append("Recent errors:")
            for err in claude_errors[-3:]:
                if "401" in err or "authentication" in err:
                    content.append(f"  [red]{err[:120]}...[/red]")
            content.append("")
            content.append("[yellow]Troubleshooting:[/yellow]")
            content.append("1. Check if ANTHROPIC_API_KEY is valid")
            content.append("2. Ensure the API key has proper permissions")
            content.append("3. Try regenerating the API key from Anthropic console")
            content.append("")
        
        # Check for other critical errors
        for agent in ["grok4_agent", "gemini_agent", "devops_agent"]:
            errors = self.get_recent_errors(agent, 2)
            if any("ERROR" in err or "error" in err for err in errors):
                content.append(f"[yellow]{agent} errors:[/yellow]")
                for err in errors:
                    content.append(f"  {err[:100]}...")
                content.append("")
        
        if not content:
            content.append("[green]✅ No critical errors detected[/green]")
        
        return Panel(
            "\n".join(content),
            title="[bold red]🚨 Error Diagnostics[/bold red]",
            border_style="red",
            box=DOUBLE
        )
    
    def create_infrastructure_panel(self) -> Panel:
        """Create infrastructure services panel"""
        table = Table(show_header=True, box=ROUNDED, expand=True)
        table.add_column("Service", style="cyan", min_width=20, ratio=2)
        table.add_column("Type", style="blue", min_width=15, ratio=2)
        table.add_column("Status", style="green", min_width=15, ratio=2)
        table.add_column("Details", style="yellow", min_width=40, ratio=4)
        
        # PostgreSQL Container
        postgres_info = self.check_postgres_container()
        table.add_row(
            "PostgreSQL",
            "🐳 Container",
            postgres_info["status"],
            postgres_info["details"]
        )
        
        return Panel(
            table,
            title="[bold blue]🏗️ Infrastructure Services[/bold blue]",
            border_style="blue",
            box=DOUBLE
        )
    
    def create_layout(self) -> Layout:
        """Create the dashboard layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="discord", size=10),
            Layout(name="api", size=8),
            Layout(name="status", size=12),
            Layout(name="infrastructure", size=6),
            Layout(name="errors", size=10)
        )
        
        layout["discord"].update(self.create_discord_bots_panel())
        layout["api"].update(self.create_llm_api_panel())
        layout["status"].update(self.create_agent_status_panel())
        layout["infrastructure"].update(self.create_infrastructure_panel())
        layout["errors"].update(self.create_error_diagnostics_panel())
        
        return layout
    
    async def run(self):
        """Run the diagnostic dashboard"""
        layout = self.create_layout()
        
        with Live(layout, console=self.console, refresh_per_second=0.5) as live:
            try:
                while True:
                    await asyncio.sleep(2)
                    layout["discord"].update(self.create_discord_bots_panel())
                    layout["api"].update(self.create_llm_api_panel())
                    layout["status"].update(self.create_agent_status_panel())
                    layout["infrastructure"].update(self.create_infrastructure_panel())
                    layout["errors"].update(self.create_error_diagnostics_panel())
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Dashboard stopped[/yellow]")

def main():
    dashboard = DiagnosticDashboard()
    asyncio.run(dashboard.run())

if __name__ == "__main__":
    main()