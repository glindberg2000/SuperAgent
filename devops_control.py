#!/usr/bin/env python3
"""
DevOps Agent Process Control
Manages the MCP DevOps Agent lifecycle with proper process control
"""

import os
import sys
import signal
import subprocess
import time
from pathlib import Path

def get_devops_processes():
    """Find all running DevOps agent processes"""
    try:
        # Use pgrep to find processes
        result = subprocess.run(['pgrep', '-f', 'conversational_devops|start.*devops'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = [int(pid.strip()) for pid in result.stdout.strip().split('\n') if pid.strip()]
            return pids
        return []
    except Exception as e:
        print(f"Error finding processes: {e}")
        return []

def stop_all_devops_agents():
    """Stop all running DevOps agent instances"""
    print("🔍 Checking for running DevOps agents...")

    pids = get_devops_processes()
    if not pids:
        print("✅ No DevOps agents currently running")
        return True

    print(f"🛑 Found {len(pids)} running DevOps agent(s): {pids}")

    for pid in pids:
        try:
            print(f"   Stopping process {pid}...")
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)

            # Check if still running
            try:
                os.kill(pid, 0)  # Check if process exists
                print(f"   Force killing process {pid}...")
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                print(f"   ✅ Process {pid} stopped")

        except ProcessLookupError:
            print(f"   ✅ Process {pid} already stopped")
        except Exception as e:
            print(f"   ❌ Error stopping process {pid}: {e}")

    # Final check
    remaining = get_devops_processes()
    if remaining:
        print(f"⚠️ Warning: {len(remaining)} processes still running: {remaining}")
        return False
    else:
        print("✅ All DevOps agents stopped successfully")
        return True

def start_devops_agent():
    """Start the MCP DevOps agent"""
    print("🚀 Starting MCP DevOps Agent...")

    # First ensure no other instances are running
    if not stop_all_devops_agents():
        print("❌ Failed to stop existing instances")
        return False

    # Start the new agent
    script_path = Path(__file__).parent / "launchers" / "start_conversational_devops.py"

    try:
        # Use virtual environment Python
        venv_python = Path(__file__).parent / ".venv" / "bin" / "python"
        if venv_python.exists():
            python_cmd = str(venv_python)
            print(f"   Executing: {python_cmd} {script_path}")
        else:
            python_cmd = sys.executable
            print(f"   Executing: {python_cmd} {script_path} (no venv found)")

        process = subprocess.Popen([
            python_cmd, str(script_path)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True)

        print(f"✅ Started DevOps agent with PID: {process.pid}")
        print("📝 Showing startup logs (Ctrl+C to stop viewing, agent continues running):")
        print("-" * 60)

        try:
            # Show initial logs
            for _ in range(20):  # Show first 20 lines of output
                line = process.stdout.readline()
                if line:
                    print(line.rstrip())
                else:
                    break
                time.sleep(0.1)

            print("-" * 60)
            print(f"🎯 DevOps agent is running with PID: {process.pid}")
            print("   Use 'python devops_control.py status' to check status")
            print("   Use 'python devops_control.py stop' to stop the agent")

        except KeyboardInterrupt:
            print("\n👋 Stopped viewing logs. Agent continues running in background.")

        return True

    except Exception as e:
        print(f"❌ Failed to start DevOps agent: {e}")
        return False

def status_devops_agents():
    """Show status of DevOps agents"""
    print("🔍 DevOps Agent Status:")

    pids = get_devops_processes()
    if not pids:
        print("   📴 No DevOps agents currently running")
        return

    print(f"   🟢 {len(pids)} DevOps agent(s) running:")

    for pid in pids:
        try:
            # Get process info
            result = subprocess.run(['ps', '-p', str(pid), '-o', 'pid,etime,command'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    print(f"     PID {pid}: {lines[1]}")
        except Exception as e:
            print(f"     PID {pid}: (error getting details: {e})")

def main():
    """Main control interface"""
    if len(sys.argv) < 2:
        print("🤖 SuperAgent DevOps Agent Control")
        print("=" * 40)
        print("Usage:")
        print("  python devops_control.py start   - Start the DevOps agent")
        print("  python devops_control.py stop    - Stop all DevOps agents")
        print("  python devops_control.py restart - Restart the DevOps agent")
        print("  python devops_control.py status  - Show agent status")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "start":
        start_devops_agent()
    elif command == "stop":
        stop_all_devops_agents()
    elif command == "restart":
        print("🔄 Restarting DevOps agent...")
        stop_all_devops_agents()
        time.sleep(2)
        start_devops_agent()
    elif command == "status":
        status_devops_agents()
    else:
        print(f"❌ Unknown command: {command}")
        print("Use: start, stop, restart, or status")
        sys.exit(1)

if __name__ == "__main__":
    main()
