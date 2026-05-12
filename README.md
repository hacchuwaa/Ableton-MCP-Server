# Chibe - AI-Powered Ableton Live Production Suite

<p align="center">
  <img src="https://img.shields.io/github/stars/hacchuwaa/Ableton-MCP-Server" alt="Stars">
  <img src="https://img.shields.io/github/languages/top/hacchuwaa/Ableton-MCP-Server" alt="Language">
  <img src="https://img.shields.io/github/license/hacchuwaa/Ableton-MCP-Server" alt="License">
</p>

## 🚀 About

**Chibe** is a production-ready MCP (Model Context Protocol) server that enables AI agents to control Ableton Live for professional music production. Still in active development with regular updates.

### What is MCP?

**Model Context Protocol (MCP)** is an open standard developed by Anthropic that enables AI applications to connect to external tools and services through a standardized interface. Think of it as "USB-C for AI" - a universal port that lets AI models communicate with any application.

**Why MCP for Music Production?**
- **AI Integration**: AI assistants can control Ableton Live directly through natural language
- **Standardized Tools**: 43+ MCP tools provide consistent, discoverable functionality
- **Transport Flexibility**: Works via HTTP, SSE, or Stdio (great for Claude Desktop, Cursor, etc.)
- **Extensible**: Easy to add new commands without changing the AI prompts

## 🎹 Architecture

```
┌─────────────────┐      Socket (9877)      ┌──────────────────┐
│  Ableton Live  │◄─────────────────────────►│  Remote Script   │
│   (Python 3)   │                           │ (chibe_remote)   │
└─────────────────┘                          └────────┬─────────┘
                                                      │
                                                      │ TCP
                                                      ▼
┌────────────────────────────────────────────────────┐
│                  MCP Server                        │
│                  (chibe_mcp)                       │
│                                                    │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│   │ Session  │ │ Tracks   │ │  Clips   │   ...    │
│   │ Tools    │ │ Tools    │ │ Tools    │          │
│   └──────────┘ └──────────┘ └──────────┘          │
│                                                    │
│   Transport: HTTP / SSE / Stdio                    │
└────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│              AI Agent / Client                     │
│  (Claude Desktop, Cursor, custom LLM app, etc.)  │
└────────────────────────────────────────────────────┘
```

## ✨ Features

### Session Control
- `get_session_info` - Get tempo, time signature, track/scene counts, playback state
- `set_tempo` - Set BPM (92 BPM for G-Funk, 140 for House, etc.)
- `start_playback` / `stop_playback` - Transport control
- `set_loop` - Set loop region in arrangement

### Track Management (43 tools total)
- `create_midi_track` / `create_audio_track` - Create new tracks
- `delete_track` / `duplicate_track` - Manage tracks
- `set_track_name` / `set_track_name` - Rename tracks
- `arm_track` / `set_track_solo` / `set_track_mute` - Track state

### Clip & MIDI Programming
- `create_clip` - Create MIDI clips with configurable length
- `add_notes_to_clip` - Add MIDI notes with pitch, time, duration, velocity
- `get_clip_notes` - Read back note data
- `fire_clip` / `stop_clip` / `delete_clip` - Clip control
- `set_clip_name` - Name clips

### Device & Browser Integration
- `get_browser_tree` - Hierarchical library tree (instruments, sounds, drums, effects)
- `get_browser_items` - Items at specific path
- `search_browser` - Search Ableton's library
- `load_instrument` - Load instruments by URI (e.g., `query:Sounds#Bass:FileId_423099`)
- `load_effect` / `load_drum_kit` - Load effects and drum racks

### Mixing & Parameters
- `set_volume` / `set_pan` - Track mixing
- `set_send` - Send levels to return tracks
- `get_track_devices` - List devices on track
- `get_device_parameters` / `set_device_parameter` - Device automation

### Master Track & Mastering
- `get_master_info` - Master volume, pan, device count
- `get_master_devices` - Full mastering chain info
- `set_master_volume` / `set_master_pan` - Master output control
- `set_master_device_parameter` - Tweak compressor, EQ, limiter parameters

### Library Scanning (Fast!)
- `get_plugins_info` - Quick-scan all available plugins/instruments
- `scan_library` - Fast flat recursive scan with timing info

### Track Routing
- `set_track_output` - Route track output to master/other tracks

## 🔧 Installation

### Step 1: Install Remote Script in Ableton

Copy `chibe_remote_script/` to Ableton's Remote Scripts directory:
```
C:\ProgramData\Ableton\Live 12 Suite\Resources\MIDI Remote Scripts\chibe_remote_script\
```

**Enable in Ableton**: Preferences → Link/Tempo/MIDI → Control Surface → Chibe Remote Script

### Step 2: Install Dependencies

```bash
pip install mcp uvicorn httpx
# OR use the provided requirements.txt
pip install -r requirements.txt
```

### Step 3: Start the MCP Server

```bash
# Option 1: Streamable HTTP (recommended for web/API access)
python -m chibe_mcp.run_http
# Server runs at: http://127.0.0.1:8000/mcp

# Option 2: SSE transport (alternative)
python -m chibe_mcp.run_sse

# Option 3: Stdio (for Claude Desktop, AI clients)
python -m chibe_mcp.run_stdio
```

### Step 4: Connect Your AI

#### Claude Desktop
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "chibe": {
      "command": "python",
      "args": ["-m", "chibe_mcp.run_stdio"]
    }
  }
}
```

#### Other MCP Clients
```json
{
  "mcpServers": {
    "chibe": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

## 🎵 Example: Dr. Dre G-Funk Beat

Run the included beat builder:
```bash
python examples/dre_beat.py
```

This creates an 8-bar G-Funk track at 92 BPM in G minor with:
- 8 tracks (Kick, Snare, Hi-Hat, Percussion, Bass, Rhodes, Synth Lead, Pads)
- Authentic swung drum patterns
- Melodic bass following Gm7 | Cm7 | D7 | Gm7 chord progression
- Professional mix levels pre-configured

## 📁 Project Structure

```
chibe/
├── chibe_mcp/              # MCP Server
│   ├── server.py           # 43+ MCP tools
│   ├── run_http.py         # HTTP transport
│   ├── run_sse.py          # SSE transport
│   ├── run_stdio.py        # Stdio transport
│   └── __init__.py
├── chibe_remote_script/    # Ableton Remote Script
│   └── __init__.py         # 1073 lines, 40+ command handlers
├── examples/
│   └── dre_beat.py         # Dr. Dre G-Funk beat builder
├── README.md               # This file
├── pyproject.toml          # Project metadata
├── requirements.txt        # Dependencies
└── uv.lock                 # Locked dependencies
```

## 🔨 Development

### Run Tests
```bash
python test_connectivity.py
```

### Add New Commands
1. Add handler to `chibe_remote_script/__init__.py` (in `modifying_commands` or `read_commands`)
2. Add tool to `chibe_mcp/server.py` with `@mcp.tool()` decorator
3. Test with: `python -c "import asyncio; from chibe_mcp.server import mcp; print([t.name for t in mcp._tool_manager._tools.values()])"`

## 📄 License

MIT License - Feel free to use, modify, and distribute!

## 🤝 Contributing

Contributions welcome! Please open an issue or PR on GitHub.

---

<p align="center">Built with ❤️ for AI-powered music production</p>