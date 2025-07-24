#!/usr/bin/env python3
"""
SuperAgent Dashboard with Detail Views
Enhanced version with keyboard shortcuts to show full details
"""

import asyncio
import os
import json
import time
import sys
import threading
import queue
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich.align import Align
    from rich.box import ROUNDED, DOUBLE
    import psutil
    import docker
    import psycopg2
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("pip install rich psutil docker psycopg2-binary")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

class DetailDashboard:
    """Dashboard with keyboard shortcuts for detailed views"""
    
    def __init__(self):
        self.console = Console()
        self.detail_mode = None  # None, 'agents', 'teams', 'configs', 'system', 'postgres', 'logs'
        self.input_queue = queue.Queue()
        self.postgres_url = os.getenv('POSTGRES_URL', 'postgresql://superagent:superagent@localhost:5433/superagent')
        
        # Load config data
        self.config_file = Path("agent_config.json")
        self.agent_config_data = self._load_config_data()
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception:
            self.docker_client = None
    
    def _load_config_data(self) -> Dict:
        """Load agent configuration data"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {"agents": {}, "teams": {}}
    
    def get_system_status(self) -> Dict:
        """Get system resource status"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "load_avg": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0,
            "boot_time": psutil.boot_time()
        }
    
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
                        
                        agents[agent_type] = {
                            "pid": proc.info['pid'],
                            "type": "single_agent",
                            "agent": agent_type,
                            "uptime": time.time() - proc.info['create_time'],
                            "cpu": proc.cpu_percent() or 0,
                            "memory": proc.memory_percent() or 0,
                            "status": "running"
                        }
                except Exception:
                    continue
        except Exception:
            pass
        return agents
    
    def create_header(self) -> Panel:
        """Create dashboard header"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        header_text = Text()
        header_text.append("🤖 SuperAgent Dashboard", style="bold blue")
        header_text.append(" | ", style="dim")
        header_text.append(f"Updated: {current_time}", style="dim")
        
        if self.detail_mode:
            header_text.append(" | ", style="dim")
            header_text.append(f"Detail: {self.detail_mode.title()}", style="bold yellow")
            header_text.append(" | ", style="dim")
            header_text.append("0=Back", style="cyan")
        else:
            header_text.append(" | ", style="dim")
            header_text.append("1=Agents 2=Teams 3=Configs 4=System 5=Postgres 6=Logs 0=Back Q=Quit", style="cyan")
        
        return Panel(
            Align.center(header_text),
            style="bold white on blue",
            box=ROUNDED
        )
    
    def create_agents_detail(self) -> Panel:
        """Create detailed agents view"""
        agents = self.get_agent_processes()
        
        if not agents:
            content = Text()
            content.append("❌ No agents currently running\n\n", style="bold red")
            content.append("Available agent types:\n", style="bold")
            content.append("  • grok4_agent (XAI Grok-2)\n", style="green")
            content.append("  • claude_agent (Anthropic Claude)\n", style="green")
            content.append("  • gemini_agent (Google Gemini)\n", style="green")
            content.append("  • o3_agent (OpenAI o3)\n\n", style="green")
            content.append("To start agents:\n", style="bold")
            content.append("  python superagent_manager.py deploy <agent_type>", style="cyan")
        else:
            table = Table(show_header=True, box=ROUNDED)
            table.add_column("Agent", style="cyan")
            table.add_column("PID", style="white")
            table.add_column("Uptime", style="yellow")
            table.add_column("CPU%", style="red")
            table.add_column("Memory%", style="magenta")
            table.add_column("Status", style="green")
            table.add_column("Command", style="dim")
            
            for name, info in agents.items():
                uptime_str = f"{info['uptime']/60:.1f}m" if info['uptime'] < 3600 else f"{info['uptime']/3600:.1f}h"
                # Get process command line
                try:
                    proc = psutil.Process(info['pid'])
                    cmdline = ' '.join(proc.cmdline())  # Full command line
                except:
                    cmdline = "N/A"
                
                table.add_row(
                    name.replace("_", " ").title(),
                    str(info["pid"]),
                    uptime_str,
                    f"{info['cpu']:.1f}%",
                    f"{info['memory']:.1f}%",
                    "🟢 Running",
                    cmdline  # Show full command line
                )
            
            content = table
        
        return Panel(
            content,
            title="[bold green]🤖 Detailed Agent Information[/bold green]",
            border_style="green",
            box=DOUBLE
        )
    
    def create_teams_detail(self) -> Panel:
        """Create detailed teams view"""
        teams = self.agent_config_data.get('teams', {})
        
        if not teams:
            content = Text()
            content.append("❌ No teams configured\n\n", style="bold red")
            content.append("Teams allow grouping agents with:\n", style="bold")
            content.append("  • Shared server ID\n", style="green")
            content.append("  • Default GM channel\n", style="green") 
            content.append("  • Auto-deploy settings\n", style="green")
            content.append("  • Coordination modes\n\n", style="green")
            content.append("Configure in agent_config.json", style="cyan")
        else:
            table = Table(show_header=True, box=ROUNDED)
            table.add_column("Team", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Agents", style="green")
            table.add_column("Server ID", style="blue")
            table.add_column("GM Channel", style="magenta")
            table.add_column("Auto Deploy", style="yellow")
            
            for team_name, team_info in teams.items():
                agents = ", ".join(team_info.get('agents', []))
                
                table.add_row(
                    team_name,
                    team_info.get('description', 'N/A'),  # Show full description
                    agents,  # Show all agents
                    team_info.get('default_server_id', 'N/A'),
                    team_info.get('gm_channel', 'N/A'),
                    "✅ Yes" if team_info.get('auto_deploy') else "❌ No"
                )
            
            content = table
        
        return Panel(
            content,
            title="[bold cyan]👥 Detailed Team Configuration[/bold cyan]",
            border_style="cyan",
            box=DOUBLE
        )
    
    def create_configs_detail(self) -> Panel:
        """Create detailed configs view"""
        configs = self.agent_config_data.get('agents', {})
        
        if not configs:
            content = Text()
            content.append("❌ No agent configs found\n\n", style="bold red")
            content.append("Expected file: agent_config.json\n", style="yellow")
            content.append("Please check configuration file", style="cyan")
        else:
            table = Table(show_header=True, box=ROUNDED)
            table.add_column("Agent", style="cyan")
            table.add_column("LLM Type", style="green")
            table.add_column("API Key", style="yellow")
            table.add_column("Max Context", style="blue")
            table.add_column("Max Turns", style="magenta")
            table.add_column("Response Delay", style="red")
            table.add_column("Ignore Bots", style="white")
            
            # API key mapping
            key_map = {
                "grok4": "XAI_API_KEY",
                "claude": "ANTHROPIC_API_KEY", 
                "gemini": "GOOGLE_AI_API_KEY",
                "openai": "OPENAI_API_KEY"
            }
            
            for agent_name, config in configs.items():
                llm_type = config.get('llm_type', 'unknown')
                api_key_env = key_map.get(llm_type, '')
                api_status = "✅" if os.getenv(api_key_env) else "❌"
                
                table.add_row(
                    agent_name,
                    llm_type,
                    api_status,
                    str(config.get('max_context_messages', 'N/A')),
                    str(config.get('max_turns_per_thread', 'N/A')),
                    f"{config.get('response_delay', 'N/A')}s",
                    "✅" if config.get('ignore_bots', True) else "❌"
                )
            
            # Add separator and API key status
            table.add_row("", "", "", "", "", "", "")
            table.add_row("API KEY STATUS", "", "", "", "", "", "")
            table.add_row("", "", "", "", "", "", "")
            
            for llm, env_var in key_map.items():
                api_status = "✅ Set" if os.getenv(env_var) else "❌ Missing"
                table.add_row(
                    f"{llm.upper()} API Key",
                    env_var,
                    api_status,
                    "", "", "", ""
                )
            
            content = table
        
        return Panel(
            content,
            title="[bold magenta]⚙️ Detailed Agent Configuration[/bold magenta]",
            border_style="magenta",
            box=DOUBLE
        )
    
    def create_system_detail(self) -> Panel:
        """Create detailed system view"""
        system = self.get_system_status()
        
        # Get additional system info
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        table = Table(show_header=True, box=ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Current", style="yellow")
        table.add_column("Total/Available", style="green")
        table.add_column("Status", style="bold")
        
        # CPU
        cpu_color = "red" if system["cpu_percent"] > 80 else "yellow" if system["cpu_percent"] > 60 else "green"
        table.add_row(
            "CPU Usage",
            f"{system['cpu_percent']:.1f}%",
            f"{psutil.cpu_count()} cores",
            Text("●", style=cpu_color)
        )
        
        # Memory
        mem_color = "red" if system["memory_percent"] > 85 else "yellow" if system["memory_percent"] > 70 else "green"
        table.add_row(
            "Memory Usage",
            f"{system['memory_percent']:.1f}%",
            f"{memory.total / (1024**3):.1f}GB total",
            Text("●", style=mem_color)
        )
        
        # Disk
        disk_color = "red" if system["disk_percent"] > 90 else "yellow" if system["disk_percent"] > 80 else "green"
        table.add_row(
            "Disk Usage",
            f"{system['disk_percent']:.1f}%",
            f"{disk.total / (1024**3):.1f}GB total",
            Text("●", style=disk_color)
        )
        
        # Load Average
        load_color = "red" if system["load_avg"] > 4 else "yellow" if system["load_avg"] > 2 else "green"
        table.add_row(
            "Load Average",
            f"{system['load_avg']:.2f}",
            f"1min avg",
            Text("●", style=load_color)
        )
        
        # Boot time
        boot_time = datetime.fromtimestamp(system['boot_time']).strftime('%Y-%m-%d %H:%M:%S')
        uptime_hours = (time.time() - system['boot_time']) / 3600
        table.add_row(
            "System Uptime",
            f"{uptime_hours:.1f}h",
            f"Since {boot_time}",
            Text("●", style="green")
        )
        
        return Panel(
            table,
            title="[bold blue]🖥️ Detailed System Information[/bold blue]",
            border_style="blue",
            box=DOUBLE
        )
    
    def create_postgres_detail(self) -> Panel:
        """Create detailed PostgreSQL view"""
        try:
            conn = psycopg2.connect(self.postgres_url)
            cursor = conn.cursor()
            
            # Get database info
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            cursor.execute("SELECT count(*) FROM pg_stat_activity;")
            connections = cursor.fetchone()[0]
            
            cursor.execute("SELECT pg_database_size(current_database());")
            db_size = cursor.fetchone()[0]
            
            conn.close()
            
            table = Table(show_header=True, box=ROUNDED)
            table.add_column("Property", style="cyan", width=20)
            table.add_column("Value", style="white", width=50)
            table.add_column("Status", style="bold", width=10)
            
            table.add_row(
                "Connection",
                "Connected successfully",
                Text("✅", style="green")
            )
            
            table.add_row(
                "Database URL",
                self.postgres_url,
                Text("✅", style="green")
            )
            
            table.add_row(
                "Version",
                version[:50] + "..." if len(version) > 50 else version,
                Text("✅", style="green")
            )
            
            table.add_row(
                "Active Connections",
                str(connections),
                Text("✅", style="green")
            )
            
            table.add_row(
                "Database Size",
                f"{db_size / (1024**2):.1f} MB",
                Text("✅", style="green")
            )
            
            content = table
            status = "Connected"
            
        except Exception as e:
            content = Text()
            content.append("❌ Connection Failed\n\n", style="bold red")
            content.append(f"Error: {str(e)}\n\n", style="red")
            content.append(f"URL: {self.postgres_url}\n", style="yellow")
            content.append("\nCheck:\n", style="bold")
            content.append("  • PostgreSQL is running\n", style="cyan")
            content.append("  • Connection credentials\n", style="cyan")
            content.append("  • Network connectivity", style="cyan")
            status = "Failed"
        
        return Panel(
            content,
            title=f"[bold magenta]🐘 Detailed PostgreSQL Information - {status}[/bold magenta]",
            border_style="magenta",
            box=DOUBLE
        )
    
    def create_logs_detail(self) -> Panel:
        """Create detailed logs view"""
        agents = self.get_agent_processes()
        
        content = Text()
        
        if not agents:
            content.append("❌ No agents running to show logs for\n", style="bold red")
        else:
            for agent_name in agents.keys():
                log_file = Path(f"logs/{agent_name}.log")
                
                content.append(f"\n🤖 {agent_name.upper()} LOGS:\n", style="bold cyan")
                content.append("═" * 50 + "\n", style="dim")
                
                if log_file.exists():
                    try:
                        with open(log_file, 'r') as f:
                            lines = f.readlines()
                            recent_lines = lines[-15:]  # Last 15 lines
                            
                            for line in recent_lines:
                                line = line.strip()
                                if "ERROR" in line:
                                    content.append(line + "\n", style="red")
                                elif "WARNING" in line:
                                    content.append(line + "\n", style="yellow")
                                elif "INFO" in line:
                                    content.append(line + "\n", style="white")
                                else:
                                    content.append(line + "\n", style="dim")
                    except Exception as e:
                        content.append(f"Error reading log: {e}\n", style="red")
                else:
                    content.append("Log file not found\n", style="yellow")
                
                content.append("\n")
        
        return Panel(
            content,
            title="[bold yellow]📋 Detailed Agent Logs[/bold yellow]",
            border_style="yellow",
            box=DOUBLE
        )
    
    def create_main_layout(self) -> Layout:
        """Create main dashboard layout or detail view"""
        layout = Layout()
        
        if self.detail_mode == 'agents':
            layout.split_column(
                Layout(self.create_header(), size=3),
                Layout(self.create_agents_detail())
            )
        elif self.detail_mode == 'teams':
            layout.split_column(
                Layout(self.create_header(), size=3),
                Layout(self.create_teams_detail())
            )
        elif self.detail_mode == 'configs':
            layout.split_column(
                Layout(self.create_header(), size=3),
                Layout(self.create_configs_detail())
            )
        elif self.detail_mode == 'system':
            layout.split_column(
                Layout(self.create_header(), size=3),
                Layout(self.create_system_detail())
            )
        elif self.detail_mode == 'postgres':
            layout.split_column(
                Layout(self.create_header(), size=3),
                Layout(self.create_postgres_detail())
            )
        elif self.detail_mode == 'logs':
            layout.split_column(
                Layout(self.create_header(), size=3),
                Layout(self.create_logs_detail())
            )
        else:
            # Import existing dashboard panels
            from agent_dashboard import SuperAgentDashboard
            base_dashboard = SuperAgentDashboard()
            
            layout.split_column(
                Layout(self.create_header(), size=3),
                Layout(name="main")
            )
            
            layout["main"].split_row(
                Layout(name="left"),
                Layout(name="center"),
                Layout(name="right")
            )
            
            layout["left"].split_column(
                Layout(base_dashboard.create_system_panel()),
                Layout(base_dashboard.create_postgres_panel())
            )
            
            layout["center"].split_column(
                Layout(base_dashboard.create_agents_panel()),
                Layout(base_dashboard.create_containers_panel())
            )
            
            layout["right"].split_column(
                Layout(base_dashboard.create_teams_panel()),
                Layout(base_dashboard.create_configs_panel())
            )
        
        return layout
    
    def input_thread(self):
        """Thread to handle user input"""
        while True:
            try:
                key = input().strip().lower()
                if key:
                    self.input_queue.put(key)
            except (EOFError, KeyboardInterrupt):
                break
    
    async def run(self, refresh_interval: float = 1.0):
        """Run the enhanced dashboard"""
        self.console.print("[bold green]🎮 Enhanced Dashboard Starting...[/bold green]")
        self.console.print("[dim]Press 1-6 for details, ESC to go back, Q to quit[/dim]")
        
        # Start input thread
        input_thread = threading.Thread(target=self.input_thread, daemon=True)
        input_thread.start()
        
        with Live(auto_refresh=False, console=self.console) as live:
            while True:
                try:
                    # Handle input
                    try:
                        key = self.input_queue.get_nowait()
                        
                        if key == 'q':
                            break
                        elif key == '0' or key == 'escape' or key == 'esc':
                            self.detail_mode = None
                        elif key == '1':
                            self.detail_mode = 'agents'
                        elif key == '2':
                            self.detail_mode = 'teams'
                        elif key == '3':
                            self.detail_mode = 'configs'
                        elif key == '4':
                            self.detail_mode = 'system'
                        elif key == '5':
                            self.detail_mode = 'postgres'
                        elif key == '6':
                            self.detail_mode = 'logs'
                        
                    except queue.Empty:
                        pass
                    
                    # Update display
                    layout = self.create_main_layout()
                    live.update(layout)
                    live.refresh()
                    
                    await asyncio.sleep(refresh_interval)
                    
                except KeyboardInterrupt:
                    break
        
        self.console.print("\n[yellow]Enhanced Dashboard stopped[/yellow]")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SuperAgent Enhanced Dashboard')
    parser.add_argument(
        '--refresh', 
        type=float, 
        default=1.0,
        help='Refresh interval in seconds (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    dashboard = DetailDashboard()
    
    try:
        asyncio.run(dashboard.run(args.refresh))
    except KeyboardInterrupt:
        print("\nDashboard stopped")

if __name__ == "__main__":
    main()