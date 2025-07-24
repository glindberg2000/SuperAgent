#!/usr/bin/env python3
"""
Test script for AI DevOps Agent
Quick validation that all components are working
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add control_plane to path
sys.path.append(str(Path(__file__).parent / 'control_plane'))

from ai_devops_agent import AIDevOpsAgent

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('test_ai_devops')

async def test_basic_functionality():
    """Test basic DevOps agent functionality"""
    logger.info("🧪 Starting AI DevOps Agent tests...")
    
    try:
        # Test 1: Agent initialization
        logger.info("Test 1: Initializing AI DevOps Agent...")
        agent = AIDevOpsAgent()
        logger.info("✅ Agent initialized successfully")
        
        # Test 2: System knowledge
        logger.info("Test 2: Checking system knowledge...")
        knowledge = agent.system_knowledge
        assert "SuperAgent" in knowledge
        assert "Docker" in knowledge
        logger.info("✅ System knowledge loaded")
        
        # Test 3: Docker connection
        logger.info("Test 3: Testing Docker connection...")
        try:
            agent.docker_client.ping()
            logger.info("✅ Docker connection successful")
        except Exception as e:
            logger.warning(f"⚠️ Docker connection failed: {e}")
        
        # Test 4: Configuration loading
        logger.info("Test 4: Testing configuration...")
        config = agent.config
        assert config['discord_token_env'] == 'DISCORD_TOKEN_DEVOPS'
        logger.info("✅ Configuration loaded correctly")
        
        # Test 5: Health check
        logger.info("Test 5: Testing health check...")
        health = await agent._comprehensive_health_check()
        logger.info(f"✅ Health check completed - Docker: {health.docker_healthy}")
        
        # Test 6: System state
        logger.info("Test 6: Testing system state...")
        state = await agent._get_current_system_state()
        assert 'timestamp' in state
        assert 'system' in state
        logger.info("✅ System state retrieval working")
        
        # Test 7: Environment variables
        logger.info("Test 7: Checking environment variables...")
        devops_token = os.getenv('DISCORD_TOKEN_DEVOPS')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        
        if devops_token:
            logger.info("✅ DISCORD_TOKEN_DEVOPS found")
        else:
            logger.warning("⚠️ DISCORD_TOKEN_DEVOPS not set")
        
        if anthropic_key:
            logger.info("✅ ANTHROPIC_API_KEY found")
        else:
            logger.warning("⚠️ ANTHROPIC_API_KEY not set")
        
        logger.info("🎉 All basic tests completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_claude_integration():
    """Test Claude LLM integration"""
    logger.info("🧪 Testing Claude LLM integration...")
    
    try:
        agent = AIDevOpsAgent()
        
        # Test Claude API connection
        if not os.getenv('ANTHROPIC_API_KEY'):
            logger.warning("⚠️ Skipping Claude test - no API key")
            return True
        
        # Simple test prompt
        test_prompt = "Respond with 'DevOps Agent Test Successful' if you can read this."
        
        response = await agent.claude.messages.create(
            model=agent.config['claude_model'],
            max_tokens=100,
            messages=[{"role": "user", "content": test_prompt}]
        )
        
        response_text = response.content[0].text
        logger.info(f"Claude response: {response_text}")
        
        if "DevOps Agent Test Successful" in response_text:
            logger.info("✅ Claude integration working correctly")
            return True
        else:
            logger.warning("⚠️ Claude response unexpected")
            return False
            
    except Exception as e:
        logger.error(f"❌ Claude integration test failed: {e}")
        return False

def test_dependencies():
    """Test that all required dependencies are available"""
    logger.info("🧪 Testing dependencies...")
    
    required_modules = [
        'anthropic',
        'discord',
        'docker',
        'psutil',
        'watchdog',
        'yaml'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"✅ {module} available")
        except ImportError:
            missing.append(module)
            logger.error(f"❌ {module} missing")
    
    if missing:
        logger.error(f"Missing dependencies: {missing}")
        logger.info("Install with: pip install -r control_plane/requirements.txt")
        return False
    
    logger.info("✅ All dependencies available")
    return True

async def main():
    """Run all tests"""
    logger.info("🚀 Starting AI DevOps Agent test suite...")
    
    # Test dependencies first
    if not test_dependencies():
        logger.error("❌ Dependency test failed - cannot continue")
        return False
    
    # Test basic functionality
    basic_success = await test_basic_functionality()
    
    # Test Claude integration
    claude_success = await test_claude_integration()
    
    # Summary
    if basic_success and claude_success:
        logger.info("🎉 All tests passed! AI DevOps Agent is ready to deploy.")
        return True
    else:
        logger.error("❌ Some tests failed. Check logs above.")
        return False

if __name__ == "__main__":
    # Ensure we have required directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('configs', exist_ok=True)
    
    # Run tests
    success = asyncio.run(main())
    
    if success:
        print("\n🎉 Ready to start AI DevOps Agent!")
        print("Run: python control_plane/ai_devops_agent.py")
    else:
        print("\n❌ Fix issues above before starting the agent.")
        sys.exit(1)