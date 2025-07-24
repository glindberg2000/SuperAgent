#!/usr/bin/env python3
"""
SuperAgent DOS-Style Interactive Dashboard
True keyboard navigation with popup details - old school DOS interface
"""

import asyncio
import os
import json
import time
import sys
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
    from rich.box import ROUNDED, DOUBLE, HEAVY
    import psutil
    import docker
    import psycopg2
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("pip install rich psutil docker psycopg2-binary")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

class DOSDashboard:
    """DOS-style interactive dashboard with keyboard navigation"""
    
    def __init__(self):
        self.console = Console()
        self.current_panel = 0
        self.panels = ["system", "postgres", "agents", "containers", "teams", "configs"]
        self.panel_names = ["System", "PostgreSQL", "Agents", "Containers", "Teams", "Configs"]
        self.show_popup = False
        self.popup_content = ""
        self.last_key = ""
        self.docker_client = None
        self.postgres_url = os.getenv('POSTGRES_URL', 'postgresql://superagent:superagent@localhost:5433/superagent')
        
        # Load config data
        self.config_file = Path("agent_config.json")
        self.agent_config_data = self._load_config_data()
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
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
        """Create DOS-style header"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        header_text = Text()
        header_text.append("█ SuperAgent DOS Dashboard ", style="bold white on blue")
        header_text.append(f"█ {current_time} ", style="bold white on blue")
        header_text.append(f"█ Panel: {self.panel_names[self.current_panel]} ", style="bold yellow on blue")
        header_text.append(f"█ Last Key: {self.last_key} ", style="bold cyan on blue")
        
        controls = Text()
        controls.append("Tab=Next | Enter=Details | Esc=Close | Q=Quit", style="bold yellow")
        
        content = Text()
        content.append_text(header_text)
        content.append("\\n")
        content.append_text(controls)
        
        return Panel(
            content,
            style="bold white on blue",
            box=HEAVY
        )
    
    def create_panel_content(self, panel_name: str, is_selected: bool) -> Panel:
        """Create individual panel content"""
        style = "bold green" if is_selected else "dim"
        border_style = "bright_green" if is_selected else "blue"
        box_style = DOUBLE if is_selected else ROUNDED
        
        if panel_name == "system":
            content = self._get_system_content()
        elif panel_name == "postgres":
            content = self._get_postgres_content()
        elif panel_name == "agents":
            content = self._get_agents_content()
        elif panel_name == "containers":
            content = self._get_containers_content()
        elif panel_name == "teams":
            content = self._get_teams_content()
        elif panel_name == "configs":
            content = self._get_configs_content()
        else:
            content = "Panel content"
        
        title_index = self.panels.index(panel_name)
        title = f"[{style}]{title_index + 1}. {self.panel_names[title_index]}[/{style}]"
        
        return Panel(
            content,
            title=title,
            border_style=border_style,
            box=box_style
        )
    
    def _get_system_content(self) -> str:
        """Get system panel content"""
        system = self.get_system_status()
        content = []
        content.append(f"🖥️  CPU: {system['cpu_percent']:.1f}%")
        content.append(f"🧠 Memory: {system['memory_percent']:.1f}%")
        content.append(f"💾 Disk: {system['disk_percent']:.1f}%")
        content.append(f"⚡ Load: {system['load_avg']:.2f}")
        content.append(f"⏰ Boot: {datetime.fromtimestamp(system['boot_time']).strftime('%H:%M')}")
        return "\n".join(content)
    
    def _get_postgres_content(self) -> str:
        """Get PostgreSQL panel content"""
        try:
            conn = psycopg2.connect(self.postgres_url)
            conn.close()
            status = "✅ Connected"
        except Exception as e:
            status = f"❌ {str(e)[:15]}..."
        
        content = []
        content.append(f"Status: {status}")
        content.append(f"Host: localhost:5433")
        content.append(f"DB: superagent")
        return "\\n".join(content)
    
    def _get_agents_content(self) -> str:
        """Get agents panel content"""
        agents = self.get_agent_processes()
        if not agents:
            return "❌ No agents running\\n\\nPress ENTER for\\ndetailed status"
        
        content = []
        for name, info in list(agents.items())[:4]:
            uptime_min = info['uptime'] / 60
            status_icon = "🟢" if info['status'] == 'running' else "🔴"
            content.append(f"{status_icon} {name[:12]}")
            content.append(f"   {uptime_min:.1f}m up")
        return "\\n".join(content)
    
    def _get_containers_content(self) -> str:
        """Get containers panel content"""
        if not self.docker_client:
            return "🐳 Docker unavailable\\n\\nDocker client not\\ninitialized"
        
        try:
            containers = self.docker_client.containers.list(all=True)
            sa_containers = [c for c in containers if any(label in c.name.lower() for label in ['superagent', 'postgres', 'discord'])]
            
            content = []
            for container in sa_containers[:3]:
                status_icon = "🟢" if container.status == "running" else "🔴"
                content.append(f"{status_icon} {container.name[:15]}")
                content.append(f"   {container.status}")
            return "\\n".join(content) if content else "No SA containers"
        except Exception:
            return "❌ Error reading\\ncontainers"
    
    def _get_teams_content(self) -> str:
        """Get teams panel content"""
        teams = self.agent_config_data.get('teams', {})
        if not teams:
            return "❌ No teams configured\\n\\nPress ENTER to\\nview details"
        
        content = []
        for team_name, team_info in list(teams.items())[:3]:
            agents_count = len(team_info.get('agents', []))
            content.append(f"👥 {team_name[:12]}")
            content.append(f"   {agents_count} agents")
        return "\\n".join(content)
    
    def _get_configs_content(self) -> str:
        """Get configs panel content"""
        configs = self.agent_config_data.get('agents', {})
        if not configs:
            return "❌ No configs found\\n\\nCheck agent_config.json"
        
        content = []
        for agent_name, config in list(configs.items())[:3]:
            llm_type = config.get('llm_type', 'unknown')
            api_status = self._check_api_key(llm_type)
            content.append(f"🤖 {agent_name[:10]}")
            content.append(f"   {llm_type} {api_status}")
        return "\\n".join(content)
    
    def _check_api_key(self, llm_type: str) -> str:
        """Check if API key is configured"""
        key_map = {
            "grok4": "XAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY", 
            "gemini": "GOOGLE_AI_API_KEY",
            "openai": "OPENAI_API_KEY"
        }
        key_name = key_map.get(llm_type, "")
        return "✅" if os.getenv(key_name) else "❌"
    
    def get_detailed_info(self, panel_name: str) -> str:
        """Get detailed information for popup"""
        if panel_name == "system":
            system = self.get_system_status()
            details = [
                "═══ SYSTEM DETAILS ═══",
                "",
                f"CPU Usage: {system['cpu_percent']:.1f}%",
                f"Memory Usage: {system['memory_percent']:.1f}%", 
                f"Disk Usage: {system['disk_percent']:.1f}%",
                f"Load Average: {system['load_avg']:.2f}",
                f"Boot Time: {datetime.fromtimestamp(system['boot_time']).strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "Available Memory:",
                f"  Total: {psutil.virtual_memory().total / (1024**3):.1f} GB",
                f"  Available: {psutil.virtual_memory().available / (1024**3):.1f} GB",
                "",
                "Press ESC to close"
            ]
        
        elif panel_name == "agents":
            agents = self.get_agent_processes()
            details = ["═══ AGENT DETAILS ═══", ""]
            if not agents:
                details.extend([
                    "❌ No agents currently running",
                    "",
                    "Available agent types:",
                    "  • grok4_agent (XAI Grok)",
                    "  • claude_agent (Anthropic Claude)",  
                    "  • gemini_agent (Google Gemini)",
                    "",
                    "To start agents:",
                    "  python superagent_manager.py deploy <agent_type>",
                ])
            else:
                for name, info in agents.items():
                    uptime_min = info['uptime'] / 60
                    details.extend([
                        f"🤖 Agent: {name}",
                        f"   PID: {info['pid']}",
                        f"   Uptime: {uptime_min:.1f} minutes",
                        f"   CPU: {info['cpu']:.1f}%",
                        f"   Memory: {info['memory']:.1f}%",
                        f"   Status: {info['status']}",
                        ""
                    ])
            details.append("Press ESC to close")
        
        elif panel_name == "configs":
            configs = self.agent_config_data.get('agents', {})
            details = ["═══ AGENT CONFIGURATIONS ═══", ""]
            if not configs:
                details.extend([
                    "❌ No agent configs found",
                    "",
                    "Expected file: agent_config.json",
                    "Please check configuration file",
                ])
            else:
                for agent_name, config in configs.items():
                    llm_type = config.get('llm_type', 'unknown')
                    api_key_status = self._check_api_key(llm_type)
                    details.extend([
                        f"🤖 Agent: {agent_name}",
                        f"   LLM Type: {llm_type}",
                        f"   API Key: {api_key_status}",
                        f"   Max Context: {config.get('max_context_messages', 'N/A')}",
                        f"   Max Turns: {config.get('max_turns_per_thread', 'N/A')}",
                        f"   Response Delay: {config.get('response_delay', 'N/A')}s",
                        ""
                    ])
                
                # API Key status summary
                details.extend([
                    "═══ API KEY STATUS ═══",
                    f"XAI (Grok): {'✅' if os.getenv('XAI_API_KEY') else '❌ MISSING'}",
                    f"Anthropic (Claude): {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌ MISSING'}",
                    f"Google (Gemini): {'✅' if os.getenv('GOOGLE_AI_API_KEY') else '❌ MISSING'}",
                    f"OpenAI: {'✅' if os.getenv('OPENAI_API_KEY') else '❌ MISSING'}",
                ])
            
            details.append("")
            details.append("Press ESC to close")
        
        elif panel_name == "teams":
            teams = self.agent_config_data.get('teams', {})
            details = ["═══ TEAM DETAILS ═══", ""]
            if not teams:
                details.extend([
                    "❌ No teams configured",
                    "",
                    "Teams allow grouping agents with:",
                    "  • Shared server ID",
                    "  • Default GM channel", 
                    "  • Auto-deploy settings",
                    "",
                    "Configure in agent_config.json"
                ])
            else:
                for team_name, team_info in teams.items():
                    agents = ", ".join(team_info.get('agents', []))
                    details.extend([
                        f"👥 Team: {team_name}",
                        f"   Description: {team_info.get('description', 'N/A')}",
                        f"   Agents: {agents or 'None'}",
                        f"   Server ID: {team_info.get('default_server_id', 'N/A')}",
                        f"   GM Channel: {team_info.get('gm_channel', 'N/A')}",
                        f"   Auto Deploy: {team_info.get('auto_deploy', False)}",
                        ""
                    ])
            
            details.append("Press ESC to close")
        
        else:
            details = [
                f"═══ {panel_name.upper()} DETAILS ═══",
                "",
                f"Detailed information for {panel_name}",
                "",
                "Press ESC to close"
            ]
        
        return "\\n".join(details)
    
    def create_main_layout(self) -> Layout:
        """Create main DOS-style layout"""
        layout = Layout()
        
        # Header
        header = self.create_header()
        
        # Create panels
        panels = []
        for i, panel_name in enumerate(self.panels):
            is_selected = (i == self.current_panel)
            panel = self.create_panel_content(panel_name, is_selected)
            panels.append(panel)
        
        # Footer
        footer_text = Text()
        footer_text.append("SuperAgent Multi-Bot Management System", style="bold blue")
        footer_text.append(" | ", style="dim")
        footer_text.append("Press TAB to navigate between panels", style="yellow")
        
        footer = Panel(
            Align.center(footer_text),
            style="blue",
            box=ROUNDED
        )
        
        # Split layout
        layout.split_column(
            Layout(header, size=4),
            Layout(name="main"),
            Layout(footer, size=3)
        )
        
        # Create 2x3 grid for panels
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="center"), 
            Layout(name="right")
        )
        
        layout["left"].split_column(
            Layout(panels[0]),  # System
            Layout(panels[1])   # PostgreSQL
        )
        
        layout["center"].split_column(
            Layout(panels[2]),  # Agents
            Layout(panels[3])   # Containers
        )
        
        layout["right"].split_column(
            Layout(panels[4]),  # Teams
            Layout(panels[5])   # Configs
        )
        
        return layout
    
    def create_popup_layout(self) -> Layout:
        """Create popup overlay"""
        popup = Panel(
            Text(self.popup_content, style="white"),
            title="[bold yellow]📋 Detailed Information[/bold yellow]",
            border_style="bright_yellow",
            box=DOUBLE,
            width=80,
            height=25
        )
        
        # Create overlay layout
        overlay = Layout()
        overlay.split_column(
            Layout("", size=3),
            Layout(Align.center(popup), size=25),
            Layout("", size=3)
        )
        
        return overlay
    
    async def run(self, refresh_interval: float = 1.0):
        """Run the DOS-style dashboard"""
        self.console.print("[bold green]🎮 Starting DOS-Style Dashboard...[/bold green]")
        self.console.print("[dim]TAB=Navigate | ENTER=Details | ESC=Close | Q=Quit[/dim]")
        
        await asyncio.sleep(1)
        
        with Live(auto_refresh=False, console=self.console) as live:
            try:
                while True:
                    # Handle keyboard input (non-blocking)
                    key = None
                    try:
                        # Simple key detection - not perfect but works
                        import select
                        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                            key = sys.stdin.read(1).lower()
                            self.last_key = key
                    except:
                        pass
                    
                    if key:
                        if key == 'q':
                            break
                        elif key == '\\t' or key == ' ':  # Tab or Space for navigation
                            self.current_panel = (self.current_panel + 1) % len(self.panels)
                        elif key == '\\r' or key == '\\n':  # Enter for details
                            panel_name = self.panels[self.current_panel]
                            self.popup_content = self.get_detailed_info(panel_name)
                            self.show_popup = True
                        elif key == '\\x1b':  # ESC to close popup
                            self.show_popup = False
                        elif key.isdigit():
                            # Number keys for direct panel selection
                            panel_num = int(key) - 1
                            if 0 <= panel_num < len(self.panels):
                                self.current_panel = panel_num
                    
                    # Update display
                    if self.show_popup:
                        layout = self.create_popup_layout()
                    else:
                        layout = self.create_main_layout()
                    
                    live.update(layout)
                    live.refresh()
                    
                    await asyncio.sleep(refresh_interval)
                    
            except KeyboardInterrupt:
                pass
        
        self.console.print("\\n[yellow]DOS Dashboard stopped[/yellow]")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SuperAgent DOS-Style Dashboard')
    parser.add_argument(
        '--refresh', 
        type=float, 
        default=1.0,
        help='Refresh interval in seconds (default: 1.0)'
    )
    
    args = parser.parse_args()
    
    dashboard = DOSDashboard()
    
    try:
        asyncio.run(dashboard.run(args.refresh))
    except KeyboardInterrupt:
        print("\\nDashboard stopped")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()