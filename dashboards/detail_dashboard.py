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
        
        # Initialize Docker client with multiple fallback options
        self.docker_client = None
        
        # Try Colima socket first (seems to be working on this system)
        try:
            self.docker_client = docker.DockerClient(base_url='unix:///Users/greg/.colima/default/docker.sock')
        except Exception:
            # Try Docker Desktop environment
            try:
                self.docker_client = docker.from_env()
            except Exception:
                # Try standard docker socket
                try:
                    self.docker_client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
                except Exception:
                    pass
    
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
    
    def get_discord_bot_name(self, agent_type: str) -> str:
        """Extract Discord bot name from agent logs"""
        log_files = {
            "grok4_agent": ["grok4_restart.log", "grok4_fixed.log", "grok4_single_new.log"],
            "claude_agent": ["claude_restart.log", "claude_fixed.log", "claude_single.log"],
            "gemini_agent": ["gemini_single.log"],
            "devops_agent": ["mcp_devops_agent.log"],
            "o3_agent": ["o3_single.log"]
        }
        
        # Try to find the bot name from logs
        for log_file in log_files.get(agent_type, []):
            log_path = Path("logs") / log_file
            if log_path.exists():
                try:
                    with open(log_path, 'r') as f:
                        # Read all lines and search for the login message
                        content = f.read()
                        # Look for the most recent "Logged in as" message
                        import re
                        matches = re.findall(r'Logged in as (.+)', content)
                        if matches:
                            # Use the last match found (most recent)
                            bot_name = matches[-1].strip()
                            return bot_name
                except Exception:
                    continue
        
        # Fallback to agent type mapping
        fallback_names = {
            "grok4_agent": "Grok4",
            "claude_agent": "Claude Agent",
            "gemini_agent": "Gemini Agent",
            "devops_agent": "DevOps",
            "o3_agent": "O3 Agent"
        }
        return fallback_names.get(agent_type, agent_type.replace("_", " ").title())

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
                        
                        # Get actual Discord bot name
                        discord_name = self.get_discord_bot_name(agent_type)
                        
                        agents[agent_type] = {
                            "pid": proc.info['pid'],
                            "type": "single_agent",
                            "agent": agent_type,
                            "discord_name": discord_name,
                            "uptime": time.time() - proc.info['create_time'],
                            "cpu": proc.cpu_percent() or 0,
                            "memory": proc.memory_percent() or 0,
                            "status": "running"
                        }
                    
                    # Check for DevOps agent
                    elif 'mcp_devops_agent.py' in cmdline:
                        # Get actual Discord bot name
                        discord_name = self.get_discord_bot_name("devops_agent")
                        
                        agents["devops_agent"] = {
                            "pid": proc.info['pid'],
                            "type": "devops_agent",
                            "agent": "devops",
                            "discord_name": discord_name,
                            "uptime": time.time() - proc.info['create_time'],
                            "cpu": proc.cpu_percent() or 0,
                            "memory": proc.memory_percent() or 0,
                            "status": "running"
                        }
                    
                    # Check for other SuperAgent processes
                    elif any(x in cmdline for x in ['superagent_manager.py', 'multi_agent_launcher.py', 'enhanced_discord_agent.py']):
                        process_name = "manager" if 'manager' in cmdline else "launcher" if 'launcher' in cmdline else "discord_agent"
                        agents[f"{process_name}_{proc.info['pid']}"] = {
                            "pid": proc.info['pid'],
                            "type": "system_process",
                            "agent": process_name,
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
            header_text.append("0=Back C=Commands", style="cyan")
        else:
            header_text.append(" | ", style="dim")
            header_text.append("1=Agents 2=Teams 3=Configs 4=System 5=Postgres 6=Logs 7=Manage 8=Containers C=Commands Q=Quit", style="cyan")
        
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
                
                # Use Discord bot name if available, otherwise fall back to agent name
                display_name = info.get("discord_name", name.replace("_", " ").title())
                
                table.add_row(
                    display_name,
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
            table = Table(show_header=True, box=ROUNDED, expand=True)
            table.add_column("Discord Name", style="cyan", min_width=20, ratio=4)
            table.add_column("Agent ID", style="blue", min_width=15, ratio=3)
            table.add_column("LLM", style="green", min_width=10, ratio=2)
            table.add_column("API Key", style="yellow", min_width=10, ratio=2)
            table.add_column("Discord Token", style="magenta", min_width=15, ratio=3)
            table.add_column("Team", style="white", min_width=12, ratio=2)
            table.add_column("Context", style="dim", min_width=8, ratio=1)
            table.add_column("Turns", style="dim", min_width=8, ratio=1)
            table.add_column("Delay", style="dim", min_width=8, ratio=1)
            
            # Get running agents to access Discord names
            running_agents = self.get_agent_processes()
            teams_data = self.agent_config_data.get('teams', {})
            
            # Token and API key mapping
            token_map = {
                "grok4": "DISCORD_TOKEN_GROK4",
                "claude": "DISCORD_TOKEN_CLAUDE", 
                "gemini": "DISCORD_TOKEN_GEMINI",
                "openai": "DISCORD_TOKEN_OPENAI"
            }
            
            key_map = {
                "grok4": "XAI_API_KEY",
                "claude": "ANTHROPIC_API_KEY", 
                "gemini": "GEMINI_API_KEY",
                "openai": "OPENAI_API_KEY"
            }
            
            # Find which team each agent belongs to
            agent_teams = {}
            for team_name, team_config in teams_data.items():
                team_agents = team_config.get('agents', [])
                for agent_id in team_agents:
                    agent_teams[agent_id] = team_name
            
            for agent_name, config in configs.items():
                llm_type = config.get('llm_type', 'unknown')
                api_key_env = key_map.get(llm_type, '')
                token_env = token_map.get(llm_type, '')
                
                # Get Discord name from running agent or show as offline
                discord_name = "🔴 Offline"
                if agent_name in running_agents:
                    discord_name = running_agents[agent_name].get("discord_name", "Unknown")
                    if not discord_name.startswith("🔴"):
                        discord_name = f"🟢 {discord_name}"
                
                # Enhanced status indicators with key snippets
                api_key_value = os.getenv(api_key_env, '')
                token_value = os.getenv(token_env, '')
                
                if api_key_value:
                    api_snippet = f"{api_key_value[:8]}...{api_key_value[-4:]}" if len(api_key_value) > 12 else api_key_value
                    api_status = f"✅ {api_snippet}\n({api_key_env})"
                else:
                    api_status = f"❌ Missing\n({api_key_env})"
                
                if token_value:
                    token_snippet = f"{token_value[:12]}...{token_value[-8:]}" if len(token_value) > 20 else f"{len(token_value)} chars"
                    token_status = f"✅ {token_snippet}\n({token_env})"
                else:
                    token_status = f"❌ Missing\n({token_env})"
                
                # Get team membership
                team = agent_teams.get(agent_name, "None")
                
                table.add_row(
                    discord_name,
                    agent_name,
                    llm_type,
                    api_status,
                    token_status,
                    team,
                    str(config.get('max_context_messages', 'N/A')),
                    str(config.get('max_turns_per_thread', 'N/A')),
                    f"{config.get('response_delay', 'N/A')}s"
                )
            
            # Add separator and detailed environment status
            table.add_row("", "", "", "", "", "", "", "", "")
            table.add_row("[bold]ENVIRONMENT STATUS[/bold]", "", "", "", "", "", "", "", "")
            table.add_row("", "", "", "", "", "", "", "", "")
            
            # Show detailed environment variable status
            for llm in ["grok4", "claude", "gemini", "openai"]:
                token_env = token_map.get(llm, "")
                api_env = key_map.get(llm, "")
                
                token_val = os.getenv(token_env, "")
                api_val = os.getenv(api_env, "")
                
                # Enhanced status with snippets and env var names
                if token_val:
                    token_snippet = f"{token_val[:12]}...{token_val[-8:]}" if len(token_val) > 20 else f"{len(token_val)} chars"
                    token_status = f"✅ {token_snippet}\n({token_env})"
                else:
                    token_status = f"❌ Missing\n({token_env})"
                
                if api_val:
                    api_snippet = f"{api_val[:8]}...{api_val[-4:]}" if len(api_val) > 12 else api_val
                    api_status = f"✅ {api_snippet}\n({api_env})"
                else:
                    api_status = f"❌ Missing\n({api_env})"
                
                table.add_row(
                    f"🔧 {llm.upper()}",
                    token_env.replace("DISCORD_TOKEN_", ""),
                    "",
                    api_status,
                    token_status,
                    "", "", "", ""
                )
            
            content = table
        
        return Panel(
            content,
            title="[bold magenta]⚙️ Detailed Agent Configuration[/bold magenta]",
            border_style="magenta",
            box=DOUBLE
        )
    
    def get_containerized_bots(self) -> Dict[str, Dict]:
        """Get containerized Discord bots (Claude Code containers, etc.)"""
        containers = {}
        
        if not self.docker_client:
            return containers
            
        try:
            all_containers = self.docker_client.containers.list(all=True)
            for container in all_containers:
                container_name = container.name.lower()
                labels = container.labels or {}
                
                # Check if this is a SuperAgent containerized bot
                is_bot_container = False
                bot_type = "unknown"
                
                # Check for Claude Code containers
                if ('claude-code' in container.image.tags[0] if container.image.tags else False) or \
                   labels.get('superagent.type') == 'claude-code':
                    is_bot_container = True
                    bot_type = "claude-code"
                
                # Check for other SuperAgent containers
                elif any(label in container_name for label in ['superagent', 'discord-bot', 'agent']) or \
                     labels.get('superagent.team') or \
                     labels.get('superagent.agent'):
                    is_bot_container = True
                    bot_type = labels.get('superagent.type', 'superagent-bot')
                
                if is_bot_container:
                    containers[container.name] = {
                        "id": container.id[:12],
                        "status": container.status,
                        "image": container.image.tags[0] if container.image.tags else "unknown",
                        "ports": container.ports,
                        "created": container.attrs['Created'],
                        "type": bot_type,
                        "team": labels.get('superagent.team', 'unknown'),
                        "agent_type": labels.get('superagent.agent', 'unknown'),
                        "labels": labels
                    }
        except Exception as e:
            # Debug: show why Docker detection failed
            pass
            
        return containers
    
    def create_containers_detail(self) -> Panel:
        """Create detailed containerized bots view"""
        containers = self.get_containerized_bots()
        
        if not containers:
            content = Text()
            content.append("❌ No containerized bots found\n\n", style="bold red")
            content.append("Containerized bots include:\n", style="bold")
            content.append("  • Claude Code containers\n", style="green")
            content.append("  • SuperAgent Discord bots\n", style="green") 
            content.append("  • DevOps agent containers\n", style="green")
            content.append("  • Custom agent containers\n\n", style="green")
            content.append("To deploy containers:\n", style="bold")
            content.append("  python orchestrator_mvp.py spawn claude_agent\n", style="cyan")
            content.append("  python control_plane/mcp_devops_agent.py\n", style="cyan")
        else:
            table = Table(show_header=True, box=ROUNDED, expand=True)
            table.add_column("Container", style="cyan", min_width=20, ratio=4)
            table.add_column("Type", style="blue", min_width=15, ratio=3)
            table.add_column("Status", style="bold", min_width=12, ratio=2)
            table.add_column("Team", style="green", min_width=10, ratio=2)
            table.add_column("Image", style="yellow", min_width=20, ratio=4)
            table.add_column("ID", style="dim", min_width=12, ratio=2)
            table.add_column("Ports", style="magenta", min_width=15, ratio=3)
            
            for name, info in containers.items():
                status_color = "green" if info["status"] == "running" else "red" if info["status"] == "exited" else "yellow"
                status_icon = "🟢" if info["status"] == "running" else "🔴" if info["status"] == "exited" else "🟡"
                
                # Format ports
                ports_str = ""
                if info["ports"]:
                    port_mappings = []
                    for container_port, host_bindings in info["ports"].items():
                        if host_bindings:
                            for binding in host_bindings:
                                host_port = binding.get('HostPort', '')
                                if host_port:
                                    port_mappings.append(f"{host_port}→{container_port}")
                    ports_str = ", ".join(port_mappings)
                
                table.add_row(
                    name,
                    info["type"],
                    f"{status_icon} [{status_color}]{info['status']}[/{status_color}]",
                    info["team"],
                    info["image"],
                    info["id"],
                    ports_str or "None"
                )
            
            content = table
        
        return Panel(
            content,
            title="[bold blue]🐳 Containerized Discord Bots[/bold blue]",
            border_style="blue",
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
    
    def create_management_detail(self) -> Panel:
        """Create agent/team management view"""
        content = Text()
        
        # Current system status
        content.append("🎛️  SUPERAGENT MANAGEMENT CENTER\n", style="bold cyan")
        content.append("═" * 50 + "\n\n", style="dim")
        
        # Running agents status
        agents = self.get_agent_processes()
        content.append("📊 CURRENT STATUS:\n", style="bold")
        content.append(f"   Active Agents: {len(agents)}\n", style="green")
        for name, info in agents.items():
            uptime = f"{info['uptime']/60:.1f}m" if info['uptime'] < 3600 else f"{info['uptime']/3600:.1f}h"
            content.append(f"   • {name}: PID {info['pid']} ({uptime})\n", style="white")
        
        content.append("\n")
        
        # Team status
        teams = self.agent_config_data.get('teams', {})
        content.append("👥 TEAMS OVERVIEW:\n", style="bold")
        for team_name, team_info in teams.items():
            auto_deploy = "🟢 Auto" if team_info.get('auto_deploy') else "🔴 Manual"
            agents_list = ", ".join(team_info.get('agents', []))
            content.append(f"   • {team_name}: {auto_deploy} | Agents: {agents_list}\n", style="white")
        
        content.append("\n")
        
        # Missing components
        content.append("⚠️  MISSING COMPONENTS:\n", style="bold yellow")
        
        # Check for DevOps agent
        devops_running = any('devops' in name.lower() for name in agents.keys())
        if not devops_running:
            content.append("   ❌ DevOps Agent (required for management)\n", style="red")
        else:
            content.append("   ✅ DevOps Agent is running\n", style="green")
        
        # Check API keys
        api_keys = {
            "XAI_API_KEY": "Grok4",
            "ANTHROPIC_API_KEY": "Claude", 
            "GEMINI_API_KEY": "Gemini",
            "OPENAI_API_KEY": "OpenAI"
        }
        
        missing_keys = []
        for env_var, name in api_keys.items():
            if not os.getenv(env_var):
                missing_keys.append(f"{name} ({env_var})")
        
        if missing_keys:
            content.append(f"   ❌ Missing API Keys: {', '.join(missing_keys)}\n", style="red")
        else:
            content.append("   ✅ All API Keys configured\n", style="green")
        
        content.append("\n")
        
        # Quick actions
        content.append("🚀 QUICK ACTIONS:\n", style="bold")
        content.append("   Press 'C' for command interface\n", style="cyan")
        content.append("   Available commands:\n", style="white")
        content.append("   • deploy <agent_type>    - Start an agent\n", style="dim")
        content.append("   • stop <agent_type>      - Stop an agent\n", style="dim")
        content.append("   • team deploy <team>     - Deploy entire team\n", style="dim")
        content.append("   • team stop <team>       - Stop entire team\n", style="dim")
        content.append("   • status                 - Show detailed status\n", style="dim")
        content.append("   • logs <agent>           - View agent logs\n", style="dim")
        
        content.append("\n")
        content.append("💡 TIP: DevOps agent provides web UI and API management\n", style="dim")
        content.append("    Start with: python control_plane/mcp_devops_agent.py\n", style="dim")
        
        return Panel(
            content,
            title="[bold green]🎛️ SuperAgent Management Center[/bold green]",
            border_style="green",
            box=DOUBLE
        )
    
    def create_commands_detail(self) -> Panel:
        """Create interactive commands view"""
        content = Text()
        
        content.append("💻 SUPERAGENT COMMAND CENTER\n", style="bold cyan")
        content.append("═" * 50 + "\n\n", style="dim")
        
        content.append("📋 AVAILABLE COMMANDS:\n\n", style="bold")
        
        # Agent Management
        content.append("🤖 AGENT MANAGEMENT:\n", style="bold green")
        content.append("   deploy grok4_agent       - Deploy Grok4 agent\n", style="white")
        content.append("   deploy claude_agent      - Deploy Claude agent\n", style="white") 
        content.append("   deploy gemini_agent      - Deploy Gemini agent\n", style="white")
        content.append("   deploy openai_agent      - Deploy OpenAI agent\n", style="white")
        content.append("   stop <agent_name>        - Stop specific agent\n", style="white")
        content.append("   restart <agent_name>     - Restart agent\n", style="white")
        content.append("   status <agent_name>      - Check agent status\n\n", style="white")
        
        # Team Management
        content.append("👥 TEAM MANAGEMENT:\n", style="bold blue")
        content.append("   team deploy research     - Deploy research team\n", style="white")
        content.append("   team deploy creative     - Deploy creative team\n", style="white")
        content.append("   team deploy dev          - Deploy dev team\n", style="white")
        content.append("   team stop <team_name>    - Stop entire team\n", style="white")
        content.append("   team status              - Show all team status\n\n", style="white")
        
        # System Management
        content.append("⚙️ SYSTEM MANAGEMENT:\n", style="bold magenta")
        content.append("   devops start             - Start DevOps agent\n", style="white")
        content.append("   devops stop              - Stop DevOps agent\n", style="white")
        content.append("   system status            - Full system check\n", style="white")
        content.append("   logs <agent_name>        - View agent logs\n", style="white")
        content.append("   config reload            - Reload configurations\n\n", style="white")
        
        # Database Management  
        content.append("🗄️ DATABASE MANAGEMENT:\n", style="bold yellow")
        content.append("   db status                - Check PostgreSQL status\n", style="white")
        content.append("   db backup                - Create database backup\n", style="white")
        content.append("   db migrate               - Run database migrations\n\n", style="white")
        
        # Environment
        content.append("🔧 ENVIRONMENT:\n", style="bold red")
        content.append("   env check                - Validate all environment variables\n", style="white")
        content.append("   env list                 - List all configurations\n", style="white")
        content.append("   api-keys check           - Verify all API keys\n\n", style="white")
        
        content.append("💡 USAGE: Type commands in the terminal while dashboard runs\n", style="dim")
        content.append("   Commands are executed via superagent_manager.py\n", style="dim")
        content.append("   Example: python superagent_manager.py deploy grok4_agent\n", style="dim")
        
        return Panel(
            content,
            title="[bold cyan]💻 Command Reference Guide[/bold cyan]",
            border_style="cyan",
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
        elif self.detail_mode == 'manage':
            layout.split_column(
                Layout(self.create_header(), size=3),
                Layout(self.create_management_detail())
            )
        elif self.detail_mode == 'commands':
            layout.split_column(
                Layout(self.create_header(), size=3),
                Layout(self.create_commands_detail())
            )
        elif self.detail_mode == 'containers':
            layout.split_column(
                Layout(self.create_header(), size=3),
                Layout(self.create_containers_detail())
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
                        elif key == '7':
                            self.detail_mode = 'manage'
                        elif key == '8':
                            self.detail_mode = 'containers'
                        elif key == 'c':
                            self.detail_mode = 'commands'
                        
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