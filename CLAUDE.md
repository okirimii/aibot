# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Bot
```bash
python -m src.aibot
```

### Code Quality
```bash
# Run type checking
uv run mypy .

# Run linting and formatting
uv run ruff check .
uv run ruff format .

# Fix linting issues automatically
uv run ruff check --fix .
```

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package-name>

# Add development dependency
uv add --group dev <package-name>
```

## Git Configuration

- The commit message template is located in `.gitnub/.gitmessage`.

## Architecture Overview

### Multi-Provider AI System
The bot supports three AI providers (OpenAI, Anthropic, Google) through a factory pattern:
- `ApiFactory` detects provider from model name prefix or uses current provider setting
- `ProviderManager` maintains global provider state as singleton
- Each provider has dedicated implementation (`_openai.py`, `_anthropic.py`, `_gemini.py`)

### System Instruction Management
Dynamic system instruction system with multiple layers:
- **Static Instructions**: Defined in `resources/instructions.yml` per command type
- **Custom Instructions**: User-created, stored in database and `resources/gen/` files
- **Force Mode**: Admin setting to lock all commands to static instructions
- **Resolution Order**: Custom instruction → Static instruction → Error fallback

Key components:
- `InstructionService`: Orchestrates instruction resolution and file management
- `SystemSettingsService`: Manages force mode and system-wide settings
- `InstructionDAO`: Database operations for instruction persistence

### Database Layer
Uses aiosqlite with DAO pattern:
- `DAOBase`: Common database operations and timezone handling
- Table initialization in `__main__.py`: `InstructionDAO`, `SystemDAO`, `UsageDAO`, `ModerationDAO`, `PermissionDAO`
- Proper transaction handling and connection cleanup

### Discord Command Structure
Commands in `src/aibot/discord/commands/`:
- Each command file registers with Discord client singleton
- Imports aggregated in `__init__.py` for automatic registration
- Commands support both static and custom system instructions via `get_active_instruction(command_name)`
- Protection via decorators: `@has_daily_usage_left()`, `@is_admin_user()`, `@is_beta_user()`

### Security and Moderation System
Multi-layered protection system:
- **InputValidator**: Prompt injection detection and content sanitization with regex patterns
- **ModerationService**: OpenAI moderation API integration with database logging
- **Rate Limiting**: Daily usage limits per user with admin bypass
- **Permission System**: Admin/beta user role management with database persistence
- **Violation Tracking**: User violation history with automatic blocking thresholds

### Environment Configuration
Required environment variables loaded via dotenv:
- `DISCORD_BOT_TOKEN`: Discord bot authentication
- `BOT_NAME`, `BOT_ID`: Bot identity for message processing
- `ADMIN_USER_IDS`: Comma-separated admin user IDs for permission system
- AI provider API keys and model configurations
- Model defaults and generation parameters (temperature, max_tokens, top_p)

### Error Handling Patterns
- Services return structured dictionaries with `success`, `message` fields
- DAOs handle database errors and return None/False on failure
- Commands provide user-friendly error messages while logging technical details
- System instruction fallback prevents null system prompts to AI APIs

## Key Implementation Notes

### Adding New Commands
1. Create command file in `src/aibot/discord/commands/`
2. Apply appropriate decorators: `@has_daily_usage_left()` for AI commands, `@is_admin_user()` or `@is_beta_user()` for restricted features
3. Use `get_active_instruction(command_name)` for system instruction support
4. Add static instruction to `resources/instructions.yml`
5. For AI-calling commands: integrate `ModerationService.moderate_content()` and `UsageDAO.increment_usage_count()`
6. Import and register in `commands/__init__.py`

### Message Processing
The `ChatMessage` and `ChatHistory` classes handle Discord-to-AI message conversion:
- Role mapping: Discord usernames → "user", bot name → "assistant"
- Content handling with null safety for API compatibility

### File Management
Custom instructions are dual-stored:
- Database: Metadata and activation state
- Files: Content in `resources/gen/` with timestamp naming
- Automatic cleanup maintains max 100 instruction files

### Security Integration Pattern
For commands that process user input:
```python
# 1. Moderate content before processing
is_flagged = await moderation_service.moderate_content(
    content=user_input, user_id=user.id, request_type="command_name"
)
if is_flagged:
    # Reject content and log violation

# 2. Track usage for AI calls
await UsageDAO().increment_usage_count(user.id)
```

### Content Validation Layers
- **InputValidator.validate_chat_message()**: Length, forbidden terms, prompt injection detection
- **InputValidator.validate_system_instruction()**: Stricter validation for admin functions
- **InputValidator.validate_code_input()**: Code-specific security patterns
- **ModerationService**: OpenAI moderation API for content policy violations
