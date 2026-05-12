"""
Chibe Dr. Dre G-Funk Beat Builder
==================================
Complete 8-bar West Coast G-Funk beat in G minor at 92 BPM.
Uses the Chibe MCP server to drive Ableton Live.

Track Layout:
  0: KICK       - 808 Core Kit (swung G-Funk pattern)
  1: SNARE      - 808 rimshot/clap on 2 & 4 with ghost notes
  2: HI-HAT     - Swing 16ths with open hat accents
  3: PERCUSSION - Tambourine, shaker, cowbell
  4: BASS       - 808 melodic bass (Gm7-Cm7-D7-Gm7)
  5: RHODES     - Warm Rhodes chords (Gm7, Cm7, D7, EbMaj7)
  6: SYNTH LEAD - G-Funk lead melody (pentatonic whine)
  7: PADS       - Atmospheric string pad sustains

Chord progression: | Gm7 | Cm7 | D7 | Gm7 | (8 bars total)
"""

import asyncio
import json
import sys
import os

# Ensure chibe is importable
sys.path.insert(0, r"C:\Users\MSI\Desktop\Chibe")

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

# ── Configuration ────────────────────────────────────────────────
MCP_SERVER_URL = os.environ.get("CHIBE_MCP_URL", "http://127.0.0.1:8000/mcp")
TEMPO = 92.0
KEY = "G minor"
TOTAL_BARS = 8
TOTAL_BEATS = TOTAL_BARS * 4.0
BAR = 4.0

# ── MIDI Note Constants ─────────────────────────────────────────
KICK = 36
KICK_SUB = 35
SNARE = 38
RIMSHOT = 37
CLAP = 39
HAT_CLOSED = 42
HAT_OPEN = 46
TAMBOURINE = 54
SHAKER = 70
COWBELL = 56

# G minor scale
G2, G3, G4, G5 = 43, 55, 67, 79
A2, A3, A4 = 45, 57, 69
Bb2, Bb3, Bb4 = 46, 58, 70
C3, C4, C5 = 48, 60, 72
D3, D4, D5 = 50, 62, 74
Eb3, Eb4 = 51, 63
F3, F4, F5 = 53, 65, 77
Fsharp3, Fsharp4, Fsharp5 = 54, 66, 78
Eb5 = 75


# ── Instrument URIs (discovered from Ableton library) ────────────
INST_808_KIT = "query:Drums#FileId_423316"  # 808 Core Kit
INST_808_BASS = "query:Sounds#Bass:FileId_423098"  # 808 Drifter
INST_RHODES = "query:Sounds#Piano%20&%20Keys:FileId_424942"  # E-Piano MKI Mellow
INST_LEAD = "query:Sounds#Synth%20Lead:FileId_422577"  # Basic OG Lead
INST_PAD = "query:Sounds#Pad:FileId_424003"  # Analog Soft Pad


async def call_tool(session, tool_name, arguments=None):
    """Call an MCP tool and return the result text."""
    if arguments is None:
        arguments = {}
    result = await session.call_tool(tool_name, arguments)
    text = result.content[0].text if result.content else "(no content)"
    # Print truncated result
    print(f"  [{tool_name}] -> {text[:100]}")
    return text


async def ensure_track(session, index, name, instrument_uri=None):
    """Create a track if it doesn't exist, name it, optionally load instrument."""
    # Create track at specific index
    await call_tool(session, "create_midi_track", {"index": index})
    await call_tool(session, "set_track_name", {"track_index": index, "name": name})
    
    if instrument_uri:
        result = await call_tool(session, "load_instrument", {
            "track_index": index,
            "uri": instrument_uri
        })
        print(f"  >>> {name}: instrument loaded")


async def make_clip(session, track, clip_index, notes, name, length=TOTAL_BEATS):
    """Create a clip, add notes, name it."""
    await call_tool(session, "create_clip", {
        "track_index": track, "clip_index": clip_index, "length": length
    })
    await call_tool(session, "add_notes_to_clip", {
        "track_index": track, "clip_index": clip_index, "notes": notes
    })
    await call_tool(session, "set_clip_name", {
        "track_index": track, "clip_index": clip_index, "name": name
    })


# ══════════════════════════════════════════════════════════════════
#  PATTERN GENERATORS
# ══════════════════════════════════════════════════════════════════

def generate_kick_pattern():
    """Classic Dr. Dre swung kick pattern."""
    notes = []
    for bar in range(TOTAL_BARS):
        off = bar * BAR
        # Main kick on 1
        notes.append({"pitch": KICK, "start_time": off + 0.0, "duration": 0.15, "velocity": 127, "mute": False})
        notes.append({"pitch": KICK_SUB, "start_time": off + 0.0, "duration": 0.6, "velocity": 100, "mute": False})
        # "&" of 2 (swung)
        notes.append({"pitch": KICK, "start_time": off + 1.5, "duration": 0.12, "velocity": 105, "mute": False})
        # Beat 3
        notes.append({"pitch": KICK, "start_time": off + 2.0, "duration": 0.15, "velocity": 120, "mute": False})
        notes.append({"pitch": KICK_SUB, "start_time": off + 2.0, "duration": 0.5, "velocity": 95, "mute": False})
        # "&" of 4 on even bars for variation
        if bar % 2 == 0:
            notes.append({"pitch": KICK, "start_time": off + 3.5, "duration": 0.1, "velocity": 95, "mute": False})
    return notes


def generate_snare_pattern():
    """Rimshot + clap on 2&4 with ghost snares."""
    notes = []
    for bar in range(TOTAL_BARS):
        off = bar * BAR
        # Main backbeat: rimshot + clap on 2 and 4
        for beat in [1.0, 3.0]:
            notes.append({"pitch": RIMSHOT, "start_time": off + beat, "duration": 0.1, "velocity": 118, "mute": False})
            notes.append({"pitch": CLAP, "start_time": off + beat, "duration": 0.08, "velocity": 112, "mute": False})
        # Ghost snares (quiet) on "e" and "ah"
        notes.append({"pitch": SNARE, "start_time": off + 0.75, "duration": 0.05, "velocity": 50, "mute": False})
        notes.append({"pitch": SNARE, "start_time": off + 1.75, "duration": 0.05, "velocity": 55, "mute": False})
        notes.append({"pitch": SNARE, "start_time": off + 2.75, "duration": 0.05, "velocity": 50, "mute": False})
        notes.append({"pitch": SNARE, "start_time": off + 3.75, "duration": 0.05, "velocity": 55, "mute": False})
        # Snare flam on beat 4 (every 4 bars)
        if bar % 4 == 3:
            notes.append({"pitch": SNARE, "start_time": off + 2.94, "duration": 0.04, "velocity": 65, "mute": False})
    return notes


def generate_hat_pattern():
    """Swing 16th note hi-hats with open hat accents."""
    notes = []
    for bar in range(TOTAL_BARS):
        off = bar * BAR
        # 16th note grid with velocity accent shaping
        sixteenth_positions = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75,
                               2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75]
        for pos in sixteenth_positions:
            beat = pos % 1.0
            if beat == 0.0:
                vel = 108
            elif beat == 0.5:
                vel = 88
            elif beat == 0.75:
                vel = 72
            elif beat == 0.25:
                vel = 78
            else:
                vel = 68
            notes.append({
                "pitch": HAT_CLOSED, "start_time": off + pos,
                "duration": 0.08, "velocity": vel, "mute": False
            })
        # Open hats on "&" of 2 and 4
        notes.append({"pitch": HAT_OPEN, "start_time": off + 1.5, "duration": 0.35, "velocity": 88, "mute": False})
        notes.append({"pitch": HAT_OPEN, "start_time": off + 3.5, "duration": 0.3, "velocity": 92, "mute": False})
        # Hat roll before snare (every 4 bars)
        if bar % 4 == 0:
            notes.append({"pitch": HAT_CLOSED, "start_time": off + 0.875, "duration": 0.05, "velocity": 60, "mute": False})
            notes.append({"pitch": HAT_CLOSED, "start_time": off + 0.9375, "duration": 0.05, "velocity": 55, "mute": False})
    return notes


def generate_perc_pattern():
    """Tambourine on 2&4, shaker 8th notes, cowbell accents."""
    notes = []
    for bar in range(TOTAL_BARS):
        off = bar * BAR
        # Tambourine on 2 and 4
        notes.append({"pitch": TAMBOURINE, "start_time": off + 1.0, "duration": 0.12, "velocity": 98, "mute": False})
        notes.append({"pitch": TAMBOURINE, "start_time": off + 3.0, "duration": 0.12, "velocity": 102, "mute": False})
        # Shaker on 8th notes
        if bar % 2 == 0:
            for eighth in [0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75]:
                notes.append({
                    "pitch": SHAKER, "start_time": off + eighth,
                    "duration": 0.06, "velocity": 55, "mute": False
                })
        # Cowbell on 1 and 3 (every 4 bars)
        if bar % 4 == 0:
            notes.append({"pitch": COWBELL, "start_time": off + 0.0, "duration": 0.1, "velocity": 82, "mute": False})
            notes.append({"pitch": COWBELL, "start_time": off + 2.0, "duration": 0.1, "velocity": 78, "mute": False})
    return notes


def generate_bass_pattern():
    """G-Funk melodic bass - Gm7 | Cm7 | D7 | Gm7."""
    return [
        # ── Bar 1-2: Gm7 ──
        {"pitch": G2, "start_time": 0.0, "duration": 1.75, "velocity": 118, "mute": False},
        {"pitch": A2, "start_time": 1.75, "duration": 0.25, "velocity": 100, "mute": False},
        {"pitch": Bb2, "start_time": 2.0, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": G2, "start_time": 2.5, "duration": 0.5, "velocity": 105, "mute": False},
        {"pitch": D3, "start_time": 3.0, "duration": 0.5, "velocity": 112, "mute": False},
        {"pitch": Bb2, "start_time": 3.5, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": G2, "start_time": 4.0, "duration": 1.5, "velocity": 118, "mute": False},
        {"pitch": A2, "start_time": 5.5, "duration": 0.25, "velocity": 100, "mute": False},
        {"pitch": Bb2, "start_time": 5.75, "duration": 0.25, "velocity": 105, "mute": False},
        {"pitch": C3, "start_time": 6.0, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": D3, "start_time": 6.5, "duration": 0.5, "velocity": 110, "mute": False},
        {"pitch": G2, "start_time": 7.0, "duration": 1.0, "velocity": 115, "mute": False},
        # ── Bar 3-4: Cm7 ──
        {"pitch": C3, "start_time": 8.0, "duration": 1.5, "velocity": 118, "mute": False},
        {"pitch": D3, "start_time": 9.5, "duration": 0.25, "velocity": 100, "mute": False},
        {"pitch": Eb3, "start_time": 9.75, "duration": 0.25, "velocity": 105, "mute": False},
        {"pitch": C3, "start_time": 10.0, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": G3, "start_time": 10.5, "duration": 0.5, "velocity": 110, "mute": False},
        {"pitch": Eb3, "start_time": 11.0, "duration": 0.5, "velocity": 105, "mute": False},
        {"pitch": D3, "start_time": 11.5, "duration": 0.25, "velocity": 100, "mute": False},
        {"pitch": C3, "start_time": 11.75, "duration": 0.25, "velocity": 98, "mute": False},
        {"pitch": C3, "start_time": 12.0, "duration": 2.0, "velocity": 118, "mute": False},
        {"pitch": Bb2, "start_time": 14.0, "duration": 0.5, "velocity": 105, "mute": False},
        {"pitch": C3, "start_time": 14.5, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": D3, "start_time": 15.0, "duration": 0.5, "velocity": 110, "mute": False},
        {"pitch": Eb3, "start_time": 15.5, "duration": 0.5, "velocity": 105, "mute": False},
        # ── Bar 5-6: D7 ──
        {"pitch": D3, "start_time": 16.0, "duration": 1.75, "velocity": 120, "mute": False},
        {"pitch": Eb3, "start_time": 17.75, "duration": 0.25, "velocity": 100, "mute": False},
        {"pitch": Fsharp3, "start_time": 18.0, "duration": 0.5, "velocity": 112, "mute": False},
        {"pitch": A3, "start_time": 18.5, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": D3, "start_time": 19.0, "duration": 0.5, "velocity": 115, "mute": False},
        {"pitch": C3, "start_time": 19.5, "duration": 0.25, "velocity": 100, "mute": False},
        {"pitch": A2, "start_time": 19.75, "duration": 0.25, "velocity": 98, "mute": False},
        {"pitch": D3, "start_time": 20.0, "duration": 1.5, "velocity": 118, "mute": False},
        {"pitch": Fsharp3, "start_time": 21.5, "duration": 0.5, "velocity": 110, "mute": False},
        {"pitch": G3, "start_time": 22.0, "duration": 1.0, "velocity": 115, "mute": False},
        {"pitch": Fsharp3, "start_time": 23.0, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": D3, "start_time": 23.5, "duration": 0.5, "velocity": 105, "mute": False},
        # ── Bar 7-8: Gm7 (resolution) ──
        {"pitch": G2, "start_time": 24.0, "duration": 1.5, "velocity": 118, "mute": False},
        {"pitch": A2, "start_time": 25.5, "duration": 0.25, "velocity": 100, "mute": False},
        {"pitch": Bb2, "start_time": 25.75, "duration": 0.25, "velocity": 105, "mute": False},
        {"pitch": G2, "start_time": 26.0, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": D3, "start_time": 26.5, "duration": 0.5, "velocity": 110, "mute": False},
        {"pitch": Bb2, "start_time": 27.0, "duration": 0.5, "velocity": 105, "mute": False},
        {"pitch": G2, "start_time": 27.5, "duration": 0.25, "velocity": 100, "mute": False},
        {"pitch": A2, "start_time": 27.75, "duration": 0.25, "velocity": 98, "mute": False},
        {"pitch": G2, "start_time": 28.0, "duration": 2.0, "velocity": 120, "mute": False},
        {"pitch": Bb2, "start_time": 30.0, "duration": 1.0, "velocity": 108, "mute": False},
        {"pitch": G2, "start_time": 31.0, "duration": 1.0, "velocity": 115, "mute": False},
    ]


def generate_rhodes_pattern():
    """Warm Rhodes chords: Gm7 - Cm7 - D7 - Gm7/EbMaj7."""
    notes = []
    
    def chord(start, pitches_durs):
        for p, d in pitches_durs:
            notes.append({
                "pitch": p, "start_time": start, "duration": d,
                "velocity": 88, "mute": False
            })
    
    # Bar 1-2: Gm7 (G2, D3, F3, Bb3, D4)
    chord(0.0, [(G2, 4.0), (D3, 4.0), (F3, 4.0), (Bb3, 4.0), (D4, 4.0)])
    chord(4.0, [(G2, 4.0), (D3, 4.0), (F3, 4.0), (Bb3, 4.0), (D4, 4.0)])
    # Bar 3-4: Cm7 (C3, G3, Bb3, Eb4)
    chord(8.0, [(C3, 4.0), (G3, 4.0), (Bb3, 4.0), (Eb4, 4.0)])
    chord(12.0, [(C3, 4.0), (G3, 4.0), (Bb3, 4.0), (Eb4, 4.0)])
    # Bar 5-6: D7 (D3, F#3, A3, C4)
    chord(16.0, [(D3, 4.0), (Fsharp3, 4.0), (A3, 4.0), (C4, 4.0)])
    chord(20.0, [(D3, 4.0), (Fsharp3, 4.0), (A3, 4.0), (C4, 4.0)])
    # Bar 7: Gm7, Bar 7.5: EbMaj7, Bar 8: Gm7
    chord(24.0, [(G2, 2.0), (D3, 2.0), (F3, 2.0), (Bb3, 2.0), (D4, 2.0)])
    chord(26.0, [(Eb3, 2.0), (G3, 2.0), (Bb3, 2.0), (D4, 2.0)])
    chord(28.0, [(G2, 4.0), (D3, 4.0), (F3, 4.0), (Bb3, 4.0), (D4, 4.0)])
    return notes


def generate_lead_pattern():
    """G-Funk whiny lead melody in G minor pentatonic."""
    return [
        # Gm7 section
        {"pitch": D5, "start_time": 0.0, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": F5, "start_time": 0.5, "duration": 0.5, "velocity": 102, "mute": False},
        {"pitch": D5, "start_time": 1.0, "duration": 0.75, "velocity": 110, "mute": False},
        {"pitch": C5, "start_time": 1.75, "duration": 0.25, "velocity": 95, "mute": False},
        {"pitch": Bb4, "start_time": 2.0, "duration": 0.5, "velocity": 105, "mute": False},
        {"pitch": C5, "start_time": 2.5, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": D5, "start_time": 3.0, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": G5, "start_time": 3.5, "duration": 0.5, "velocity": 112, "mute": False},
        {"pitch": F5, "start_time": 4.0, "duration": 0.5, "velocity": 102, "mute": False},
        {"pitch": D5, "start_time": 4.5, "duration": 0.5, "velocity": 98, "mute": False},
        {"pitch": F5, "start_time": 5.0, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": G5, "start_time": 5.5, "duration": 0.5, "velocity": 105, "mute": False},
        {"pitch": D5, "start_time": 6.0, "duration": 1.0, "velocity": 108, "mute": False},
        {"pitch": C5, "start_time": 7.0, "duration": 0.5, "velocity": 98, "mute": False},
        {"pitch": Bb4, "start_time": 7.5, "duration": 0.5, "velocity": 92, "mute": False},
        # Cm7 section
        {"pitch": C5, "start_time": 8.0, "duration": 0.5, "velocity": 105, "mute": False},
        {"pitch": Eb5, "start_time": 8.5, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": D5, "start_time": 9.0, "duration": 0.5, "velocity": 102, "mute": False},
        {"pitch": C5, "start_time": 9.5, "duration": 0.5, "velocity": 95, "mute": False},
        {"pitch": Bb4, "start_time": 10.0, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": C5, "start_time": 10.5, "duration": 0.5, "velocity": 102, "mute": False},
        {"pitch": D5, "start_time": 11.0, "duration": 1.0, "velocity": 108, "mute": False},
        {"pitch": C5, "start_time": 12.0, "duration": 0.5, "velocity": 105, "mute": False},
        {"pitch": G4, "start_time": 12.5, "duration": 0.5, "velocity": 95, "mute": False},
        {"pitch": Bb4, "start_time": 13.0, "duration": 0.5, "velocity": 102, "mute": False},
        {"pitch": C5, "start_time": 13.5, "duration": 0.25, "velocity": 100, "mute": False},
        {"pitch": D5, "start_time": 13.75, "duration": 0.25, "velocity": 102, "mute": False},
        {"pitch": Eb5, "start_time": 14.0, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": D5, "start_time": 14.5, "duration": 0.5, "velocity": 98, "mute": False},
        {"pitch": C5, "start_time": 15.0, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": Bb4, "start_time": 15.5, "duration": 0.25, "velocity": 92, "mute": False},
        {"pitch": C5, "start_time": 15.75, "duration": 0.25, "velocity": 95, "mute": False},
        # D7 section (tension)
        {"pitch": Fsharp5, "start_time": 16.0, "duration": 0.5, "velocity": 110, "mute": False},
        {"pitch": G5, "start_time": 16.5, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": Fsharp5, "start_time": 17.0, "duration": 0.5, "velocity": 105, "mute": False},
        {"pitch": D5, "start_time": 17.5, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": A4, "start_time": 18.0, "duration": 0.5, "velocity": 102, "mute": False},
        {"pitch": C5, "start_time": 18.5, "duration": 0.5, "velocity": 105, "mute": False},
        {"pitch": D5, "start_time": 19.0, "duration": 1.0, "velocity": 110, "mute": False},
        {"pitch": G5, "start_time": 20.0, "duration": 0.5, "velocity": 112, "mute": False},
        {"pitch": Fsharp5, "start_time": 20.5, "duration": 0.5, "velocity": 102, "mute": False},
        {"pitch": G5, "start_time": 21.0, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": A5, "start_time": 21.5, "duration": 0.5, "velocity": 110, "mute": False},
        {"pitch": Fsharp5, "start_time": 22.0, "duration": 1.0, "velocity": 108, "mute": False},
        {"pitch": D5, "start_time": 23.0, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": C5, "start_time": 23.5, "duration": 0.5, "velocity": 95, "mute": False},
        # Gm7 resolution
        {"pitch": D5, "start_time": 24.0, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": F5, "start_time": 24.5, "duration": 0.75, "velocity": 102, "mute": False},
        {"pitch": G5, "start_time": 25.25, "duration": 0.75, "velocity": 110, "mute": False},
        {"pitch": D5, "start_time": 26.0, "duration": 0.5, "velocity": 102, "mute": False},
        {"pitch": F5, "start_time": 26.5, "duration": 0.5, "velocity": 100, "mute": False},
        {"pitch": G5, "start_time": 27.0, "duration": 0.5, "velocity": 108, "mute": False},
        {"pitch": D5, "start_time": 27.5, "duration": 0.5, "velocity": 102, "mute": False},
        {"pitch": G5, "start_time": 28.0, "duration": 1.0, "velocity": 112, "mute": False},
        {"pitch": F5, "start_time": 29.0, "duration": 0.5, "velocity": 98, "mute": False},
        {"pitch": D5, "start_time": 29.5, "duration": 0.5, "velocity": 95, "mute": False},
        {"pitch": G5, "start_time": 30.0, "duration": 0.5, "velocity": 110, "mute": False},
        {"pitch": D5, "start_time": 30.5, "duration": 0.25, "velocity": 102, "mute": False},
        {"pitch": F5, "start_time": 30.75, "duration": 0.25, "velocity": 100, "mute": False},
        {"pitch": G5, "start_time": 31.0, "duration": 1.0, "velocity": 115, "mute": False},
    ]


def generate_pad_pattern():
    """Sustained atmospheric pads following the chord progression."""
    notes = []
    def add(start, pitches, duration):
        for p in pitches:
            notes.append({
                "pitch": p, "start_time": start, "duration": duration,
                "velocity": 72, "mute": False
            })
    # Gm7 (bars 1-2)
    add(0.0, [G3, Bb3, D4, F4], 7.5)
    add(7.5, [G3, Bb3, D4, F4], 0.5)
    # Cm7 (bars 3-4)
    add(8.0, [C4, Eb4, G4, Bb4], 7.5)
    add(15.5, [C4, Eb4, G4, Bb4], 0.5)
    # D7 (bars 5-6)
    add(16.0, [D4, Fsharp4, A4, C5], 7.5)
    add(23.5, [D4, Fsharp4, A4, C5], 0.5)
    # Gm7 -> EbMaj7 -> Gm7 (bars 7-8)
    add(24.0, [G3, Bb3, D4, F4], 2.0)
    add(26.0, [Eb4, G4, Bb4, D5], 2.0)
    add(28.0, [G3, Bb3, D4, F4], 4.0)
    return notes


# ══════════════════════════════════════════════════════════════════
#  MAIN BUILD
# ══════════════════════════════════════════════════════════════════

async def main():
    print("=" * 64)
    print("  CHIBE - Dr. Dre / West Coast G-Funk Beat Builder")
    print(f"  Tempo: {TEMPO} BPM  |  Key: {KEY}  |  {TOTAL_BARS} bars")
    print(f"  Server: {MCP_SERVER_URL}")
    print("=" * 64)

    async with streamable_http_client(MCP_SERVER_URL) as (read, write, gsid):
        async with ClientSession(read, write) as session:
            await session.initialize()
            session_id = gsid()
            print(f"  Connected! Session: {session_id}\n")

            # ── Phase 1: Session Setup ──
            print("─── PHASE 1: Session Setup ───")
            info = json.loads(await call_tool(session, "get_session_info"))
            print(f"  Current BPM: {info.get('tempo')}")
            await call_tool(session, "set_tempo", {"tempo": TEMPO})
            
            # Set loop for 8 bars
            await call_tool(session, "set_loop", {
                "loop_start": 0.0, "loop_length": TOTAL_BEATS, "looping": True
            })
            print("  >>> Loop set to 8 bars")

            # ── Phase 2: Create Tracks with Instruments ──
            print("\n─── PHASE 2: Creating Tracks & Loading Instruments ───")
            
            tracks = [
                (0, "KICK",       INST_808_KIT),
                (1, "SNARE",      INST_808_KIT),
                (2, "HI-HAT",     INST_808_KIT),
                (3, "PERCUSSION", INST_808_KIT),
                (4, "BASS",       INST_808_BASS),
                (5, "RHODES",     INST_RHODES),
                (6, "SYNTH LEAD", INST_LEAD),
                (7, "PADS",       INST_PAD),
            ]
            
            for idx, name, uri in tracks:
                await ensure_track(session, idx, name, uri)

            # ── Phase 3: Program MIDI Patterns ──
            print("\n─── PHASE 3: Programming MIDI Patterns ───")

            print("\n  >> KICK (808 G-Funk pattern)...")
            await make_clip(session, 0, 0, generate_kick_pattern(), "G-Funk Kick")
            
            print("  >> SNARE (rimshot+clap 2&4)...")
            await make_clip(session, 1, 0, generate_snare_pattern(), "G-Funk Snare")
            
            print("  >> HI-HAT (swing 16ths)...")
            await make_clip(session, 2, 0, generate_hat_pattern(), "Swing Hats")
            
            print("  >> PERCUSSION (tambourine, shaker)...")
            await make_clip(session, 3, 0, generate_perc_pattern(), "Perc Groove")
            
            print("  >> BASS (808 melodic G-Funk)...")
            await make_clip(session, 4, 0, generate_bass_pattern(), "G-Funk Bass")
            
            print("  >> RHODES (warm chords)...")
            await make_clip(session, 5, 0, generate_rhodes_pattern(), "Rhodes Chords")
            
            print("  >> SYNTH LEAD (G-Funk whine)...")
            await make_clip(session, 6, 0, generate_lead_pattern(), "G-Funk Lead")
            
            print("  >> PADS (atmosphere)...")
            await make_clip(session, 7, 0, generate_pad_pattern(), "String Pad")

            # ── Phase 4: Mixing ──
            print("\n─── PHASE 4: Mixing ───")
            # Set volumes and pan for each track
            mix = [
                (0, 0.85, 0.0),   # KICK - center, punchy
                (1, 0.80, 0.05),  # SNARE - slightly right
                (2, 0.72, -0.1),  # HI-HAT - slightly left
                (3, 0.65, 0.08),  # PERCUSSION - slightly right
                (4, 0.90, 0.0),   # BASS - center, loud
                (5, 0.75, -0.15), # RHODES - left
                (6, 0.78, 0.12),  # SYNTH LEAD - right
                (7, 0.60, 0.0),   # PADS - center, behind
            ]
            for idx, vol, pan in mix:
                await call_tool(session, "set_volume", {"track_index": idx, "volume": vol})
                await call_tool(session, "set_pan", {"track_index": idx, "pan": pan})
            print("  >>> Mix levels set")

            # ── Phase 5: Fire Clips & Start ──
            print("\n─── PHASE 5: Launching ───")
            for i in range(8):
                await call_tool(session, "fire_clip", {"track_index": i, "clip_index": 0})
            await call_tool(session, "start_playback")
            print("  >>> All clips fired! Playing...")

            # ── Summary ──
            print("\n" + "=" * 64)
            print("  🎵  DR. DRE G-FUNK BEAT COMPLETE!  🎵")
            print("=" * 64)
            print(f"\n  Tempo: {TEMPO} BPM")
            print(f"  Key: {KEY}")
            print(f"  Bars: {TOTAL_BARS}")
            print(f"  Chord Progression: Gm7 | Cm7 | D7 | Gm7")
            print(f"\n  Track Layout:")
            print(f"    0: KICK       - 808 Core Kit (swung pattern)")
            print(f"    1: SNARE      - 808 rimshot+clap 2&4 + ghosts")
            print(f"    2: HI-HAT     - Swing 16ths + open hats")
            print(f"    3: PERCUSSION - Tambourine, shaker, cowbell")
            print(f"    4: BASS       - 808 Drifter melodic bass")
            print(f"    5: RHODES     - E-Piano MKI Mellow chords")
            print(f"    6: SYNTH LEAD - Basic OG Lead (G-Funk whine)")
            print(f"    7: PADS       - Analog Soft Pad atmosphere")
            print(f"\n  Mix: Drums + Bass center, Keys left, Lead right, Pads behind")
            print(f"\n  🎧  Listen in Ableton Live - Session View!")
            print("=" * 64)


if __name__ == "__main__":
    asyncio.run(main())
