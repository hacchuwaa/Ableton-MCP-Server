"""
Chibe MCP Server
================
Comprehensive MCP (Model Context Protocol) server for Ableton Live.
Connects to the Chibe Remote Script running inside Ableton via a socket.

All tools are organized by domain:
  - Session: tempo, playback, time signature, loop
  - Tracks: create, delete, rename, duplicate, solo, mute, arm
  - Mixing: volume, pan, sends
  - Clips: create, add notes, fire, stop, delete
  - Devices: browse, load, parameter control
  - Browser: browse library, search, get items
  - Scenes: list, fire

Usage:
  from chibe_mcp.server import mcp
  mcp.run(transport="streamable-http")  # or "sse" or "stdio"
"""

import json
import logging
import socket
import time
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("ChibeMCP")

# Configuration
ABLETON_HOST = "localhost"
ABLETON_PORT = 9877
DEFAULT_TIMEOUT = 20.0

# ── Socket Communication ─────────────────────────────────────────

class AbletonBridge:
    """Handles socket communication with the Chibe Remote Script."""

    def __init__(self, host=ABLETON_HOST, port=ABLETON_PORT):
        self.host = host
        self.port = port
        self._sock = None

    def connect(self):
        if self._sock:
            return True
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(5.0)
            self._sock.connect((self.host, self.port))
            logger.info(f"Connected to Ableton at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self._sock = None
            return False

    def disconnect(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def send_command(self, cmd_type: str, params: dict = None) -> dict:
        """Send a command and return parsed response."""
        if not self._sock and not self.connect():
            raise ConnectionError("Cannot connect to Ableton")

        command = {"type": cmd_type, "params": params or {}}

        # State-modifying commands get a small delay
        modifying = cmd_type in [
            "create_midi_track", "create_audio_track", "delete_track", "duplicate_track",
            "set_track_name", "set_track_solo", "set_track_mute", "arm_track",
            "create_clip", "delete_clip", "add_notes_to_clip", "set_clip_name",
            "set_tempo", "fire_clip", "stop_clip",
            "start_playback", "stop_playback",
            "load_browser_item", "load_effect", "load_drum_kit",
            "set_volume", "set_pan", "set_send",
            "set_device_parameter",
            "set_session_focus_point", "fire_scene", "set_loop",
        ]

        try:
            logger.info(f"Sending: {cmd_type}")
            self._sock.sendall(json.dumps(command).encode("utf-8"))

            if modifying:
                time.sleep(0.15)

            self._sock.settimeout(DEFAULT_TIMEOUT)

            chunks = []
            while True:
                try:
                    chunk = self._sock.recv(8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    try:
                        data = b"".join(chunks)
                        parsed = json.loads(data.decode("utf-8"))
                        logger.info(f"Response: {cmd_type} -> {parsed.get('status', '?')}")
                        if parsed.get("status") == "error":
                            raise Exception(parsed.get("message", "Unknown error"))
                        return parsed.get("result", {})
                    except json.JSONDecodeError:
                        continue
                except socket.timeout:
                    if chunks:
                        data = b"".join(chunks)
                        try:
                            parsed = json.loads(data.decode("utf-8"))
                            if parsed.get("status") == "error":
                                raise Exception(parsed.get("message", "Unknown error"))
                            return parsed.get("result", {})
                        except json.JSONDecodeError:
                            raise Exception("Incomplete JSON response")
                    raise Exception("No response from Ableton")

        except Exception as e:
            logger.error(f"Command error ({cmd_type}): {e}")
            self._sock = None
            raise


# Global bridge instance
_bridge = None


def get_bridge() -> AbletonBridge:
    global _bridge
    if _bridge is None:
        _bridge = AbletonBridge()
        _bridge.connect()
    elif _bridge._sock is None:
        _bridge.connect()
    return _bridge


# ── MCP Server Setup ────────────────────────────────────────────

mcp = FastMCP("ChibeAbletonMCP")


# ── Helper ───────────────────────────────────────────────────────

def _cmd(cmd_type: str, params: dict = None) -> dict:
    return get_bridge().send_command(cmd_type, params)


# ══════════════════════════════════════════════════════════════════
#  SESSION TOOLS
# ══════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════
#  MASTER TRACK & MASTERING TOOLS
# ══════════════════════════════════════════════════════════════════

@mcp.tool()
def get_master_info() -> str:
    """Get master track info including volume, pan, and device chain.
    
    Use this to inspect the mastering chain.
    """
    try:
        return json.dumps(_cmd("get_master_info"), indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_master_devices() -> str:
    """Get all devices on the master track with parameters.
    
    Essential for mastering - see what's on the master bus.
    """
    try:
        return json.dumps(_cmd("get_master_devices"), indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_master_volume(volume: float) -> str:
    """Set the master track volume.
    
    Args:
        volume: 0.0 (silent) to 1.0 (unity), careful with > 1.0
    """
    try:
        v = max(0.0, min(1.0, volume))
        _cmd("set_master_volume", {"volume": v})
        return f"Master volume set to {v:.2f}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_master_pan(pan: float) -> str:
    """Set the master track pan position.
    
    Args:
        pan: -1.0 (hard left) to 1.0 (hard right), 0.0 = center
    """
    try:
        p = max(-1.0, min(1.0, pan))
        _cmd("set_master_pan", {"pan": p})
        side = "center" if p == 0 else ("left" if p < 0 else "right")
        return f"Master pan set to {p:.2f} ({side})"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_master_device_parameter(device_index: int, parameter_index: int, value: float) -> str:
    """Set a parameter on a master track device (for mastering).
    
    Use get_master_devices first to find device/parameter indices.
    
    Args:
        device_index: Index of the device on master track
        parameter_index: Index of the parameter on the device
        value: New value (typically 0.0 to 1.0)
    """
    try:
        result = _cmd("set_master_device_parameter", {
            "device_index": device_index,
            "parameter_index": parameter_index,
            "value": value
        })
        return f"Master '{result.get('parameter_name', '?')}' on '{result.get('device_name', '?')}' set to {value}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_plugins_info() -> str:
    """Quick-scan all available plugins and instruments in Ableton's browser.
    
    Returns a categorized list of all available instruments and devices.
    """
    try:
        return json.dumps(_cmd("get_plugins_info"), indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def scan_library(category: str = "all", max_depth: int = 2) -> str:
    """Fast-scan the Ableton library for all loadable items.
    
    Returns a flat list sorted by name for quick searching.
    Much faster than browsing the tree manually.
    
    Args:
        category: 'all', 'instruments', 'sounds', 'drums', 'audio_effects'
        max_depth: How deep to scan (1=top level, 2=one subfolder, 3=two levels)
    """
    try:
        return json.dumps(_cmd("scan_library", {
            "category": category, "max_depth": max_depth
        }), indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_track_output(track_index: int, output_type: str = "master") -> str:
    """Set a track's output routing.
    
    Args:
        track_index: Track to route
        output_type: 'master' for master output
    """
    try:
        _cmd("set_track_output", {"track_index": track_index, "output_type": output_type})
        return f"Track {track_index} output set to '{output_type}'"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_session_info() -> str:
    """Get detailed information about the current Ableton session.
    
    Returns tempo, time signature, track counts, scene counts,
    playback state, and loop settings.
    """
    try:
        return json.dumps(_cmd("get_session_info"), indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_tempo(tempo: float) -> str:
    """Set the session tempo in BPM.
    
    Args:
        tempo: Tempo in BPM (e.g., 92.0 for G-Funk, 140.0 for house)
    """
    try:
        _cmd("set_tempo", {"tempo": tempo})
        return f"Tempo set to {tempo} BPM"
    except Exception as e:
        return f"Error setting tempo: {e}"


@mcp.tool()
def start_playback() -> str:
    """Start Ableton session playback."""
    try:
        _cmd("start_playback")
        return "Playback started"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def stop_playback() -> str:
    """Stop Ableton session playback."""
    try:
        _cmd("stop_playback")
        return "Playback stopped"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def show_session() -> str:
    """Switch to Session view to see clips in clip slots."""
    try:
        result = _cmd("show_session")
        return "Switched to Session view - look at the clip slots!"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_loop(loop_start: float = 0.0, loop_length: float = 32.0, looping: bool = True) -> str:
    """Set the loop range in the arrangement.

    Args:
        loop_start: Start position in beats
        loop_length: Length in beats
        looping: Enable/disable looping
    """
    try:
        _cmd("set_loop", {"loop_start": loop_start, "loop_length": loop_length, "looping": looping})
        return f"Loop set: {loop_start} to {loop_start + loop_length} beats (looping={looping})"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_tracks_info() -> str:
    """Get information about all tracks in the session.
    
    Returns name, index, volume, pan, mute, solo, arm, device count, clip count for each track.
    """
    try:
        return json.dumps(_cmd("get_tracks_info"), indent=2)
    except Exception as e:
        return f"Error: {e}"


# ══════════════════════════════════════════════════════════════════
#  TRACK MANAGEMENT TOOLS
# ══════════════════════════════════════════════════════════════════

@mcp.tool()
def create_midi_track(index: int = -1, name: str = "") -> str:
    """Create a new MIDI track.
    
    Args:
        index: Insert position (-1 = end of list)
        name: Optional track name
    """
    try:
        result = _cmd("create_midi_track", {"index": index})
        if name:
            _cmd("set_track_name", {"track_index": result.get("index", 0), "name": name})
            return f"Created MIDI track '{name}' at index {result.get('index', 0)}"
        return f"Created MIDI track at index {result.get('index', 0)}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def create_audio_track(index: int = -1, name: str = "") -> str:
    """Create a new audio track.
    
    Args:
        index: Insert position (-1 = end of list)
        name: Optional track name
    """
    try:
        result = _cmd("create_audio_track", {"index": index})
        if name:
            _cmd("set_track_name", {"track_index": result.get("index", 0), "name": name})
            return f"Created audio track '{name}' at index {result.get('index', 0)}"
        return f"Created audio track at index {result.get('index', 0)}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def delete_track(track_index: int) -> str:
    """Delete a track by index.
    
    Args:
        track_index: Index of the track to delete
    """
    try:
        result = _cmd("delete_track", {"track_index": track_index})
        return f"Deleted track '{result.get('deleted_track', '?')}'"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_track_name(track_index: int, name: str) -> str:
    """Rename a track.
    
    Args:
        track_index: Index of the track
        name: New name for the track
    """
    try:
        _cmd("set_track_name", {"track_index": track_index, "name": name})
        return f"Track {track_index} renamed to '{name}'"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def arm_track(track_index: int, arm: bool = True) -> str:
    """Arm a track for recording.
    
    Args:
        track_index: Index of the track
        arm: True to arm, False to disarm
    """
    try:
        _cmd("arm_track", {"track_index": track_index, "arm": arm})
        return f"Track {track_index} {'armed' if arm else 'disarmed'}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_track_solo(track_index: int, solo: bool = True) -> str:
    """Solo/unsolo a track.
    
    Args:
        track_index: Index of the track
        solo: True to solo, False to unsolo
    """
    try:
        _cmd("set_track_solo", {"track_index": track_index, "solo": solo})
        return f"Track {track_index} {'soloed' if solo else 'unsoloed'}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_track_mute(track_index: int, mute: bool = True) -> str:
    """Mute/unmute a track.
    
    Args:
        track_index: Index of the track
        mute: True to mute, False to unmute
    """
    try:
        _cmd("set_track_mute", {"track_index": track_index, "mute": mute})
        return f"Track {track_index} {'muted' if mute else 'unmuted'}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def create_instrument(track_index: int, instrument_type: str = "simpler") -> str:
    """Create an instrument on a track.
    
    Attempts multiple methods to load the instrument reliably.
    
    Args:
        track_index: Index of the track to load instrument onto
        instrument_type: Type of instrument ('simpler', 'drum_rack', 'operator', 'analog', 'collision')
    
    Returns:
        Status message with loaded instrument info
    """
    try:
        result = _cmd("create_instrument", {"track_index": track_index, "instrument_type": instrument_type})
        if result.get("loaded"):
            return f"Loaded {result.get('instrument')} on track {track_index} (method: {result.get('method', 'unknown')})"
        else:
            return f"Track {track_index} prepared for manual instrument load: {result.get('message', '')}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def duplicate_track(track_index: int) -> str:
    """Duplicate a track.
    
    Args:
        track_index: Index of the track to duplicate
    """
    try:
        result = _cmd("duplicate_track", {"track_index": track_index})
        return f"Duplicated track at index {result.get('index', '?')} as '{result.get('name', '?')}'"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def load_default_instrument(track_index: int, instrument_type: str = "drum_rack") -> str:
    """Load a default Ableton instrument on a track.
    
    Attempts to load the instrument from Ableton's browser.
    
    Args:
        track_index: Track to load instrument on
        instrument_type: Type of instrument ('drum_rack', 'simpler', 'operator', 'analog')
    
    Returns:
        Status message with loaded instrument name
    """
    try:
        result = _cmd("load_default_instrument", {
            "track_index": track_index,
            "instrument_type": instrument_type
        })
        if result.get("loaded"):
            return f"Loaded {result.get('instrument', instrument_type)} on track {track_index}"
        else:
            return f"Could not load {instrument_type} - {result.get('message', 'Please load manually')}"
    except Exception as e:
        return f"Error: {e}"


# ══════════════════════════════════════════════════════════════════
#  CLIP MANAGEMENT TOOLS
# ══════════════════════════════════════════════════════════════════

@mcp.tool()
def create_clip(track_index: int, clip_index: int, length: float = 4.0) -> str:
    """Create a new empty MIDI clip.
    
    Args:
        track_index: Track to create the clip in
        clip_index: Clip slot index
        length: Length in beats (default: 4.0 = 1 bar at 4/4)
    """
    try:
        _cmd("create_clip", {"track_index": track_index, "clip_index": clip_index, "length": length})
        return f"Created clip at track {track_index}, slot {clip_index} ({length} beats)"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def add_notes_to_clip(track_index: int, clip_index: int, notes: List[Dict[str, Any]]) -> str:
    """Add MIDI notes to a clip.
    
    Args:
        track_index: Track containing the clip
        clip_index: Clip slot index
        notes: List of note dicts with keys:
              - pitch: MIDI note number (36=C1, 60=C4, etc.)
              - start_time: Start position in beats
              - duration: Note length in beats
              - velocity: 0-127
              - mute: boolean (optional, default false)
    
    Example:
        [{"pitch": 36, "start_time": 0.0, "duration": 0.1, "velocity": 120}]
    """
    try:
        result = _cmd("add_notes_to_clip", {
            "track_index": track_index,
            "clip_index": clip_index,
            "notes": notes
        })
        return f"Added {result.get('notes_added', 0)} notes to clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def create_arrangement_clip(track_index: int, start_time: float = 0.0, length: float = 4.0) -> str:
    """Create a clip in the Arrangement view at a specific time position.
    
    Args:
        track_index: Track index to create clip on
        start_time: Position in the arrangement (in beats)
        length: Length of the clip in beats
    """
    try:
        result = _cmd("create_arrangement_clip", {
            "track_index": track_index,
            "start_time": start_time,
            "length": length
        })
        return f"Created arrangement clip at track {track_index}, position {start_time}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def add_notes_to_arrangement(track_index: int, start_time: float = 0.0, notes: List[Dict[str, Any]] = []) -> str:
    """Add MIDI notes to the Arrangement view at a specific position.
    
    Args:
        track_index: Track index
        start_time: Start position in the arrangement (beats)
        notes: List of note dicts with keys: pitch, start_time, duration, velocity, mute
    
    Example:
        add_notes_to_arrangement(track_index=0, start_time=0.0, notes=[{"pitch": 60, "start_time": 0, "duration": 1}])
    """
    try:
        result = _cmd("add_notes_to_arrangement", {
            "track_index": track_index,
            "start_time": start_time,
            "notes": notes
        })
        return f"Added {result.get('notes_added', 0)} notes to arrangement at track {track_index}, position {start_time}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_clip_name(track_index: int, clip_index: int, name: str) -> str:
    """Name a clip.
    
    Args:
        track_index: Track containing the clip
        clip_index: Clip slot index
        name: New name for the clip
    """
    try:
        _cmd("set_clip_name", {"track_index": track_index, "clip_index": clip_index, "name": name})
        return f"Clip at track {track_index}, slot {clip_index} named '{name}'"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def fire_clip(track_index: int, clip_index: int) -> str:
    """Start playing a clip (launch it).
    
    Args:
        track_index: Track containing the clip
        clip_index: Clip slot index
    """
    try:
        _cmd("fire_clip", {"track_index": track_index, "clip_index": clip_index})
        return f"Fired clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def stop_clip(track_index: int, clip_index: int) -> str:
    """Stop a playing clip.
    
    Args:
        track_index: Track containing the clip
        clip_index: Clip slot index
    """
    try:
        _cmd("stop_clip", {"track_index": track_index, "clip_index": clip_index})
        return f"Stopped clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def delete_clip(track_index: int, clip_index: int) -> str:
    """Delete a clip from a clip slot.
    
    Args:
        track_index: Track containing the clip
        clip_index: Clip slot index
    """
    try:
        _cmd("delete_clip", {"track_index": track_index, "clip_index": clip_index})
        return f"Deleted clip at track {track_index}, slot {clip_index}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_clip_notes(track_index: int, clip_index: int) -> str:
    """Get all MIDI notes from a clip.
    
    Returns the notes with their pitches, timings, durations, and velocities.
    Useful for reading existing patterns.
    
    Args:
        track_index: Track containing the clip
        clip_index: Clip slot index
    """
    try:
        return json.dumps(_cmd("get_clip_notes", {
            "track_index": track_index, "clip_index": clip_index
        }), indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def fire_scene(scene_index: int) -> str:
    """Fire (launch) a scene.
    
    Args:
        scene_index: Index of the scene to launch
    """
    try:
        _cmd("fire_scene", {"scene_index": scene_index})
        return f"Fired scene {scene_index}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_scenes() -> str:
    """Get all scenes in the session."""
    try:
        return json.dumps(_cmd("get_scenes"), indent=2)
    except Exception as e:
        return f"Error: {e}"


# ══════════════════════════════════════════════════════════════════
#  MIXING TOOLS
# ══════════════════════════════════════════════════════════════════

@mcp.tool()
def set_volume(track_index: int, volume: float) -> str:
    """Set a track's volume level.
    
    Args:
        track_index: Index of the track
        volume: Volume 0.0 (silent) to 1.0 (0 dB), >1.0 for gain
    """
    try:
        vol = max(0.0, min(1.0, volume))
        _cmd("set_volume", {"track_index": track_index, "volume": vol})
        db = -60 + (vol * 60)  # approximate
        return f"Track {track_index} volume set to {vol:.2f} (~{db:.1f} dB)"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_pan(track_index: int, pan: float) -> str:
    """Set a track's pan position.
    
    Args:
        track_index: Index of the track
        pan: -1.0 (hard left) to 1.0 (hard right), 0.0 = center
    """
    try:
        p = max(-1.0, min(1.0, pan))
        _cmd("set_pan", {"track_index": track_index, "pan": p})
        side = "center" if p == 0 else ("left" if p < 0 else "right")
        return f"Track {track_index} pan set to {p:.2f} ({side})"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_send(track_index: int, send_index: int, value: float) -> str:
    """Set a track's send level to a return track.
    
    Args:
        track_index: Index of the track
        send_index: Index of the send (0 = first return track)
        value: 0.0 to 1.0
    """
    try:
        v = max(0.0, min(1.0, value))
        _cmd("set_send", {"track_index": track_index, "send_index": send_index, "value": v})
        return f"Track {track_index} send {send_index} set to {v:.2f}"
    except Exception as e:
        return f"Error: {e}"


# ══════════════════════════════════════════════════════════════════
#  DEVICE / BROWSER TOOLS
# ══════════════════════════════════════════════════════════════════

@mcp.tool()
def get_browser_tree(category_type: str = "all") -> str:
    """Get the hierarchical browser tree from Ableton's library.
    
    Args:
        category_type: Which category to browse:
                     - 'all' - all categories
                     - 'instruments' - synth/device instruments
                     - 'sounds' - audio presets sorted by type
                     - 'drums' - drum kits and hits
                     - 'audio_effects' - audio effects (reverb, delay, etc.)
                     - 'midi_effects' - MIDI effects (arp, chord, etc.)
    
    Use this to discover what instruments and sounds are available.
    """
    try:
        return json.dumps(_cmd("get_browser_tree", {"category_type": category_type}), indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_browser_items(path: str) -> str:
    """Get items at a specific browser path.
    
    Returns all items (folders and loadable presets) at the given path.
    
    Args:
        path: Browser path like 'instruments', 'sounds/Bass', 'drums', etc.
    
    Examples:
        'instruments' - all built-in instruments
        'sounds/Bass' - all bass presets
        'drums' - drum racks and kits
        'sounds/Pad' - pad presets
        'sounds/Piano & Keys' - piano and electric piano presets
    """
    try:
        return json.dumps(_cmd("get_browser_items_at_path", {"path": path}), indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def search_browser(query: str, category: str = "all") -> str:
    """Search the Ableton browser for instruments/sounds by name.
    
    Args:
        query: Search term (e.g., '808', 'Rhodes', 'Pad', 'Lead')
        category: Where to search ('all', 'instruments', 'sounds', 'drums', 'audio_effects')
    """
    try:
        return json.dumps(_cmd("search_browser", {"query": query, "category": category}), indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def load_instrument(track_index: int, uri: str) -> str:
    """Load an instrument or sound onto a track by its browser URI.
    
    Use 'get_browser_items' or 'search_browser' first to find URIs.
    
    Args:
        track_index: Track to load onto
        uri: Browser URI (e.g., 'query:Sounds#Bass:FileId_423099')
    """
    try:
        result = _cmd("load_browser_item", {"track_index": track_index, "item_uri": uri})
        if result.get("loaded"):
            return f"Loaded '{result.get('item_name', '?')}' on track {track_index}"
        return f"Failed to load item on track {track_index}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def browse_instruments(track_index: int) -> str:
    """Open the browser to instruments section for a track.
    
    This makes it easy to load instruments manually - just click!
    
    Args:
        track_index: Track to prepare for instrument loading
    """
    try:
        result = _cmd("browse_instruments", {"track_index": track_index})
        if result.get("status") == "browser_opened":
            return f"Browser opened to Instruments for track '{result.get('track_name', '?')}'. Click an instrument to load it."
        return result.get("message", "Failed to open browser")
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def load_drum_kit(track_index: int, rack_uri: str = "", kit_path: str = "") -> str:
    """Load a drum rack with a kit onto a track.
    
    Args:
        track_index: Track to load onto
        rack_uri: URI of the drum rack instrument (optional)
        kit_path: Browser path to the drum kit (e.g., 'drums' then finds kit)
    """
    try:
        result = _cmd("load_drum_kit", {
            "track_index": track_index,
            "rack_uri": rack_uri,
            "kit_path": kit_path
        })
        return f"Drum kit loaded on track {track_index}: {result}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def load_effect(track_index: int, effect_uri: str) -> str:
    """Load an audio effect onto a track.
    
    Args:
        track_index: Track to load the effect onto
        effect_uri: Browser URI of the effect (use get_browser_items to find)
    """
    try:
        result = _cmd("load_effect", {"track_index": track_index, "effect_uri": effect_uri})
        return f"Loaded effect '{result.get('effect_name', '?')}' on track {track_index}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_track_devices(track_index: int) -> str:
    """Get all devices (instruments and effects) on a track.
    
    Returns device names, types, and all their parameters with current values.
    
    Args:
        track_index: Track to inspect
    """
    try:
        return json.dumps(_cmd("get_track_devices", {"track_index": track_index}), indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_device_parameters(track_index: int, device_index: int) -> str:
    """Get all parameters of a specific device on a track.
    
    Returns parameter names, current values, min/max ranges.
    Useful before using set_device_parameter.
    
    Args:
        track_index: Track containing the device
        device_index: Index of the device on the track
    """
    try:
        return json.dumps(_cmd("get_device_parameters", {
            "track_index": track_index, "device_index": device_index
        }), indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def set_device_parameter(track_index: int, device_index: int, parameter_index: int, value: float) -> str:
    """Set a parameter value on a device.
    
    Use get_device_parameters first to find parameter indices.
    Typical value ranges are 0.0 to 1.0.
    
    Args:
        track_index: Track containing the device
        device_index: Index of the device (0 = first device)
        parameter_index: Index of the parameter on the device
        value: New value (typically 0.0 to 1.0)
    """
    try:
        result = _cmd("set_device_parameter", {
            "track_index": track_index,
            "device_index": device_index,
            "parameter_index": parameter_index,
            "value": value
        })
        return f"Set '{result.get('parameter_name', '?')}' on '{result.get('device_name', '?')}' to {value}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def export_audio(file_path: str = r"C:\Users\MSI\Desktop\Chibe\export.wav", format: str = "wav", sample_rate: int = 44100, bit_depth: int = 24) -> str:
    """Export the current arrangement to an audio file.
    
    Note: Ableton Live typically requires user confirmation for export.
    This triggers the export dialog or returns instructions.
    
    Args:
        file_path: Output file path
        format: Audio format ('wav', 'aiff', 'mp3')
        sample_rate: Sample rate (44100, 48000, 96000)
        bit_depth: Bit depth (16, 24, 32)
    """
    try:
        result = _cmd("export_audio", {
            "file_path": file_path,
            "format": format,
            "sample_rate": sample_rate,
            "bit_depth": bit_depth
        })
        return f"Export: {result.get('message', 'Export triggered')}\nFile: {result.get('file_path', file_path)}"
    except Exception as e:
        return f"Error: {e}"


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def main():
    """Run the MCP server with SSE transport."""
    from chibe_mcp.run_sse import run_sse
    run_sse()


if __name__ == "__main__":
    main()
