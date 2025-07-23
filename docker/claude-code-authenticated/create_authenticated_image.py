#!/usr/bin/env python3
"""
Create a pre-authenticated Claude Code container image
This requires manual OAuth login but automates the rest
"""

import docker
import subprocess
import time
import sys

def create_authenticated_image():
    client = docker.from_env()
    
    print("🚀 Creating pre-authenticated Claude Code container...")
    
    # Start an interactive container
    container = client.containers.run(
        "deepworks/claude-code:latest",
        name="claude-auth-setup",
        detach=True,
        tty=True,
        stdin_open=True,
        volumes={
            "/Users/greg/repos/SuperAgent": {"bind": "/workspace", "mode": "rw"}
        },
        working_dir="/workspace",
        command="/bin/bash"
    )
    
    print(f"✅ Container started: {container.id[:12]}")
    print("\n" + "="*60)
    print("📝 MANUAL AUTHENTICATION REQUIRED")
    print("="*60)
    print("\nRun these commands in a new terminal:\n")
    print(f"1. docker exec -it claude-auth-setup /bin/bash")
    print("2. claude login")
    print("3. Choose 'Pro or Max plan' option")
    print("4. Complete the browser authentication")
    print("5. Test with: claude --print 'Hello from authenticated Claude'")
    print("6. Exit the container shell (type 'exit')")
    print("\n" + "="*60)
    
    input("\n🔔 Press ENTER after completing authentication...")
    
    # Verify authentication
    print("\n🔍 Verifying authentication...")
    exec_result = container.exec_run("claude config get auth.type", stdout=True, stderr=True)
    output = exec_result.output.decode()
    
    if "oauth" in output.lower() or exec_result.exit_code == 0:
        print("✅ Authentication verified!")
    else:
        print(f"⚠️  Authentication status unclear: {output}")
        proceed = input("Continue anyway? (y/n): ")
        if proceed.lower() != 'y':
            container.stop()
            container.remove()
            return
    
    # Commit the authenticated container
    print("\n📦 Creating authenticated image...")
    image = container.commit(
        repository="superagent/claude-code-authenticated",
        tag="latest",
        message="Pre-authenticated Claude Code with Max plan",
        author="SuperAgent"
    )
    
    print(f"✅ Created image: {image.tags[0]}")
    
    # Clean up
    container.stop()
    container.remove()
    print("🧹 Cleaned up temporary container")
    
    # Update orchestrator config
    print("\n📝 Update your orchestrator to use: superagent/claude-code-authenticated:latest")
    print("   Instead of: deepworks/claude-code:latest")
    
    print("\n🎉 Done! Your authenticated Claude Code image is ready!")

if __name__ == "__main__":
    try:
        create_authenticated_image()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)