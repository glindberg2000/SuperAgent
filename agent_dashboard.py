#!/usr/bin/env python3
"""
SuperAgent CLI Dashboard
Beautiful real-time monitoring for agents, PostgreSQL, and system status
"""

import asyncio
import os
import psutil
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import time
import sys

# Rich imports for beautiful CLI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.align import Align
    from rich.columns import Columns
    from rich.box import ROUNDED
    import docker
    import psycopg2
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("pip install rich docker psycopg2-binary")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

# Import manager for team and config access
from superagent_manager import SuperAgentManager

class SuperAgentDashboard:
    """Beautiful CLI dashboard for SuperAgent monitoring"""
    
    def __init__(self):
        self.console = Console()
        self.docker_client = None
        self.postgres_url = os.getenv('POSTGRES_URL', 'postgresql://superagent:superagent@localhost:5433/superagent')
        self.logs_dir = Path("logs")
        self.agents_status = {}
        self.last_update = datetime.now()
        
        # Initialize manager for teams and config access
        self.manager = SuperAgentManager()
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception:
            pass
    
    def get_system_status(self) -> Dict:
        """Get system resource status"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "load_avg": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0,
            "uptime": time.time() - psutil.boot_time()
        }
    
    def get_postgres_status(self) -> Tuple[bool, str]:
        """Check PostgreSQL connection"""
        try:
            import psycopg2
            conn = psycopg2.connect(self.postgres_url)
            conn.close()
            return True, "Connected"
        except Exception as e:
            return False, str(e)[:50]
    
    def get_agent_processes(self) -> Dict[str, Dict]:
        """Get running agent processes"""
        agents = {}
        
        try:
            # Check for running agent processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    cmdline_list = proc.info.get('cmdline', [])
                    if not cmdline_list:
                        continue
                        
                    cmdline = ' '.join(cmdline_list)
                    
                    # Check for single agent launcher
                    if 'launch_single_agent.py' in cmdline:
                        parts = cmdline.split()
                        agent_type = parts[-1] if len(parts) > 0 and parts[-1] in ['grok4_agent', 'claude_agent', 'gemini_agent', 'o3_agent'] else 'unknown'
                        
                        # Get CPU and memory with error handling
                        try:
                            cpu_percent = proc.cpu_percent() or 0
                        except:
                            cpu_percent = 0
                            
                        try:
                            memory_percent = proc.memory_percent() or 0
                        except:
                            memory_percent = 0
                        
                        agents[agent_type] = {
                            "pid": proc.info['pid'],
                            "type": "single_agent",
                            "agent": agent_type,
                            "uptime": time.time() - proc.info['create_time'],
                            "cpu": cpu_percent,
                            "memory": memory_percent,
                            "status": "running"
                        }
                    
                    # Check for hybrid launcher
                    elif 'multi_agent_launcher_hybrid.py' in cmdline:
                        agents["hybrid_system"] = {
                            "pid": proc.info['pid'],
                            "type": "hybrid_launcher",
                            "agent": "multiple",
                            "uptime": time.time() - proc.info['create_time'],
                            "cpu": proc.info['cpu_percent'] or 0,
                            "memory": proc.info['memory_percent'] or 0,
                            "status": "running"
                        }
                    
                    # Check for DevOps agent
                    elif 'mcp_devops_agent.py' in cmdline:
                        agents["devops_agent"] = {
                            "pid": proc.info['pid'],
                            "type": "devops_agent",
                            "agent": "devops",
                            "uptime": time.time() - proc.info['create_time'],
                            "cpu": proc.info['cpu_percent'] or 0,
                            "memory": proc.info['memory_percent'] or 0,
                            "status": "running"
                        }
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, IndexError):
                    continue
                    
        except Exception:
            pass
            
        return agents
    
    def get_docker_containers(self) -> Dict[str, Dict]:
        """Get SuperAgent Docker containers"""
        containers = {}
        
        if not self.docker_client:
            return containers
            
        try:
            for container in self.docker_client.containers.list(all=True):
                if any(label in container.name.lower() for label in ['superagent', 'claude-code', 'grok', 'discord', 'postgres']):
                    containers[container.name] = {
                        "id": container.id[:12],
                        "status": container.status,
                        "image": container.image.tags[0] if container.image.tags else "unknown",
                        "ports": container.ports,
                        "created": container.attrs['Created']
                    }
        except Exception:
            pass
            
        return containers
    
    def get_recent_logs(self, agent_name: str, lines: int = 5) -> List[str]:
        """Get recent log lines for an agent"""
        log_files = {
            "single_grok4_agent": "grok4_single_new.log",
            "single_claude_agent": "claude_single.log", 
            "single_gemini_agent": "gemini_single.log",
            "hybrid_system": "hybrid_agents.log",
            "devops_agent": "mcp_devops_agent.log"
        }
        
        log_file = self.logs_dir / log_files.get(agent_name, f"{agent_name}.log")
        
        if not log_file.exists():
            return ["No log file found"]
            
        try:
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                return [line.strip() for line in all_lines[-lines:]]
        except Exception as e:
            return [f"Error reading logs: {e}"]
    
    def create_system_panel(self) -> Panel:
        """Create system status panel"""
        system = self.get_system_status()
        
        # Create system metrics table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bright_white")
        table.add_column("Status", style="bold")
        
        # CPU
        cpu_color = "red" if system["cpu_percent"] > 80 else "yellow" if system["cpu_percent"] > 60 else "green"
        table.add_row(
            "CPU", 
            f"{system['cpu_percent']:.1f}%",
            Text("●", style=cpu_color)
        )
        
        # Memory
        mem_color = "red" if system["memory_percent"] > 85 else "yellow" if system["memory_percent"] > 70 else "green"
        table.add_row(
            "Memory", 
            f"{system['memory_percent']:.1f}%",
            Text("●", style=mem_color)
        )
        
        # Disk
        disk_color = "red" if system["disk_percent"] > 90 else "yellow" if system["disk_percent"] > 80 else "green"
        table.add_row(
            "Disk", 
            f"{system['disk_percent']:.1f}%",
            Text("●", style=disk_color)
        )
        
        # Load average
        load_color = "red" if system["load_avg"] > 4 else "yellow" if system["load_avg"] > 2 else "green"
        table.add_row(
            "Load", 
            f"{system['load_avg']:.2f}",
            Text("●", style=load_color)
        )
        
        # Uptime
        uptime_hours = system["uptime"] / 3600
        table.add_row(
            "Uptime", 
            f"{uptime_hours:.1f}h",
            Text("●", style="green")
        )
        
        return Panel(
            table,
            title="[bold blue]System Status[/bold blue]",
            border_style="blue",
            box=ROUNDED
        )
    
    def create_postgres_panel(self) -> Panel:
        """Create PostgreSQL status panel"""
        is_connected, status = self.get_postgres_status()
        
        # Get Docker container status for postgres
        containers = self.get_docker_containers()
        postgres_container = None
        for name, info in containers.items():
            if 'postgres' in name.lower():
                postgres_container = info
                break
        
        content = []
        
        # Connection status
        conn_icon = "✅" if is_connected else "❌"
        conn_color = "green" if is_connected else "red"
        content.append(f"{conn_icon} Connection: [{conn_color}]{status}[/{conn_color}]")
        
        # Container status
        if postgres_container:
            cont_icon = "🐳" if postgres_container["status"] == "running" else "⏸️"
            cont_color = "green" if postgres_container["status"] == "running" else "red"
            content.append(f"{cont_icon} Container: [{cont_color}]{postgres_container['status']}[/{cont_color}]")
            content.append(f"   Image: {postgres_container['image']}")
            if postgres_container['ports']:
                ports = ", ".join([f"{k}→{v}" for k, v in postgres_container['ports'].items()])
                content.append(f"   Ports: {ports}")
        else:
            content.append("🔍 Container: Not found")
        
        # Database URL
        content.append(f"📍 URL: {self.postgres_url}")
        
        return Panel(
            "\n".join(content),
            title="[bold magenta]PostgreSQL Status[/bold magenta]",
            border_style="magenta",
            box=ROUNDED
        )
    
    def create_agents_panel(self) -> Panel:
        """Create agents status panel"""
        agents = self.get_agent_processes()
        
        if not agents:
            return Panel(
                "[yellow]No agents currently running[/yellow]",
                title="[bold green]Active Agents[/bold green]",
                border_style="green",
                box=ROUNDED
            )
        
        table = Table(show_header=True, box=None)
        table.add_column("Agent", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("PID", style="white")
        table.add_column("Uptime", style="yellow")
        table.add_column("CPU%", style="red")
        table.add_column("Mem%", style="magenta")
        table.add_column("Status", style="bold green")
        
        for name, info in agents.items():
            uptime_str = f"{info['uptime']/60:.1f}m" if info['uptime'] < 3600 else f"{info['uptime']/3600:.1f}h"
            table.add_row(
                name.replace("_", " ").title(),
                info["type"].replace("_", " ").title(),
                str(info["pid"]),
                uptime_str,
                f"{info['cpu']:.1f}",
                f"{info['memory']:.1f}",
                "🟢 Running"
            )
        
        return Panel(
            table,
            title="[bold green]Active Agents[/bold green]",
            border_style="green",  
            box=ROUNDED
        )
    
    def create_containers_panel(self) -> Panel:
        """Create Docker containers panel"""
        containers = self.get_docker_containers()
        
        if not containers:
            return Panel(
                "[yellow]No containers found[/yellow]",
                title="[bold blue]Docker Containers[/bold blue]",
                border_style="blue",
                box=ROUNDED
            )
        
        table = Table(show_header=True, box=None)
        table.add_column("Container", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Image", style="blue")
        table.add_column("ID", style="dim")
        
        for name, info in containers.items():
            status_color = "green" if info["status"] == "running" else "red" if info["status"] == "exited" else "yellow"
            status_icon = "🟢" if info["status"] == "running" else "🔴" if info["status"] == "exited" else "🟡"
            
            table.add_row(
                name,
                f"{status_icon} [{status_color}]{info['status']}[/{status_color}]",
                info["image"],
                info["id"]
            )
        
        return Panel(
            table,
            title="[bold blue]Docker Containers[/bold blue]",
            border_style="blue",
            box=ROUNDED
        )
    
    def create_logs_panel(self) -> Panel:
        """Create recent logs panel"""
        agents = self.get_agent_processes()
        
        if not agents:
            return Panel(
                "[yellow]No agents to show logs for[/yellow]",
                title="[bold yellow]Recent Logs[/bold yellow]",
                border_style="yellow",
                box=ROUNDED
            )
        
        content = []
        
        for agent_name in list(agents.keys())[:2]:  # Show logs for first 2 agents
            logs = self.get_recent_logs(agent_name, 3)
            content.append(f"[bold cyan]{agent_name}:[/bold cyan]")
            for log_line in logs:
                # Truncate long lines
                if len(log_line) > 80:
                    log_line = log_line[:77] + "..."
                content.append(f"  {log_line}")
            content.append("")
        
        return Panel(
            "\n".join(content),
            title="[bold yellow]Recent Logs[/bold yellow]",
            border_style="yellow",
            box=ROUNDED
        )
    
    def create_teams_panel(self) -> Panel:
        """Create teams configuration panel"""
        try:
            teams = self.manager.list_teams()
            if not teams:
                return Panel(
                    "[yellow]No teams configured[/yellow]",
                    title="[bold cyan]Teams[/bold cyan]",
                    border_style="cyan",
                    box=ROUNDED
                )
            
            table = Table(show_header=True, box=None)
            table.add_column("Team", style="cyan")
            table.add_column("Agents", style="green")
            table.add_column("Server", style="blue")
            table.add_column("Status", style="yellow")
            
            for team_name, team_info in teams.items():
                agents_str = ", ".join(team_info.get('agents', []))
                if len(agents_str) > 20:
                    agents_str = agents_str[:17] + "..."
                
                server_id = team_info.get('default_server_id', 'N/A')
                if len(server_id) > 15:
                    server_id = server_id[:12] + "..."
                
                auto_deploy = "🟢 Auto" if team_info.get('auto_deploy') else "🔴 Manual"
                
                table.add_row(
                    team_name,
                    agents_str,
                    server_id,
                    auto_deploy
                )
            
            return Panel(
                table,
                title="[bold cyan]Teams Configuration[/bold cyan]",
                border_style="cyan",
                box=ROUNDED
            )
        except Exception as e:
            return Panel(
                f"[red]Error loading teams: {e}[/red]",
                title="[bold cyan]Teams[/bold cyan]",
                border_style="cyan",
                box=ROUNDED
            )
    
    def create_configs_panel(self) -> Panel:
        """Create agent configurations panel"""
        try:
            configs = self.manager.show_agent_configs()
            if not configs:
                return Panel(
                    "[yellow]No agent configs found[/yellow]",
                    title="[bold magenta]Agent Configs[/bold magenta]",
                    border_style="magenta",
                    box=ROUNDED
                )
            
            content = []
            for line in configs.split('\n')[:8]:  # Show first 8 lines
                if line.strip():
                    # Color code the line based on content
                    if "Agent:" in line:
                        content.append(f"[bold cyan]{line}[/bold cyan]")
                    elif "LLM:" in line:
                        content.append(f"[green]{line}[/green]")
                    elif "Max Context:" in line or "Max Turns:" in line:
                        content.append(f"[yellow]{line}[/yellow]")
                    else:
                        content.append(line)
            
            if len(configs.split('\n')) > 8:
                content.append("[dim]... (truncated)[/dim]")
            
            return Panel(
                "\n".join(content),
                title="[bold magenta]Agent Configs[/bold magenta]",
                border_style="magenta",
                box=ROUNDED
            )
        except Exception as e:
            return Panel(
                f"[red]Error loading configs: {e}[/red]",
                title="[bold magenta]Agent Configs[/bold magenta]",
                border_style="magenta",
                box=ROUNDED
            )
    
    def create_header(self) -> Panel:
        """Create dashboard header"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        header_text = Text()
        header_text.append("🤖 SuperAgent Dashboard", style="bold blue")
        header_text.append(" | ", style="dim")
        header_text.append(f"Updated: {current_time}", style="dim")
        header_text.append(" | ", style="dim")
        header_text.append("Press Ctrl+C to exit", style="dim italic")
        
        return Panel(
            Align.center(header_text),
            style="bold white on blue",
            box=ROUNDED
        )
    
    def create_layout(self) -> Layout:
        """Create the main dashboard layout"""
        layout = Layout()
        
        # Split into rows
        layout.split_column(
            Layout(self.create_header(), size=3, name="header"),
            Layout(name="main"),
            Layout(name="bottom")
        )
        
        # Split main section into columns
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="center"),
            Layout(name="right")
        )
        
        # Split left column
        layout["left"].split_column(
            Layout(self.create_system_panel(), name="system"),
            Layout(self.create_postgres_panel(), name="postgres")
        )
        
        # Split center column
        layout["center"].split_column(
            Layout(self.create_agents_panel(), name="agents"),
            Layout(self.create_containers_panel(), name="containers")
        )
        
        # Split right column for teams and configs
        layout["right"].split_column(
            Layout(self.create_teams_panel(), name="teams"),
            Layout(self.create_configs_panel(), name="configs")
        )
        
        # Bottom section for logs
        layout["bottom"].split_column(
            Layout(self.create_logs_panel(), size=12, name="logs")
        )
        
        return layout
    
    def update_layout(self, layout: Layout):
        """Update all panels in the layout"""
        layout["header"].update(self.create_header())
        layout["system"].update(self.create_system_panel())
        layout["postgres"].update(self.create_postgres_panel())
        layout["agents"].update(self.create_agents_panel())
        layout["containers"].update(self.create_containers_panel())
        layout["teams"].update(self.create_teams_panel())
        layout["configs"].update(self.create_configs_panel())
        layout["logs"].update(self.create_logs_panel())
    
    async def run(self, refresh_interval: float = 2.0):
        """Run the live dashboard"""
        layout = self.create_layout()
        
        with Live(layout, console=self.console, refresh_per_second=1/refresh_interval) as live:
            try:
                while True:
                    await asyncio.sleep(refresh_interval)
                    self.update_layout(layout)
                    self.last_update = datetime.now()
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Dashboard stopped by user[/yellow]")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SuperAgent CLI Dashboard')
    parser.add_argument(
        '--refresh', 
        type=float, 
        default=2.0,
        help='Refresh interval in seconds (default: 2.0)'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Run a quick status check and exit'
    )
    
    args = parser.parse_args()
    
    dashboard = SuperAgentDashboard()
    
    if args.check:
        # Quick status check
        console = Console()
        console.print(Panel("[bold blue]SuperAgent Quick Status Check[/bold blue]"))
        
        # System
        system = dashboard.get_system_status()
        console.print(f"🖥️  System: CPU {system['cpu_percent']:.1f}%, Memory {system['memory_percent']:.1f}%")
        
        # PostgreSQL
        pg_connected, pg_status = dashboard.get_postgres_status()
        pg_icon = "✅" if pg_connected else "❌"
        console.print(f"{pg_icon} PostgreSQL: {pg_status}")
        
        # Agents
        agents = dashboard.get_agent_processes()
        console.print(f"🤖 Active Agents: {len(agents)}")
        for name, info in agents.items():
            console.print(f"   • {name}: PID {info['pid']}, uptime {info['uptime']/60:.1f}m")
        
        return
    
    # Run live dashboard
    try:
        asyncio.run(dashboard.run(args.refresh))
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[yellow]Dashboard stopped[/yellow]")

if __name__ == "__main__":
    main()