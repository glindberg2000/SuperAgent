#!/usr/bin/env python3
"""
Discord Bot Identity Test Suite
Tests that different Discord tokens produce different bot identities and can send messages
This ensures the multi-bot functionality works correctly and prevents regressions
"""

import os
import sys
import json
import time
import asyncio
import requests
from typing import Dict, List, Optional
import discord
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DiscordIdentityTester:
    """Test suite for Discord bot identities and multi-bot functionality"""
    
    def __init__(self):
        self.api_url = "http://localhost:9091"
        self.test_tokens = self._load_test_tokens()
        self.results = {}
        
    def _load_test_tokens(self) -> Dict[str, str]:
        """Load test tokens from environment"""
        tokens = {}
        
        # Primary test tokens (from .env)
        primary_tokens = {
            'GROK4_BOT': os.getenv('DISCORD_TOKEN_GROK'),
            'CLAUDE_BOT': os.getenv('DISCORD_TOKEN2'), 
            'GEMINI_BOT': os.getenv('DISCORD_TOKEN3'),
        }
        
        # Optional additional test tokens
        additional_tokens = {
            'TEST_BOT_1': os.getenv('DISCORD_TEST_TOKEN_1'),
            'TEST_BOT_2': os.getenv('DISCORD_TEST_TOKEN_2'),
            'TEST_BOT_3': os.getenv('DISCORD_TEST_TOKEN_3'),
        }
        
        # Add tokens that are set
        for name, token in {**primary_tokens, **additional_tokens}.items():
            if token and token.strip():
                tokens[name] = token
                
        if not tokens:
            raise ValueError("No Discord tokens found! Set DISCORD_TOKEN_GROK, DISCORD_TOKEN2, DISCORD_TOKEN3 in .env")
            
        return tokens
    
    def test_api_health(self) -> bool:
        """Test if Discord API is accessible"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Discord API Health: {health_data.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ Discord API Health Check Failed: Status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Discord API Not Accessible: {e}")
            return False
    
    async def get_bot_info_direct(self, token: str) -> Optional[Dict]:
        """Get bot info by connecting directly to Discord (not via API)"""
        try:
            intents = discord.Intents.default()
            intents.message_content = True
            client = discord.Client(intents=intents)
            
            @client.event
            async def on_ready():
                bot_info = {
                    'id': str(client.user.id),
                    'name': client.user.name,
                    'discriminator': client.user.discriminator,
                    'display_name': str(client.user),
                    'avatar_url': str(client.user.avatar.url) if client.user.avatar else None
                }
                await client.close()
                return bot_info
            
            # Connect and get info
            await client.start(token, reconnect=False)
            
        except discord.LoginFailure:
            print(f"❌ Invalid Discord token (ends with ...{token[-8:]})")
            return None
        except Exception as e:
            print(f"❌ Error getting bot info for token ...{token[-8:]}: {e}")
            return None
    
    def test_bot_identity_via_api(self, name: str, token: str) -> Dict:
        """Test bot identity through Discord HTTP API"""
        try:
            # Test both /test endpoint and /bot/info endpoint
            # First test message sending
            headers = {'Authorization': f'Bot {token}'}
            test_response = requests.post(f"{self.api_url}/test", headers=headers, json={}, timeout=10)
            
            # Then get bot identity info
            info_response = requests.post(f"{self.api_url}/bot/info", json={'token': token}, timeout=10)
            
            result = {
                'success': False,
                'bot_info': 'N/A',
                'message_id': None,
                'error': None
            }
            
            # Process test response
            if test_response.status_code == 200:
                test_result = test_response.json()
                result['success'] = test_result.get('success', False)
                result['message_id'] = test_result.get('message_id')
            
            # Process bot info response
            if info_response.status_code == 200:
                info_result = info_response.json()
                if info_result.get('success'):
                    bot_info = info_result.get('bot_info', {})
                    result['bot_info'] = bot_info.get('user', 'Unknown Bot')
            
            if not result['success'] and test_response.status_code != 200:
                result['error'] = f"Test API returned status {test_response.status_code}"
            
            return result
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Request failed: {e}"
            }
    
    async def run_comprehensive_test(self):
        """Run all tests and generate report"""
        print("🧪 Discord Bot Identity Test Suite")
        print("=" * 50)
        
        # Test API health
        if not self.test_api_health():
            print("❌ Cannot continue without Discord API")
            return False
        
        print(f"\n📋 Testing {len(self.test_tokens)} bot tokens:")
        for name in self.test_tokens.keys():
            print(f"  - {name}")
        
        print("\n🔍 Testing Bot Identities via API...")
        api_results = {}
        
        for name, token in self.test_tokens.items():
            print(f"\nTesting {name} (token ending: ...{token[-8:]})")
            result = self.test_bot_identity_via_api(name, token)
            api_results[name] = result
            
            if result['success']:
                print(f"  ✅ API Test Passed: {result['bot_info']}")
                if result['message_id']:
                    print(f"  📨 Test message sent: {result['message_id']}")
            else:
                print(f"  ❌ API Test Failed: {result['error']}")
        
        # Analyze results
        print("\n📊 Test Results Analysis:")
        successful_tests = [name for name, result in api_results.items() if result['success']]
        failed_tests = [name for name, result in api_results.items() if not result['success']]
        
        print(f"  ✅ Successful: {len(successful_tests)} ({', '.join(successful_tests)})")
        print(f"  ❌ Failed: {len(failed_tests)} ({', '.join(failed_tests)})")
        
        # Check for identity uniqueness
        bot_infos = [result['bot_info'] for result in api_results.values() if result['success'] and result['bot_info'] != 'N/A']
        unique_identities = set(bot_infos)
        
        print(f"\n🤖 Bot Identity Analysis:")
        print(f"  Total identities detected: {len(unique_identities)}")
        print(f"  Expected unique identities: {len(successful_tests)}")
        
        if len(unique_identities) == len(successful_tests) and len(unique_identities) > 1:
            print("  ✅ All bots have unique identities - MULTI-BOT WORKING!")
        elif len(unique_identities) == 1 and len(successful_tests) > 1:
            print("  ❌ ALL BOTS SHARING SAME IDENTITY - REGRESSION DETECTED!")
            print(f"     Shared identity: {list(unique_identities)[0]}")
        else:
            print("  ⚠️  Mixed results - some bots may be sharing identities")
        
        # Detailed identity breakdown
        print(f"\n🔍 Detailed Identity Breakdown:")
        for name, result in api_results.items():
            if result['success']:
                identity = result['bot_info'] if result['bot_info'] != 'N/A' else 'Unknown'
                print(f"  {name}: {identity}")
        
        # Generate recommendations
        print(f"\n💡 Recommendations:")
        if len(unique_identities) < len(successful_tests):
            print("  🔧 IMMEDIATE ACTION REQUIRED:")
            print("     - Verify each agent is using correct Discord token")
            print("     - Check token mapping in multi_agent_launcher_hybrid.py")
            print("     - Ensure Discord HTTP API returns proper bot_info")
            print("     - Test with manual Discord API calls")
        else:
            print("  ✅ Multi-bot identity system working correctly!")
        
        # Save results for future reference
        self.results = {
            'timestamp': time.time(),
            'api_results': api_results,
            'unique_identities': len(unique_identities),
            'total_tokens': len(self.test_tokens),
            'successful_tests': len(successful_tests),
            'identity_regression': len(unique_identities) == 1 and len(successful_tests) > 1
        }
        
        return len(unique_identities) == len(successful_tests) and len(unique_identities) > 1
    
    def save_test_report(self, filename: str = "discord_identity_test_report.json"):
        """Save test results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"📋 Test report saved to: {filename}")

def main():
    """Main test runner"""
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        print("🚀 Running quick identity test...")
    
    tester = DiscordIdentityTester()
    
    try:
        # Run async test
        success = asyncio.run(tester.run_comprehensive_test())
        
        # Save report
        tester.save_test_report()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()