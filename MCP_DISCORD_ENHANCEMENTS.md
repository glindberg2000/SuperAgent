# MCP Discord Server Enhancement Requirements

## Overview

To enable file upload/download capabilities for SuperAgent Discord bots, the MCP Discord server needs to be extended with additional tools. This document outlines the required changes to the separate MCP Discord repository.

## Current MCP Discord Tools (25 available)

The MCP Discord server currently provides 25 tools for Discord integration, but **lacks file handling capabilities**:

### Available Tools
- **Messages**: `send_message`, `read_messages`, `wait_for_message`, `get_unread_messages`
- **Server**: `get_server_info`, `list_members` 
- **Channels**: `create_text_channel`, `delete_channel`, `create_thread`, `create_category`
- **Permissions**: `set_channel_permissions`
- **Reactions**: `add_reaction`, `add_multiple_reactions`, `remove_reaction`
- **Roles**: `create_role`, `delete_role`, `list_roles`, `add_role`, `remove_role`
- **Moderation**: `moderate_message`, `kick_user`, `ban_user`
- **Agent**: `set_agent_status`, `check_connection`

### Missing File Operations
- ❌ `send_file` - Upload files to Discord channels
- ❌ `get_attachment` - Download attachments from messages  
- ❌ `save_attachment` - Save message attachments locally
- ❌ `upload_document` - Upload generated documents

## Required Enhancements

### 1. Add `send_file` Tool

**Purpose**: Upload files to Discord channels
**Discord.py Implementation**: `discord.File()` and `channel.send(file=...)`

```python
@tool("send_file")
async def send_file(channel_id: str, file_path: str, filename: str = None, content: str = ""):
    """Send a file to a Discord channel"""
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return {"error": "Channel not found"}
    
    try:
        discord_file = discord.File(file_path, filename=filename)
        await channel.send(content=content, file=discord_file)
        return {"status": "success", "message": f"File uploaded: {filename or file_path}"}
    except Exception as e:
        return {"error": str(e)}
```

**Parameters**:
- `channel_id`: Discord channel ID
- `file_path`: Local file path to upload
- `filename`: Optional custom filename (defaults to original)
- `content`: Optional message text to send with file

### 2. Add `send_file_from_bytes` Tool

**Purpose**: Upload generated content as files
**Use case**: Bot creates documents/reports and uploads them

```python
@tool("send_file_from_bytes")
async def send_file_from_bytes(channel_id: str, file_data: bytes, filename: str, content: str = ""):
    """Send file from bytes data to Discord channel"""
    import io
    
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return {"error": "Channel not found"}
    
    try:
        file_obj = io.BytesIO(file_data)
        discord_file = discord.File(file_obj, filename=filename)
        await channel.send(content=content, file=discord_file)
        return {"status": "success", "message": f"File uploaded: {filename}"}
    except Exception as e:
        return {"error": str(e)}
```

### 3. Add `get_message_attachments` Tool

**Purpose**: List attachments from a specific message
**Discord.py Implementation**: `message.attachments`

```python
@tool("get_message_attachments")
async def get_message_attachments(channel_id: str, message_id: str):
    """Get list of attachments from a message"""
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return {"error": "Channel not found"}
    
    try:
        message = await channel.fetch_message(int(message_id))
        attachments = [{
            "filename": att.filename,
            "url": att.url,
            "size": att.size,
            "content_type": getattr(att, 'content_type', 'unknown')
        } for att in message.attachments]
        
        return {"attachments": attachments}
    except Exception as e:
        return {"error": str(e)}
```

### 4. Add `download_attachment` Tool

**Purpose**: Download and save message attachments locally
**Discord.py Implementation**: `attachment.save()`

```python
@tool("download_attachment")
async def download_attachment(channel_id: str, message_id: str, attachment_filename: str, save_path: str = None):
    """Download an attachment from a Discord message"""
    channel = bot.get_channel(int(channel_id))
    if not channel:
        return {"error": "Channel not found"}
    
    try:
        message = await channel.fetch_message(int(message_id))
        
        # Find the attachment
        target_attachment = None
        for attachment in message.attachments:
            if attachment.filename == attachment_filename:
                target_attachment = attachment
                break
        
        if not target_attachment:
            return {"error": f"Attachment '{attachment_filename}' not found"}
        
        # Save attachment
        save_path = save_path or f"downloads/{attachment_filename}"
        await target_attachment.save(fp=save_path, use_cached=False)  # use_cached=False for non-images
        
        return {
            "status": "success", 
            "saved_path": save_path,
            "filename": attachment_filename,
            "size": target_attachment.size
        }
    except Exception as e:
        return {"error": str(e)}
```

### 5. Enhanced `read_messages` Tool

**Purpose**: Include attachment info in message reading
**Enhancement**: Add attachment metadata to existing message responses

```python
# Modify existing read_messages to include attachment info
def format_message_with_attachments(message):
    formatted = format_message(message)  # existing logic
    
    if message.attachments:
        attachments = [{
            "filename": att.filename,
            "url": att.url,
            "size": att.size
        } for att in message.attachments]
        formatted["attachments"] = attachments
    
    return formatted
```

## Integration with SuperAgent

### 1. Update Enhanced Discord Agent

Add file handling capability to `enhanced_discord_agent.py`:

```python
async def handle_file_upload(self, session: ClientSession, file_path: str, channel_id: str, description: str = ""):
    """Upload a generated file to Discord"""
    result = await session.call_tool(
        "send_file",
        {
            "channel_id": channel_id,
            "file_path": file_path,
            "content": description
        }
    )
    return result

async def process_attachment(self, session: ClientSession, message_data: Dict):
    """Process incoming message attachments"""
    if message_data.get('attachments'):
        for attachment in message_data['attachments']:
            # Download for analysis
            result = await session.call_tool(
                "download_attachment",
                {
                    "channel_id": message_data['channel_id'],
                    "message_id": message_data['id'],
                    "attachment_filename": attachment['filename'],
                    "save_path": f"temp/{attachment['filename']}"
                }
            )
            
            if result.get('status') == 'success':
                # Process downloaded file
                await self.analyze_uploaded_file(result['saved_path'])
```

### 2. Add File Generation Capabilities

Enable bots to create and upload documents:

```python
async def generate_document(self, content: str, format: str = "txt", channel_id: str = ""):
    """Generate and upload a document"""
    filename = f"report_{int(time.time())}.{format}"
    
    if format == "txt":
        with open(f"temp/{filename}", "w") as f:
            f.write(content)
    elif format == "json":
        with open(f"temp/{filename}", "w") as f:
            json.dump(content, f, indent=2)
    
    # Upload to Discord
    await self.handle_file_upload(session, f"temp/{filename}", channel_id)
```

## Configuration Updates

### Agent Config Enhancement

Add file handling settings to `agent_config.json`:

```json
{
  "agents": {
    "grok4_agent": {
      "file_capabilities": {
        "can_upload": true,
        "can_download": true,
        "max_file_size_mb": 10,
        "allowed_extensions": [".txt", ".md", ".json", ".csv", ".pdf"],
        "download_directory": "downloads/grok4/"
      }
    }
  }
}
```

## Implementation Priority

### Phase 1: Core File Operations
1. ✅ `send_file` tool (highest priority)
2. ✅ `get_message_attachments` tool  
3. ✅ `download_attachment` tool

### Phase 2: Enhanced Features
4. `send_file_from_bytes` for generated content
5. Enhanced `read_messages` with attachment metadata
6. File type validation and security checks

### Phase 3: Advanced Features  
7. Batch file operations
8. File compression/archiving
9. Image processing capabilities
10. Document parsing (PDF, Word, etc.)

## Security Considerations

### File Upload Security
- Validate file extensions and MIME types
- Implement file size limits (Discord: 10MB default)
- Scan for malicious content
- Sanitize filenames

### File Download Security  
- Limit download locations (sandboxed directories)
- Validate attachment sources
- Implement rate limiting for downloads
- Clean up temporary files

### Storage Management
- Automatic cleanup of old files
- Configurable storage limits
- Backup important generated documents

## Testing Requirements

Before deploying MCP Discord server updates:

1. **Unit Tests**: Test each new tool individually
2. **Integration Tests**: Test with SuperAgent bot instances
3. **File Type Tests**: Test various file formats (images, documents, archives)
4. **Error Handling**: Test invalid files, missing permissions, etc.
5. **Performance Tests**: Test with large files and multiple concurrent uploads

## Deployment Notes

⚠️ **Important**: The MCP Discord server is a **separate repository** that powers multiple sessions beyond SuperAgent. Changes must be:

1. **Thoroughly tested** in isolated environment first
2. **Backward compatible** with existing MCP tool interfaces
3. **Coordinated** with other projects using the MCP Discord server
4. **Versioned properly** to allow rollback if issues occur

## Expected Benefits

After implementation, SuperAgent bots will be able to:

✅ **Generate and share reports** (analysis summaries, research findings)
✅ **Process uploaded documents** (analyze user-provided files)  
✅ **Create visual content** (charts, diagrams, code snippets)
✅ **Archive conversations** (export chat histories)
✅ **Share code files** (generated scripts, configurations)

This will significantly enhance bot utility for document-heavy workflows, data analysis, and collaborative content creation.