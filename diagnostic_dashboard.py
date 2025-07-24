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
                            "status": "running"
                        }
                    
                    elif 'mcp_devops_agent.py' in cmdline:
                        discord_name = self.get_discord_bot_name("devops_agent")
                        agents["devops_agent"] = {
                            "pid": proc.info['pid'],
                            "discord_name": discord_name,
                            "uptime": time.time() - proc.info['create_time'],
                            "status": "running"
                        }
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, IndexError):
                    continue
        except Exception:
            pass
        return agents
    
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
        table = Table(show_header=True, box=ROUNDED)
        table.add_column("Discord Bot", style="cyan", width=20)
        table.add_column("Agent ID", style="blue", width=15)
        table.add_column("Status", style="green", width=12)
        table.add_column("Token Env Var", style="yellow", width=20)
        table.add_column("Token Status", style="magenta", width=12)
        table.add_column("Running", style="white", width=10)
        
        tokens = self.check_discord_tokens()
        running_agents = self.get_agent_processes()
        
        for token_key, token_info in tokens.items():
            agent_id = token_info["agent"]
            is_running = agent_id in running_agents
            
            # Get actual Discord name if running
            if is_running:
                actual_name = running_agents[agent_id].get("discord_name", "Unknown")
                bot_display = f"{token_info['bot_name']}\n({actual_name})"
            else:
                bot_display = token_info["bot_name"]
            
            running_status = "🟢 Online" if is_running else "🔴 Offline"
            
            table.add_row(
                bot_display,
                agent_id,
                token_info["status"],
                token_info["env_var"],
                f"{token_info['length']} chars" if token_info["length"] > 0 else "❌ Missing",
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
        table = Table(show_header=True, box=ROUNDED)
        table.add_column("LLM Provider", style="green", width=20)
        table.add_column("Used By", style="blue", width=15)
        table.add_column("API Key Env", style="yellow", width=20)
        table.add_column("Status", style="magenta", width=12)
        table.add_column("Key Preview", style="dim", width=30)
        
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
        table = Table(show_header=True, box=ROUNDED)
        table.add_column("Agent", style="cyan", width=15)
        table.add_column("Discord Bot", style="blue", width=20)
        table.add_column("LLM", style="green", width=10)
        table.add_column("Team", style="magenta", width=15)
        table.add_column("Status", style="yellow", width=12)
        table.add_column("Uptime", style="white", width=10)
        
        running_agents = self.get_agent_processes()
        configs = self.agent_config_data.get("agents", {})
        teams = self.agent_config_data.get("teams", {})
        
        # Find team membership
        agent_teams = {}
        for team_name, team_config in teams.items():
            for agent_id in team_config.get("agents", []):
                agent_teams[agent_id] = team_name
        
        # Show all configured agents
        for agent_id, config in configs.items():
            is_running = agent_id in running_agents
            
            if is_running:
                discord_name = running_agents[agent_id].get("discord_name", "Unknown")
                status = "🟢 Running"
                uptime = f"{running_agents[agent_id]['uptime']/60:.1f}m"
            else:
                discord_name = "N/A"
                status = "🔴 Offline"
                uptime = "N/A"
            
            table.add_row(
                agent_id,
                discord_name,
                config.get("llm_type", "unknown"),
                agent_teams.get(agent_id, "None"),
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
    
    def create_layout(self) -> Layout:
        """Create the dashboard layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="discord", size=10),
            Layout(name="api", size=8),
            Layout(name="status", size=10),
            Layout(name="errors", size=12)
        )
        
        layout["discord"].update(self.create_discord_bots_panel())
        layout["api"].update(self.create_llm_api_panel())
        layout["status"].update(self.create_agent_status_panel())
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
                    layout["errors"].update(self.create_error_diagnostics_panel())
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Dashboard stopped[/yellow]")

def main():
    dashboard = DiagnosticDashboard()
    asyncio.run(dashboard.run())

if __name__ == "__main__":
    main()