# SuperAgent Issues & Troubleshooting

This directory contains documentation for known issues, their root causes, and resolutions.

## Current Issues

### `DISCORD_IDENTITY_ISSUE.md`
**Issue**: Discord bot identity regression where all agents appeared as the same bot
**Status**: ✅ RESOLVED
**Summary**: All Discord tokens in `.env` were identical, causing multi-bot functionality to fail

**Quick Fix:**
1. Create separate Discord bot applications
2. Update `.env` with unique tokens
3. Run `python tests/validate_discord_config.py` to verify

## Issue Categories

### 🤖 **Discord & Bot Issues**
- Discord identity conflicts
- Multi-bot functionality problems
- Token configuration errors

### 🐳 **Container & Deployment Issues**
- Docker container code mismatches
- Port mapping problems
- Build and deployment inconsistencies

### 🔧 **Configuration Issues**
- Environment variable problems
- Service connectivity issues
- Authentication and token problems

## Reporting New Issues

When documenting new issues:

1. **Create issue document**: `ISSUE_NAME.md`
2. **Include sections**:
   - Issue Summary
   - Root Cause Analysis
   - Resolution Steps
   - Prevention Measures
3. **Add to this README**
4. **Link to related troubleshooting docs**

## Related Documentation

- [Troubleshooting Guides](../docs/troubleshooting/)
- [Test Suite](../tests/)
- [Developer Guide](../docs/DEVELOPER_GUIDE.md)