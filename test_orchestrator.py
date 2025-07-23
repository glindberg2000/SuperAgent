#!/usr/bin/env python3
"""
Test the MVP orchestrator with minimal setup
"""

import os
import sys
from orchestrator_mvp import MVPOrchestrator

def test_orchestrator():
    """Test orchestrator with minimal configuration"""
    
    # Set up minimal environment
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    os.environ["DISCORD_TOKEN"] = "test-token"
    os.environ["DOCKER_HOST"] = "unix:///Users/greg/.colima/default/docker.sock"
    
    try:
        print("🧪 Testing MVP Orchestrator...")
        
        # Create orchestrator
        orchestrator = MVPOrchestrator()
        
        # Check health
        health = orchestrator.health_check()
        print(f"📊 Health Status: {health}")
        
        if not all(health.values()):
            print("❌ Some services are not healthy!")
            return False
        
        # Test spawning a simple agent
        print("🚀 Testing agent spawn...")
        try:
            container_id = orchestrator.spawn_agent(
                name="test-agent",
                workspace_path="/Users/greg/repos/SuperAgent",  # This repo
                discord_token="test-token-123",
                personality="Test agent for MVP validation"
            )
            print(f"✅ Test agent spawned: {container_id[:12]}")
            
            # List agents
            agents = orchestrator.list_agents()
            print(f"📋 Active agents: {list(agents.keys())}")
            
            # Get logs
            logs = orchestrator.get_agent_logs("test-agent", lines=5)
            print(f"📋 Recent logs:\n{logs[:200]}...")
            
            # Clean up
            print("🧹 Cleaning up test agent...")
            orchestrator.stop_agent("test-agent")
            orchestrator.remove_agent("test-agent")
            
            print("✅ Orchestrator test completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Agent spawn test failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Orchestrator test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_orchestrator()
    sys.exit(0 if success else 1)