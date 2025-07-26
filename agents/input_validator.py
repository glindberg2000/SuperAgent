#!/usr/bin/env python3
"""
Input Validator and Sanitizer
Comprehensive input validation and sanitization for all user inputs
Prevents injection attacks and ensures data integrity
"""

import re
import html
import unicodedata
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation strictness levels"""
    STRICT = "strict"      # Maximum security, restrictive
    MODERATE = "moderate"  # Balanced security and usability
    PERMISSIVE = "permissive"  # Minimal validation for user-friendly content


@dataclass
class ValidationResult:
    """Result of input validation"""
    is_valid: bool
    sanitized_value: Any
    original_value: Any
    errors: List[str]
    warnings: List[str]


class InputValidator:
    """
    Comprehensive input validator and sanitizer
    Handles all types of user inputs with configurable security levels
    """

    def __init__(self, default_level: ValidationLevel = ValidationLevel.MODERATE):
        self.default_level = default_level

        # Define dangerous patterns
        self.dangerous_patterns = [
            # Code injection patterns
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__\s*\(',
            r'compile\s*\(',
            r'getattr\s*\(',
            r'setattr\s*\(',
            r'delattr\s*\(',
            r'vars\s*\(',
            r'globals\s*\(',
            r'locals\s*\(',

            # Command injection patterns
            r';\s*rm\s',
            r';\s*cat\s',
            r';\s*ls\s',
            r';\s*pwd\s',
            r';\s*whoami\s',
            r'&&\s*rm\s',
            r'\|\s*rm\s',
            r'\|\s*nc\s',
            r'\|\s*netcat\s',
            r'\|\s*curl\s',
            r'\|\s*wget\s',
            r'\|\s*ssh\s',
            r'\|\s*scp\s',
            r'nc\s+[\w\.]',
            r'netcat\s+[\w\.]',
            r'curl\s+[\w\.]',
            r'wget\s+[\w\.]',
            r'`.*`',
            r'\$\(.*\)',

            # SQL injection patterns
            r"'.*OR.*'",
            r'".*OR.*"',
            r';\s*DROP\s',
            r';\s*DELETE\s',
            r';\s*UPDATE\s',
            r';\s*INSERT\s',
            r'UNION\s+SELECT',

            # JavaScript injection patterns
            r'<script.*?>',
            r'javascript:',
            r'on\w+\s*=',
            r'alert\s*\(',
            r'confirm\s*\(',
            r'prompt\s*\(',

            # Path traversal patterns
            r'\.\./.*',
            r'\.\.\\.*',
            r'/etc/passwd',
            r'/etc/shadow',
            r'\\windows\\system32',

            # Network patterns
            r'file://',
            r'ftp://',
            r'ldap://',

            # Docker escape patterns
            r'docker\s+run',
            r'docker\s+exec',
            r'kubectl\s+exec',
            r'/proc/self/environ',

            # Environment variable access
            r'\$\{.*\}',
            r'process\.env\.',
            r'os\.environ',

            # Suspicious file operations
            r'open\s*\([\'"]/(etc|proc|sys|dev)/',
            r'writeFile\s*\(',
            r'unlinkSync\s*\(',
        ]

        # Compile patterns for performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.dangerous_patterns]

        logger.info(f"🛡️ Input validator initialized with {len(self.compiled_patterns)} security patterns")

    def validate_string(self, value: str, field_name: str = "input",
                       max_length: int = 10000, level: Optional[ValidationLevel] = None) -> ValidationResult:
        """
        Validate and sanitize string input

        Args:
            value: Input string to validate
            field_name: Name of the field for error messages
            max_length: Maximum allowed length
            level: Validation strictness level

        Returns:
            ValidationResult with validation status and sanitized value
        """

        level = level or self.default_level
        errors = []
        warnings = []

        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                sanitized_value="",
                original_value=value,
                errors=[f"{field_name} must be a string"],
                warnings=[]
            )

        # Length validation
        if len(value) > max_length:
            errors.append(f"{field_name} exceeds maximum length of {max_length} characters")

        # Check for dangerous patterns
        for pattern in self.compiled_patterns:
            if pattern.search(value):
                if level == ValidationLevel.STRICT:
                    errors.append(f"{field_name} contains potentially dangerous content: {pattern.pattern[:50]}...")
                else:
                    warnings.append(f"{field_name} contains suspicious pattern: {pattern.pattern[:50]}...")

        # Sanitization
        sanitized = self._sanitize_string(value, level)

        # Check for significant changes during sanitization
        if len(sanitized) < len(value) * 0.8:  # More than 20% removed
            warnings.append(f"{field_name} was significantly modified during sanitization")

        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=sanitized,
            original_value=value,
            errors=errors,
            warnings=warnings
        )

    def _sanitize_string(self, value: str, level: ValidationLevel) -> str:
        """Sanitize string input based on validation level"""

        # Basic Unicode normalization
        sanitized = unicodedata.normalize('NFKD', value)

        # Remove null bytes and control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\t\n\r')

        if level == ValidationLevel.STRICT:
            # Strict mode: aggressive sanitization

            # HTML escape
            sanitized = html.escape(sanitized)

            # Remove potential code execution patterns
            for pattern in self.compiled_patterns:
                sanitized = pattern.sub('[REMOVED]', sanitized)

            # Remove excessive whitespace
            sanitized = re.sub(r'\s+', ' ', sanitized).strip()

            # Limit special characters
            sanitized = re.sub(r'[<>"\';{}()\\|`$]', '', sanitized)

        elif level == ValidationLevel.MODERATE:
            # Moderate mode: balanced sanitization

            # Escape HTML entities but preserve some formatting
            sanitized = html.escape(sanitized, quote=False)

            # Remove only the most dangerous patterns
            dangerous_code_patterns = [
                r'eval\s*\(',
                r'exec\s*\(',
                r'__import__\s*\(',
                r'<script.*?>',
                r'javascript:',
            ]

            for pattern in dangerous_code_patterns:
                sanitized = re.sub(pattern, '[BLOCKED]', sanitized, flags=re.IGNORECASE)

            # Clean up excessive whitespace
            sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        else:  # PERMISSIVE
            # Permissive mode: minimal sanitization for user-friendly content

            # Only remove null bytes and excessive control characters
            sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)

            # Basic cleanup
            sanitized = sanitized.strip()

        return sanitized

    def validate_agent_name(self, name: str) -> ValidationResult:
        """Validate agent name with specific rules"""

        errors = []
        warnings = []

        # Basic string validation
        result = self.validate_string(name, "agent_name", max_length=100, level=ValidationLevel.MODERATE)

        if not result.is_valid:
            return result

        sanitized = result.sanitized_value

        # Agent-specific validation
        if not sanitized:
            errors.append("Agent name cannot be empty")
        elif len(sanitized) < 2:
            errors.append("Agent name must be at least 2 characters")
        elif not re.match(r'^[a-zA-Z0-9_\-\s]+$', sanitized):
            errors.append("Agent name can only contain letters, numbers, spaces, hyphens, and underscores")
        elif sanitized.lower() in ['root', 'admin', 'system', 'bot', 'null', 'undefined', 'test']:
            warnings.append(f"Agent name '{sanitized}' is a reserved word")

        # Clean up the name
        final_name = re.sub(r'[^a-zA-Z0-9_\-\s]', '', sanitized)
        final_name = re.sub(r'\s+', '_', final_name.strip())
        final_name = final_name[:50]  # Reasonable length limit

        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=final_name,
            original_value=name,
            errors=errors,
            warnings=warnings
        )

    def validate_team_name(self, team: str) -> ValidationResult:
        """Validate team name with specific rules"""

        result = self.validate_string(team, "team_name", max_length=50, level=ValidationLevel.MODERATE)

        if not result.is_valid:
            return result

        sanitized = result.sanitized_value
        errors = []
        warnings = []

        # Team-specific validation
        if sanitized and not re.match(r'^[a-zA-Z0-9_\-\s]+$', sanitized):
            errors.append("Team name can only contain letters, numbers, spaces, hyphens, and underscores")

        # Clean up team name
        if sanitized:
            final_team = re.sub(r'[^a-zA-Z0-9_\-\s]', '', sanitized)
            final_team = re.sub(r'\s+', '_', final_team.strip().lower())
        else:
            final_team = "default"

        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=final_team,
            original_value=team,
            errors=errors,
            warnings=warnings
        )

    def validate_agent_type(self, agent_type: str) -> ValidationResult:
        """Validate agent type against allowed values"""

        allowed_types = [
            'grok4', 'grok4_agent',
            'claude', 'claude_agent',
            'gemini', 'gemini_agent',
            'openai', 'o3_agent',
            'fullstackdev', 'fullstack',
            'coderdev1', 'coder',
            'coderdev2',
            'manager', 'devops'
        ]

        result = self.validate_string(agent_type, "agent_type", max_length=50, level=ValidationLevel.STRICT)

        if not result.is_valid:
            return result

        sanitized = result.sanitized_value.lower()
        errors = []

        if sanitized not in allowed_types:
            errors.append(f"Agent type '{sanitized}' is not supported. Allowed types: {', '.join(allowed_types)}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=sanitized,
            original_value=agent_type,
            errors=errors,
            warnings=[]
        )

    def validate_deployment_type(self, deployment_type: str) -> ValidationResult:
        """Validate deployment type against allowed values"""

        allowed_types = ['process', 'container', 'isolated_container']

        result = self.validate_string(deployment_type, "deployment_type", max_length=30, level=ValidationLevel.STRICT)

        if not result.is_valid:
            return result

        sanitized = result.sanitized_value.lower()
        errors = []

        if sanitized not in allowed_types:
            errors.append(f"Deployment type '{sanitized}' is not supported. Allowed types: {', '.join(allowed_types)}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=sanitized,
            original_value=deployment_type,
            errors=errors,
            warnings=[]
        )

    def validate_discord_message(self, content: str) -> ValidationResult:
        """Validate Discord message content"""

        # Discord messages can be more permissive but still need security
        result = self.validate_string(content, "message_content", max_length=2000, level=ValidationLevel.PERMISSIVE)

        if not result.is_valid:
            return result

        # Check for Discord-specific issues
        warnings = result.warnings.copy()

        # Check for excessive mentions or spam patterns
        mention_count = len(re.findall(r'<@[!&]?\d+>', result.sanitized_value))
        if mention_count > 10:
            warnings.append("Message contains excessive mentions")

        # Check for potential Discord formatting abuse
        if '```' in result.sanitized_value and result.sanitized_value.count('```') % 2 != 0:
            warnings.append("Unmatched code block formatting")

        return ValidationResult(
            is_valid=result.is_valid,
            sanitized_value=result.sanitized_value,
            original_value=content,
            errors=result.errors,
            warnings=warnings
        )

    def validate_json_data(self, data: str, field_name: str = "json_data") -> ValidationResult:
        """Validate JSON data input"""

        result = self.validate_string(data, field_name, max_length=50000, level=ValidationLevel.STRICT)

        if not result.is_valid:
            return result

        errors = result.errors.copy()

        # Try to parse JSON
        try:
            import json
            parsed = json.loads(result.sanitized_value)

            # Check for dangerous keys in JSON
            dangerous_keys = ['__proto__', 'constructor', 'prototype', 'eval', 'exec']

            def check_dangerous_keys(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key in dangerous_keys:
                            errors.append(f"Dangerous key '{key}' found at {path}")
                        check_dangerous_keys(value, f"{path}.{key}")
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        check_dangerous_keys(item, f"{path}[{i}]")

            check_dangerous_keys(parsed)

        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON format: {str(e)}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=result.sanitized_value,
            original_value=data,
            errors=errors,
            warnings=result.warnings
        )

    def validate_environment_variables(self, env_vars: Dict[str, str]) -> ValidationResult:
        """Validate environment variables dictionary"""

        errors = []
        warnings = []
        sanitized_env = {}

        # Dangerous environment variable names
        dangerous_env_names = [
            'PATH', 'LD_LIBRARY_PATH', 'LD_PRELOAD', 'PYTHONPATH',
            'HOME', 'USER', 'SHELL', 'TERM', 'PWD',
            'DOCKER_HOST', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'
        ]

        for key, value in env_vars.items():
            # Validate key
            key_result = self.validate_string(key, f"env_key_{key}", max_length=100, level=ValidationLevel.STRICT)
            if not key_result.is_valid:
                errors.extend(key_result.errors)
                continue

            clean_key = key_result.sanitized_value

            # Check for dangerous environment variables
            if clean_key in dangerous_env_names:
                warnings.append(f"Environment variable '{clean_key}' is potentially dangerous")

            # Validate value
            value_result = self.validate_string(value, f"env_value_{key}", max_length=1000, level=ValidationLevel.MODERATE)
            if not value_result.is_valid:
                errors.extend(value_result.errors)
                continue

            sanitized_env[clean_key] = value_result.sanitized_value

        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=sanitized_env,
            original_value=env_vars,
            errors=errors,
            warnings=warnings
        )

    def validate_file_path(self, path: str) -> ValidationResult:
        """Validate file path for safety"""

        result = self.validate_string(path, "file_path", max_length=500, level=ValidationLevel.STRICT)

        if not result.is_valid:
            return result

        errors = result.errors.copy()
        warnings = result.warnings.copy()

        sanitized_path = result.sanitized_value

        # Check for path traversal
        if '..' in sanitized_path:
            errors.append("Path traversal not allowed")

        # Check for absolute paths to sensitive areas
        dangerous_paths = [
            '/etc/', '/proc/', '/sys/', '/dev/',
            '/root/', '/boot/', '/usr/bin/', '/usr/sbin/',
            'C:\\Windows\\', 'C:\\Program Files\\',
        ]

        for dangerous in dangerous_paths:
            if sanitized_path.startswith(dangerous):
                errors.append(f"Access to system path '{dangerous}' not allowed")

        # Ensure path doesn't start with /
        if sanitized_path.startswith('/'):
            warnings.append("Absolute paths are discouraged, consider using relative paths")

        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_value=sanitized_path,
            original_value=path,
            errors=errors,
            warnings=warnings
        )

    def validate_all_inputs(self, inputs: Dict[str, Any]) -> Dict[str, ValidationResult]:
        """Validate multiple inputs at once"""

        results = {}

        for field, value in inputs.items():
            if field.endswith('_name') or field == 'name':
                if 'agent' in field:
                    results[field] = self.validate_agent_name(str(value))
                elif 'team' in field:
                    results[field] = self.validate_team_name(str(value))
                else:
                    results[field] = self.validate_string(str(value), field)

            elif field in ['agent_type', 'type']:
                results[field] = self.validate_agent_type(str(value))

            elif field in ['deployment_type']:
                results[field] = self.validate_deployment_type(str(value))

            elif field in ['content', 'message', 'message_content']:
                results[field] = self.validate_discord_message(str(value))

            elif field in ['channel_id', 'user_id', 'guild_id', 'server_id']:
                # Discord IDs should be validated strictly to prevent path traversal
                results[field] = self.validate_string(str(value), field, max_length=100, level=ValidationLevel.STRICT)

            elif field.endswith('_path') or field == 'path':
                results[field] = self.validate_file_path(str(value))

            elif isinstance(value, dict) and field in ['environment', 'env']:
                results[field] = self.validate_environment_variables(value)

            elif isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                results[field] = self.validate_json_data(value, field)

            else:
                # Default string validation
                results[field] = self.validate_string(str(value), field)

        return results

    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Get summary of validation results"""

        total_fields = len(results)
        valid_fields = sum(1 for r in results.values() if r.is_valid)
        total_errors = sum(len(r.errors) for r in results.values())
        total_warnings = sum(len(r.warnings) for r in results.values())

        failed_fields = [field for field, result in results.items() if not result.is_valid]
        warned_fields = [field for field, result in results.items() if result.warnings]

        return {
            'total_fields': total_fields,
            'valid_fields': valid_fields,
            'invalid_fields': total_fields - valid_fields,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'success_rate': valid_fields / total_fields if total_fields > 0 else 0,
            'failed_fields': failed_fields,
            'warned_fields': warned_fields,
            'is_all_valid': valid_fields == total_fields
        }


# Global validator instance
global_validator = InputValidator()


# Convenience functions
def validate_string(value: str, field_name: str = "input", **kwargs) -> ValidationResult:
    """Quick string validation using global validator"""
    return global_validator.validate_string(value, field_name, **kwargs)


def validate_agent_inputs(agent_name: str, agent_type: str, team: str = None,
                         deployment_type: str = "process") -> Dict[str, ValidationResult]:
    """Validate all agent-related inputs"""

    inputs = {
        'agent_name': agent_name,
        'agent_type': agent_type,
        'deployment_type': deployment_type
    }

    if team:
        inputs['team'] = team

    return global_validator.validate_all_inputs(inputs)


def validate_discord_inputs(content: str, channel_id: str = None,
                           user_id: str = None) -> Dict[str, ValidationResult]:
    """Validate Discord-related inputs"""

    inputs = {'content': content}

    if channel_id:
        inputs['channel_id'] = channel_id
    if user_id:
        inputs['user_id'] = user_id

    return global_validator.validate_all_inputs(inputs)


# Example usage and testing
if __name__ == "__main__":
    # Test the validator
    validator = InputValidator()

    # Test agent name validation
    test_cases = [
        "my_agent",
        "research_claude_001",
        "evil_eval()_agent",
        "<script>alert('xss')</script>",
        "agent'; DROP TABLE users; --",
        "../../etc/passwd",
        "a" * 200,  # Too long
        "",  # Empty
        "normal agent name",
    ]

    print("🧪 Testing Input Validator\n")

    for test_case in test_cases:
        result = validator.validate_agent_name(test_case)
        status = "✅" if result.is_valid else "❌"

        print(f"{status} '{test_case}' -> '{result.sanitized_value}'")
        if result.errors:
            print(f"   Errors: {', '.join(result.errors)}")
        if result.warnings:
            print(f"   Warnings: {', '.join(result.warnings)}")
        print()

    # Test comprehensive validation
    print("\n🔍 Testing Comprehensive Validation")

    test_inputs = {
        'agent_name': 'test_agent',
        'agent_type': 'claude',
        'team': 'research',
        'deployment_type': 'container',
        'content': 'Deploy a new agent please!',
        'environment': {
            'API_KEY': 'safe_key_123',
            'DANGEROUS_PATH': '/etc/passwd'
        }
    }

    results = validator.validate_all_inputs(test_inputs)
    summary = validator.get_validation_summary(results)

    print(f"Validation Summary:")
    print(f"  Valid fields: {summary['valid_fields']}/{summary['total_fields']}")
    print(f"  Success rate: {summary['success_rate']:.1%}")
    print(f"  Total errors: {summary['total_errors']}")
    print(f"  Total warnings: {summary['total_warnings']}")

    if summary['failed_fields']:
        print(f"  Failed fields: {', '.join(summary['failed_fields'])}")

    print("\n🛡️ Input Validator test completed!")
