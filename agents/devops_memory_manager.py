#!/usr/bin/env python3
"""
DevOps Memory Manager
Leverages existing PostgreSQL + pgvector infrastructure for DevOps operations
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from memory_client import MemoryClient

logger = logging.getLogger(__name__)


class DevOpsMemoryManager:
    """DevOps-specific memory management using existing PostgreSQL system"""

    def __init__(self, memory_client: MemoryClient):
        self.client = memory_client
        logger.info("Initialized DevOps Memory Manager with PostgreSQL backend")

    async def store_deployment_memory(self, deployment_data: Dict) -> int:
        """Store deployment operation with semantic embedding"""
        content = f"Deployed {deployment_data['agent_type']} agent {deployment_data['name']} for team {deployment_data.get('team', 'default')}"

        return await self.client.store_memory(
            agent_id="devops_agent",
            content=content,
            metadata={
                'operation_type': 'deployment',
                'agent_target': deployment_data['name'],
                'agent_type': deployment_data['agent_type'],
                'team': deployment_data.get('team', 'default'),
                'deployment_type': deployment_data.get('deployment_type', 'unknown'),
                'timestamp': datetime.now().isoformat(),
                'system_state': deployment_data
            }
        )

    async def store_conversation_memory(self, conversation_data: Dict) -> int:
        """Store DevOps conversation with context"""
        content = f"User {conversation_data['username']}: {conversation_data['message_content']}"
        if conversation_data.get('response_content'):
            content += f" | DevOps Response: {conversation_data['response_content']}"

        return await self.client.store_memory(
            agent_id="devops_agent",
            content=content,
            metadata={
                'operation_type': 'conversation',
                'channel_id': conversation_data['channel_id'],
                'user_id': conversation_data['user_id'],
                'username': conversation_data['username'],
                'thread_id': conversation_data.get('thread_id'),
                'timestamp': conversation_data.get('timestamp', datetime.now().isoformat()),
                'conversation_type': conversation_data.get('conversation_type', 'general')
            }
        )

    async def store_system_event(self, event_type: str, event_data: Dict, severity: str = 'info') -> int:
        """Store system events for pattern analysis"""
        content = f"{event_type}: {event_data.get('description', 'System event occurred')}"

        return await self.client.store_memory(
            agent_id="devops_agent",
            content=content,
            metadata={
                'operation_type': 'system_event',
                'event_type': event_type,
                'severity': severity,
                'timestamp': datetime.now().isoformat(),
                'event_data': event_data
            }
        )

    async def search_deployment_history(self, query: str, limit: int = 5) -> List[Dict]:
        """Search deployment history using vector similarity"""
        memories = await self.client.search_memories(
            query=query,
            agent_id="devops_agent",
            limit=limit
        )

        # Filter for deployment operations
        deployment_memories = []
        for memory in memories:
            metadata = memory.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    continue

            if metadata.get('operation_type') == 'deployment':
                deployment_memories.append(memory)

        return deployment_memories

    async def search_conversation_history(self, query: str, limit: int = 10) -> List[Dict]:
        """Search conversation history using vector similarity"""
        memories = await self.client.search_memories(
            query=query,
            agent_id="devops_agent",
            limit=limit
        )

        # Filter for conversation operations
        conversation_memories = []
        for memory in memories:
            metadata = memory.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    continue

            if metadata.get('operation_type') == 'conversation':
                conversation_memories.append(memory)

        return conversation_memories

    async def analyze_failure_patterns(self, agent_name: str) -> List[Dict]:
        """Use vector search to find similar failure patterns"""
        query = f"failure error problem issue {agent_name} down crashed stopped"

        memories = await self.client.search_memories(
            query=query,
            agent_id="devops_agent",
            limit=15
        )

        # Filter for system events with error severity
        failure_patterns = []
        for memory in memories:
            metadata = memory.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    continue

            # Include system events or conversations mentioning failures
            operation_type = metadata.get('operation_type')
            severity = metadata.get('severity', 'info')

            if (operation_type == 'system_event' and severity in ['error', 'warning']) or \
               (operation_type == 'conversation' and any(word in memory.get('content', '').lower()
                                                       for word in ['error', 'failure', 'problem', 'issue', 'down'])):
                failure_patterns.append(memory)

        return failure_patterns

    async def get_system_insights(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get system insights using vector analysis"""

        # Search for recent system activity
        recent_activity = await self.client.search_memories(
            query="deployment system status health performance",
            agent_id="devops_agent",
            limit=20
        )

        # Analyze patterns
        insights = {
            'total_memories': len(recent_activity),
            'deployment_count': 0,
            'conversation_count': 0,
            'system_event_count': 0,
            'error_count': 0,
            'recent_deployments': [],
            'common_issues': []
        }

        for memory in recent_activity:
            metadata = memory.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    continue

            operation_type = metadata.get('operation_type', 'unknown')

            if operation_type == 'deployment':
                insights['deployment_count'] += 1
                insights['recent_deployments'].append({
                    'agent_name': metadata.get('agent_target', 'unknown'),
                    'agent_type': metadata.get('agent_type', 'unknown'),
                    'team': metadata.get('team', 'default'),
                    'timestamp': metadata.get('timestamp', 'unknown')
                })
            elif operation_type == 'conversation':
                insights['conversation_count'] += 1
            elif operation_type == 'system_event':
                insights['system_event_count'] += 1
                if metadata.get('severity') == 'error':
                    insights['error_count'] += 1

        return insights

    async def get_agent_history(self, agent_name: str, limit: int = 10) -> List[Dict]:
        """Get specific agent's deployment and operational history"""
        query = f"agent {agent_name} deployment status"

        memories = await self.client.search_memories(
            query=query,
            agent_id="devops_agent",
            limit=limit
        )

        # Filter and sort by relevance to the specific agent
        agent_memories = []
        for memory in memories:
            content = memory.get('content', '').lower()
            metadata = memory.get('metadata', {})

            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    continue

            # Check if memory relates to this specific agent
            if (agent_name.lower() in content or
                metadata.get('agent_target', '').lower() == agent_name.lower()):
                agent_memories.append(memory)

        return agent_memories[:limit]
