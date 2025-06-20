# Whirlpool Sixth Sense MCP Server

This MCP (Model Context Protocol) server allows LLMs to interact with your Whirlpool, Maytag, KitchenAid, or Consul washer/dryer appliances. It supports both Server-Sent Events (SSE) and stdio transports using the FastMCP framework.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -e .
   ```

2. **Configure environment variables:**
   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your Whirlpool account details
   ```

## Running the Server

### Option 1: SSE Transport (Default, Recommended)

Start the server with SSE transport (default):
```bash
python mcp_server.py
# or explicitly:
python mcp_server.py --transport sse
```

The server will be available at `http://localhost:8000` with SSE endpoint at `/sse`.

### Option 2: Stdio Transport (for compatibility)

For clients that only support stdio transport:
```bash
python mcp_server.py --transport stdio
```

**Configure MCP client for stdio:**
```json
{
  "mcpServers": {
    "whirlpool-sixth-sense": {
      "command": "python",
      "args": ["/path/to/whirlpool-sixth-sense/mcp_server.py", "--transport", "stdio"],
      "env": {
        "WHIRLPOOL_EMAIL": "your-email@example.com",
        "WHIRLPOOL_PASSWORD": "your-password",
        "WHIRLPOOL_BRAND": "whirlpool",
        "WHIRLPOOL_REGION": "EU"
      }
    }
  }
}
```

**Configure MCP client for SSE:**
```json
{
  "mcpServers": {
    "whirlpool-sixth-sense": {
      "url": "http://localhost:8000/sse",
      "env": {
        "WHIRLPOOL_EMAIL": "your-email@example.com",
        "WHIRLPOOL_PASSWORD": "your-password",
        "WHIRLPOOL_BRAND": "whirlpool",
        "WHIRLPOOL_REGION": "EU"
      }
    }
  }
}
```

## Tools Available

- **`list_appliances`** - Get all available washer/dryer appliances
- **`get_status`** - Get comprehensive status of a specific appliance
- **`refresh_data`** - Refresh appliance data from Whirlpool servers
- **`send_command`** - Send custom commands/attributes to appliance
- **`get_machine_state`** - Get human-readable machine state

## Resources Available

- **`whirlpool://appliances`** - List of all appliances
- **`whirlpool://status/{appliance_id}`** - Current status of specific appliance
- **`whirlpool://raw/{appliance_id}`** - Raw API data for specific appliance

## Usage Examples

Ask your LLM:
- "What's the status of my washer?"
- "List all my appliances"
- "Is my dryer cycle complete?"
- "Send a pause command to my washer"
- "What's the time remaining on my current cycle?"

## Supported Brands & Regions

- **Brands:** Whirlpool, Maytag, KitchenAid, Consul
- **Regions:** EU, US

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `WHIRLPOOL_EMAIL` | - | Your account email (required) |
| `WHIRLPOOL_PASSWORD` | - | Your account password (required) |
| `WHIRLPOOL_BRAND` | `whirlpool` | Brand name |
| `WHIRLPOOL_REGION` | `EU` | Region |

## Testing

You can test the CLI functionality first:
```bash
python cli.py -e your-email@example.com -p your-password -l
```

This will list your appliances and verify your credentials work.