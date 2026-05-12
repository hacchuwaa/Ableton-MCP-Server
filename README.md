# Chibe - AI-Powered Ableton Live Production Suite

Chibe is a comprehensive MCP (Model Context Protocol) server that enables AI agents to control Ableton Live for music production. It consists of:

1. **Remote Script** (`chibe_remote_script/`) - Runs inside Ableton Live, exposes the Live API via socket
2. **MCP Server** (`chibe_mcp/`) - Bridges AI agents to Ableton via standard MCP protocol
3. **Example Scripts** (`examples/`) - Ready-to-run beat builders

## Features

- **Session Control**: Tempo, playback, loop, time signature
- **Track Management**: Create, delete, rename, duplicate MIDI/audio tracks
- **Clip Programming**: Create clips, add MIDI notes, fire/stop clips, read back notes
- **Instrument Loading**: Browse Ableton's library, search, load instruments by URI
- **Effect Management**: Load audio/MIDI effects, control device parameters
- **Mixing**: Volume, pan, sends, solo, mute, arm
- **Browser Integration**: Full library browser tree, search, path-based navigation
- **Scene Control**: List and fire scenes

## Quick Start

### 1. Install the Remote Script in Ableton

Copy `chibe_remote_script/` to Ableton's Remote Scripts directory:
```
C:\ProgramData\Ableton\Live 12 Suite\Resources\MIDI Remote Scripts\chibe_remote_script\
```

Enable it in Ableton: **Preferences → Link/Tempo/MIDI → Control Surface → Chibe Remote Script**

### 2. Install Dependencies

```bash
pip install mcp uvicorn httpx
```

### 3. Start the MCP Server

```bash
cd chibe
python -m chibe_mcp.run_http    # Streamable HTTP transport (port 8000)
# OR
python -m chibe_mcp.run_uvicorn  # SSE transport (port 8501)
# OR  
python -m chibe_mcp.run_stdio    # Stdio transport (for Claude Desktop)
```

### 4. Build a Beat

```bash
python examples/dre_beat.py
```

## MCP Server Configuration

### For Claude Desktop (Windows)

Add this to your `claude_desktop_config.json`:

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

### For MCP Clients (Streamable HTTP)

```json
{
  "mcpServers": {
    "chibe": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

Or use the CLI:

```bash
# Start HTTP server
python -m chibe_mcp.run_http

# Then connect via any MCP client
# URL: http://127.0.0.1:8000/mcp
```

## Available MCP Tools

### Session
| Tool | Description |
|------|-------------|
| `get_session_info` | Get session details (tempo, tracks, scenes) |
| `set_tempo` | Set BPM |
| `start_playback` / `stop_playback` | Transport control |
| `set_loop` | Set loop range |

### Tracks
| Tool | Description |
|------|-------------|
| `create_midi_track` | Create MIDI track (+ optional name) |
| `create_audio_track` | Create audio track |
| `delete_track` | Remove a track |
| `duplicate_track` | Clone a track |
| `set_track_name` | Rename track |
| `arm_track` | Arm for recording |
| `set_track_solo` / `set_track_mute` | Solo/mute control |

### Clips
| Tool | Description |
|------|-------------|
| `create_clip` | Create empty MIDI clip |
| `add_notes_to_clip` | Add MIDI notes (pitch, time, duration, velocity) |
| `get_clip_notes` | Read back MIDI notes from clip |
| `set_clip_name` | Name a clip |
| `fire_clip` / `stop_clip` | Launch/stop clips |
| `delete_clip` | Remove clip |

### Browser & Instruments
| Tool | Description |
|------|-------------|
| `get_browser_tree` | Browse library hierarchy (instruments, sounds, drums, effects) |
| `get_browser_items` | List items at a browser path |
| `search_browser` | Search library by keyword |
| `load_instrument` | Load instrument/sound onto track by URI |

### Effects & Parameters
| Tool | Description |
|------|-------------|
| `load_effect` | Load audio effect onto track |
| `get_track_devices` | List devices on a track |
| `get_device_parameters` | List all parameters of a device |
| `set_device_parameter` | Control any device parameter |

### Mixing
| Tool | Description |
|------|-------------|
| `set_volume` | Track volume (0.0-1.0) |
| `set_pan` | Track pan (-1.0 to 1.0) |
| `set_send` | Send to return track |

## Architecture

```
┌─────────────────────┐     MCP Protocol      ┌──────────────────┐
│   AI Agent / Client │ ◄──────────────────►  │  Chibe MCP Server │
│  (Claude, Cursor,   │     (HTTP/SSE/Stdio)  │  (chibe_mcp/)    │
│   OpenCode, etc.)   │                        │  Port 8000/8501  │
└─────────────────────┘                        └────────┬─────────┘
                                                        │ TCP Socket
                                                        │ Port 9877
                                               ┌────────▼─────────┐
                                               │ Chibe Remote     │
                                               │ Script           │
                                               │ (in Ableton Live)│
                                               └────────┬─────────┘
                                                        │ Live API
                                               ┌────────▼─────────┐
                                               │ Ableton Live 12  │
                                               │ Suite            │
                                               └──────────────────┘
```

## GitHub

This project is designed to be pushed to GitHub for collaboration.
