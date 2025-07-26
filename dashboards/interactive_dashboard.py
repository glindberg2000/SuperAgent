#!/usr/bin/env python3
"""
SuperAgent Interactive CLI Dashboard
Real-time monitoring with interactive command support
"""

import asyncio
import os
import json
import subprocess
import threading
import queue
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich.align import Align
    from rich.columns import Columns
    from rich.box import ROUNDED
    from rich.prompt import Prompt
    from rich.status import Status
except ImportError:
    print("❌ Rich library not installed. Run: pip install rich")
    sys.exit(1)

from agent_dashboard import SuperAgentDashboard

class InteractiveDashboard(SuperAgentDashboard):
    def __init__(self):
        super().__init__()
        self.command_queue = queue.Queue()
        self.console = Console()
        self.running = True
        self.command_history = []
        
    def create_help_panel(self) -> Panel:
        """Create help panel with available commands"""
        help_text = Text()
        help_text.append("Interactive Commands:\n", style="bold yellow")
        help_text.append("deploy <agent>  ", style="cyan")
        help_text.append("- Deploy an agent (grok4_agent, claude_agent, etc.)\n")
        help_text.append("stop <agent>    ", style="cyan") 
        help_text.append("- Stop a running agent\n")
        help_text.append("restart <agent> ", style="cyan")
        help_text.append("- Restart an agent\n")
        help_text.append("status <agent>  ", style="cyan")
        help_text.append("- Check agent status\n")
        help_text.append("list            ", style="cyan") 
        help_text.append("- List all available agents\n")
        help_text.append("logs <agent>    ", style="cyan")
        help_text.append("- View agent logs\n")
        help_text.append("help            ", style="cyan")
        help_text.append("- Show this help\n")
        help_text.append("quit/exit       ", style="cyan")
        help_text.append("- Exit dashboard\n")
        
        return Panel(
            help_text,
            title="💡 Commands", 
            border_style="yellow",
            box=ROUNDED
        )
    
    def create_command_panel(self) -> Panel:
        """Create command input panel"""
        cmd_text = Text()
        cmd_text.append("Type a command (or 'help' for options): ", style="bold green")
        if self.command_history:
            cmd_text.append(f"\nLast: {self.command_history[-1]}", style="dim")
            
        return Panel(
            cmd_text,
            title="⌨️  Command Input",
            border_style="green", 
            box=ROUNDED
        )
    
    async def handle_command(self, command: str) -> str:
        """Handle interactive commands"""
        parts = command.strip().split()
        if not parts:
            return "No command entered"
            
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        try:
            if cmd in ['quit', 'exit']:
                self.running = False
                return "Exiting dashboard..."
                
            elif cmd == 'help':
                return "Help panel is shown on the right →"
                
            elif cmd == 'deploy':
                if not args:
                    return "Usage: deploy <agent_type> (e.g., deploy grok4_agent)"
                agent_type = args[0]
                result = subprocess.run([
                    sys.executable, 'superagent_manager.py', 'deploy', agent_type
                ], capture_output=True, text=True, cwd=Path(__file__).parent)
                return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
                
            elif cmd == 'stop':
                if not args:
                    return "Usage: stop <agent_type>"
                agent_type = args[0]
                result = subprocess.run([
                    sys.executable, 'superagent_manager.py', 'stop', agent_type
                ], capture_output=True, text=True, cwd=Path(__file__).parent)
                return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
                
            elif cmd == 'restart':
                if not args:
                    return "Usage: restart <agent_type>"
                agent_type = args[0]
                # Stop then deploy
                subprocess.run([
                    sys.executable, 'superagent_manager.py', 'stop', agent_type
                ], capture_output=True, text=True, cwd=Path(__file__).parent)
                await asyncio.sleep(2)
                result = subprocess.run([
                    sys.executable, 'superagent_manager.py', 'deploy', agent_type
                ], capture_output=True, text=True, cwd=Path(__file__).parent)
                return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
                
            elif cmd == 'status':
                if not args:
                    return "Usage: status <agent_type>"
                agent_type = args[0]
                result = subprocess.run([
                    sys.executable, 'superagent_manager.py', 'status', agent_type
                ], capture_output=True, text=True, cwd=Path(__file__).parent)
                return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
                
            elif cmd == 'list':
                result = subprocess.run([
                    sys.executable, 'superagent_manager.py', 'list'
                ], capture_output=True, text=True, cwd=Path(__file__).parent)
                return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
                
            elif cmd == 'logs':
                if not args:
                    return "Usage: logs <agent_type>"
                agent_type = args[0]
                log_file = Path(f"logs/{agent_type}.log")
                if log_file.exists():
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        return '\n'.join(lines[-10:])  # Last 10 lines
                return f"Log file not found: {log_file}"
                
            else:
                return f"Unknown command: {cmd}. Type 'help' for available commands."
                
        except Exception as e:
            return f"Command error: {str(e)}"
    
    def input_thread(self):
        """Thread to handle user input without blocking the display"""
        while self.running:
            try:
                command = input()
                if command.strip():
                    self.command_queue.put(command)
            except (EOFError, KeyboardInterrupt):
                self.running = False
                break
    
    async def run_interactive(self, refresh_interval: float = 2.0):
        """Run interactive dashboard"""
        # Start input thread
        input_thread = threading.Thread(target=self.input_thread, daemon=True)
        input_thread.start()
        
        last_command_result = ""
        
        with Live(self.create_layout(), refresh_per_second=1/refresh_interval, console=self.console) as live:
            while self.running:
                try:
                    # Check for new commands
                    try:
                        command = self.command_queue.get_nowait()
                        self.command_history.append(command)
                        last_command_result = await self.handle_command(command)
                    except queue.Empty:
                        pass
                    
                    # Create simplified layout
                    layout = Layout()
                    layout.split_row(
                        Layout(name="main", ratio=3),
                        Layout(name="sidebar", ratio=1)
                    )
                    
                    # Main content
                    main_content = Layout()
                    main_content.split_column(
                        Layout(self.create_header(), size=3),
                        Layout(name="grid", ratio=2),
                        Layout(self.create_logs_panel(), size=12),
                        Layout(self.create_command_result_panel(last_command_result), size=8)
                    )
                    
                    # Grid layout
                    grid = Layout()
                    grid.split_row(
                        Layout(name="left"),
                        Layout(name="right")
                    )
                    
                    # Left column
                    left_col = Layout()
                    left_col.split_column(
                        Layout(self.create_system_panel()),
                        Layout(self.create_agents_panel())
                    )
                    
                    # Right column  
                    right_col = Layout()
                    right_col.split_column(
                        Layout(self.create_postgres_panel()),
                        Layout(self.create_containers_panel())
                    )
                    
                    grid["left"].update(left_col)
                    grid["right"].update(right_col)
                    main_content["grid"].update(grid)
                    layout["main"].update(main_content)
                    
                    # Sidebar
                    sidebar = Layout()
                    sidebar.split_column(
                        Layout(self.create_help_panel(), size=20),
                        Layout(self.create_command_panel(), size=5)
                    )
                    layout["sidebar"].update(sidebar)
                    
                    live.update(layout)
                    await asyncio.sleep(refresh_interval)
                    
                except KeyboardInterrupt:
                    self.running = False
                    break
    
    def create_command_result_panel(self, result: str) -> Panel:
        """Create panel to show command results"""
        if not result:
            result = "No recent command output"
            
        # Truncate very long results
        if len(result) > 1000:
            result = result[:1000] + "\n... (truncated)"
            
        return Panel(
            Text(result, style="white"),
            title="📤 Command Output",
            border_style="blue",
            box=ROUNDED
        )

def main():
    """Main entry point"""
    console = Console()
    
    try:
        console.print(Panel(
            "[bold green]SuperAgent Interactive Dashboard[/bold green]\n"
            "Real-time monitoring with command support\n\n"
            "[yellow]💡 Type commands in the terminal while dashboard runs[/yellow]\n"
            "[dim]Press Ctrl+C to exit[/dim]",
            title="🚀 Starting Dashboard",
            border_style="green"
        ))
        
        dashboard = InteractiveDashboard()
        asyncio.run(dashboard.run_interactive())
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Dashboard error: {e}[/red]")

if __name__ == "__main__":
    main()