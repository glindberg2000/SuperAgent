# SuperAgent Test Suite

This directory contains all test files and validation tools for the SuperAgent project.

## Test Files

### `test_discord_identities.py`
Comprehensive test suite for Discord bot identities and multi-bot functionality.

**Usage:**
```bash
source .venv/bin/activate
python tests/test_discord_identities.py
```

**Features:**
- Tests all configured Discord tokens
- Verifies unique bot identities
- Detects identity conflicts and regressions
- Generates detailed test reports
- Prevents multi-bot functionality issues

### `validate_discord_config.py`
Configuration validator for Discord token setup.

**Usage:**
```bash
source .venv/bin/activate
python tests/validate_discord_config.py
```

**Features:**
- Validates Discord token uniqueness
- Detects duplicate tokens
- Provides setup instructions
- Prevents configuration errors

## Test Reports

### `discord_identity_test_report.json`
Generated test report containing:
- Test results for all Discord tokens
- Bot identity analysis
- Unique identity counts
- Regression detection flags

## Running All Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Validate Discord configuration
python tests/validate_discord_config.py

# Test Discord identities
python tests/test_discord_identities.py

# Check test report
cat tests/discord_identity_test_report.json
```

## CI/CD Integration

These tests should be run before deployment to ensure:
- Discord tokens are properly configured
- Multi-bot functionality works correctly
- No identity regressions are introduced

## Adding New Tests

When adding new test files:
1. Follow naming convention: `test_*.py`
2. Include comprehensive docstrings
3. Generate test reports in JSON format
4. Update this README with new test descriptions