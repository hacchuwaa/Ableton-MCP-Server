"""
Chibe Remote Script for Ableton Live
=====================================
Enhanced Ableton Remote Script with comprehensive Live API access.
Provides a socket-based API for the Chibe MCP server to communicate with Ableton Live.

Features:
- Session control (tempo, playback, time signature)
- Track management (create, delete, rename, duplicate, route)
- Clip management (create, edit notes, launch, stop)
- Device management (browse, load, parameter control)
- Mixing (volume, pan, sends, solo, mute, arm)
- Browser integration (browse, search, load instruments/effects)
"""

from __future__ import absolute_import, print_function, unicode_literals
from _Framework.ControlSurface import ControlSurface
import socket
import json
import threading
import time
import traceback

try:
    import Queue as queue  # Python 2
except ImportError:
    import queue  # Python 3

DEFAULT_PORT = 9877
HOST = "localhost"


def create_instance(c_instance):
    return ChibeRemoteScript(c_instance)


# ─── MIDI NOTE CONSTANTS ──────────────────────────────────────────
NOTE_NAMES = {
    36: "Kick", 35: "Kick2", 38: "Snare", 37: "Rimshot",
    39: "Clap", 40: "Snare2", 42: "HH Closed", 46: "HH Open",
    44: "HH Pedal", 54: "Tambourine", 56: "Cowbell", 70: "Shaker",
    76: "Hi Conga", 77: "Low Conga", 78: "Hi Timbale", 79: "Low Timbale"
}


class ChibeRemoteScript(ControlSurface):
    """Enhanced Chibe Remote Script for Ableton Live."""

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self.log_message("Chibe Remote Script initializing...")
        self._server = None
        self._running = False
        self._server_thread = None
        self._song = self.song()
        self.start_server()
        self.log_message("Chibe Remote Script initialized")
        self.show_message("Chibe: Listening on port " + str(DEFAULT_PORT))

    # ── Lifecycle ─────────────────────────────────────────────────

    def disconnect(self):
        self.log_message("Chibe disconnecting...")
        self._running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(1.0)
        ControlSurface.disconnect(self)
        self.log_message("Chibe disconnected")

    def start_server(self):
        try:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind((HOST, DEFAULT_PORT))
            self._server.listen(5)
            self._running = True
            self._server_thread = threading.Thread(target=self._server_loop)
            self._server_thread.daemon = True
            self._server_thread.start()
            self.log_message("Server started on port " + str(DEFAULT_PORT))
        except Exception as e:
            self.log_message("Error starting server: " + str(e))

    def _server_loop(self):
        try:
            self._server.settimeout(1.0)
            while self._running:
                try:
                    client, addr = self._server.accept()
                    self.log_message("Client connected from " + str(addr))
                    t = threading.Thread(target=self._handle_client, args=(client,))
                    t.daemon = True
                    t.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self._running:
                        self.log_message("Accept error: " + str(e))
                    time.sleep(0.5)
        except Exception as e:
            self.log_message("Server loop error: " + str(e))

    def _handle_client(self, client):
        self.log_message("Client handler started")
        client.settimeout(None)
        buffer = ""
        try:
            while self._running:
                try:
                    data = client.recv(8192)
                    if not data:
                        break
                    try:
                        buffer += data.decode("utf-8")
                    except AttributeError:
                        buffer += data
                    try:
                        command = json.loads(buffer)
                        buffer = ""
                        self.log_message("Cmd: " + str(command.get("type", "?")))
                        response = self._process_command(command)
                        try:
                            client.sendall(json.dumps(response).encode("utf-8"))
                        except AttributeError:
                            client.sendall(json.dumps(response))
                    except ValueError:
                        continue
                except Exception as e:
                    self.log_message("Client error: " + str(e))
                    self.log_message(traceback.format_exc())
                    err_resp = {"status": "error", "message": str(e)}
                    try:
                        client.sendall(json.dumps(err_resp).encode("utf-8"))
                    except AttributeError:
                        client.sendall(json.dumps(err_resp))
                    if not isinstance(e, ValueError):
                        break
        except Exception as e:
            self.log_message("Client handler fatal: " + str(e))
        finally:
            try:
                client.close()
            except Exception:
                pass
            self.log_message("Client handler ended")

    # ── Command Router ────────────────────────────────────────────

    def _process_command(self, command):
        cmd_type = command.get("type", "")
        params = command.get("params", {})
        response = {"status": "success", "result": {}}

        try:
            # Read-only commands (fast path, no main thread needed)
            read_commands = {
                "get_session_info": lambda: self._get_session_info(),
                "get_track_info": lambda: self._get_track_info(params.get("track_index", 0)),
                "get_tracks_info": lambda: self._get_tracks_info(),
                "get_browser_tree": lambda: self._get_browser_tree(params.get("category_type", "all")),
                "get_browser_items_at_path": lambda: self._get_browser_items_at_path(params.get("path", "")),
                "get_browser_item": lambda: self._get_browser_item(params.get("uri", ""), params.get("path", "")),
                "get_track_devices": lambda: self._get_track_devices(params.get("track_index", 0)),
                "get_device_parameters": lambda: self._get_device_parameters(params.get("track_index", 0), params.get("device_index", 0)),
                "get_clip_notes": lambda: self._get_clip_notes(params.get("track_index", 0), params.get("clip_index", 0)),
                "search_browser": lambda: self._search_browser(params.get("query", ""), params.get("category", "all")),
                "get_plugins_info": lambda: self._get_plugins_info(),
                "get_master_info": lambda: self._get_master_info(),
                "get_master_devices": lambda: self._get_master_devices(),
                # "scan_library" - enhanced browser scan
                "scan_library": lambda: self._scan_library(params.get("category", "all"), params.get("max_depth", 2)),
            }
            if cmd_type in read_commands:
                response["result"] = read_commands[cmd_type]()
                return response

            # State-modifying commands (must run on main thread)
            modifying_commands = {
                "create_midi_track": lambda: self._create_midi_track(params.get("index", -1)),
                "create_audio_track": lambda: self._create_audio_track(params.get("index", -1)),
                "delete_track": lambda: self._delete_track(params.get("track_index", 0)),
                "duplicate_track": lambda: self._duplicate_track(params.get("track_index", 0)),
                "set_track_name": lambda: self._set_track_name(params.get("track_index", 0), params.get("name", "")),
                "create_clip": lambda: self._create_clip(params.get("track_index", 0), params.get("clip_index", 0), params.get("length", 4.0)),
                "add_notes_to_clip": lambda: self._add_notes_to_clip(params.get("track_index", 0), params.get("clip_index", 0), params.get("notes", [])),
                "set_clip_name": lambda: self._set_clip_name(params.get("track_index", 0), params.get("clip_index", 0), params.get("name", "")),
                "set_tempo": lambda: self._set_tempo(params.get("tempo", 120.0)),
                "fire_clip": lambda: self._fire_clip(params.get("track_index", 0), params.get("clip_index", 0)),
                "stop_clip": lambda: self._stop_clip(params.get("track_index", 0), params.get("clip_index", 0)),
                "start_playback": lambda: self._start_playback(),
                "stop_playback": lambda: self._stop_playback(),
                "load_browser_item": lambda: self._load_browser_item(params.get("track_index", 0), params.get("item_uri", "")),
                "set_volume": lambda: self._set_volume(params.get("track_index", 0), params.get("volume", 0.8)),
                "set_pan": lambda: self._set_pan(params.get("track_index", 0), params.get("pan", 0.0)),
                "arm_track": lambda: self._arm_track(params.get("track_index", 0), params.get("arm", True)),
                "set_track_solo": lambda: self._set_track_solo(params.get("track_index", 0), params.get("solo", True)),
                "set_track_mute": lambda: self._set_track_mute(params.get("track_index", 0), params.get("mute", True)),
                "set_device_parameter": lambda: self._set_device_parameter(params.get("track_index", 0), params.get("device_index", 0), params.get("parameter_index", 0), params.get("value", 0.0)),
                "set_send": lambda: self._set_send(params.get("track_index", 0), params.get("send_index", 0), params.get("value", 0.0)),
                "set_session_focus_point": lambda: self._set_session_focus_point(params.get("track_index", 0), params.get("clip_index", 0)),
                "load_drum_kit": lambda: self._load_drum_kit(params.get("track_index", 0), params.get("rack_uri", ""), params.get("kit_path", "")),
                "load_effect": lambda: self._load_effect(params.get("track_index", 0), params.get("effect_uri", "")),
                "delete_clip": lambda: self._delete_clip(params.get("track_index", 0), params.get("clip_index", 0)),
                "get_scenes": lambda: self._get_scenes(),
                "fire_scene": lambda: self._fire_scene(params.get("scene_index", 0)),
                "set_loop": lambda: self._set_loop(params.get("loop_start", 0.0), params.get("loop_length", 8.0), params.get("looping", True)),
                # Master track
                "set_master_volume": lambda: self._set_master_volume(params.get("volume", 0.8)),
                "set_master_pan": lambda: self._set_master_pan(params.get("pan", 0.0)),
                "set_master_device_parameter": lambda: self._set_master_device_parameter(params.get("device_index", 0), params.get("parameter_index", 0), params.get("value", 0.0)),
                # Track routing
                "set_track_output": lambda: self._set_track_output(params.get("track_index", 0), params.get("output_type", "master"), params.get("output_index", 0)),
            }

            if cmd_type in modifying_commands:
                q = queue.Queue()

                def task():
                    try:
                        result = modifying_commands[cmd_type]()
                        q.put(result)
                    except Exception as e:
                        q.put(e)

                self.log_message("Scheduling on main thread: " + cmd_type)
                self.schedule_message(1, task)
                result = q.get(timeout=30)
                if isinstance(result, Exception):
                    raise result
                response["result"] = result
            else:
                response["status"] = "error"
                response["message"] = "Unknown command: " + cmd_type

        except queue.Empty:
            response["status"] = "error"
            response["message"] = "Command timed out: " + cmd_type
        except Exception as e:
            self.log_message("Error processing command: " + str(e))
            self.log_message(traceback.format_exc())
            response["status"] = "error"
            response["message"] = str(e)

        return response

    # ══════════════════════════════════════════════════════════════
    #  COMMAND IMPLEMENTATIONS
    # ══════════════════════════════════════════════════════════════

    # ── Session Info ──────────────────────────────────────────────

    def _get_session_info(self):
        song = self._song
        try:
            sig_num = getattr(song, 'signature_numerator', 4)
            sig_den = getattr(song, 'signature_denominator', 4)
        except Exception:
            sig_num, sig_den = 4, 4
        try:
            master_vol = song.master_track.mixer_device.volume.value
        except Exception:
            master_vol = 0.8
        return {
            "tempo": song.tempo,
            "signature_numerator": sig_num,
            "signature_denominator": sig_den,
            "track_count": len(song.tracks),
            "return_track_count": len(song.return_tracks),
            "scene_count": len(song.scenes),
            "is_playing": song.is_playing,
            "current_song_time": song.current_song_time,
            "loop_on": song.loop,
            "loop_start": song.loop_start,
            "loop_length": song.loop_length,
            "punch_in": song.punch_in,
            "punch_out": song.punch_out,
            "master_volume": master_vol,
        }

    def _get_track_info(self, track_index):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range: " + str(track_index))
        track = song.tracks[track_index]
        return self._track_to_dict(track)

    def _get_tracks_info(self):
        return {"tracks": [self._track_to_dict(t) for t in self._song.tracks]}

    def _track_to_dict(self, track):
        has_audio = hasattr(track, "has_audio_input")
        return {
            "name": track.name,
            "index": list(self._song.tracks).index(track) if track in self._song.tracks else -1,
            "is_foldable": hasattr(track, "is_foldable") and track.is_foldable,
            "is_grouped": hasattr(track, "is_grouped") and track.is_grouped,
            "has_midi_input": hasattr(track, "has_midi_input") and track.has_midi_input,
            "has_audio_input": hasattr(track, "has_audio_input") and track.has_audio_input,
            "color": track.color,
            "mute": track.mute,
            "solo": track.solo,
            "arm": track.arm if hasattr(track, "arm") else False,
            "volume": track.mixer_device.volume.value,
            "pan": track.mixer_device.panning.value,
            "device_count": len(track.devices),
            "clip_count": len(track.clip_slots) if hasattr(track, "clip_slots") else 0,
            "devices": [d.name for d in track.devices],
        }

    # ── Track Management ──────────────────────────────────────────

    def _create_midi_track(self, index):
        song = self._song
        track = song.create_midi_track(index)
        return {"name": track.name, "index": list(song.tracks).index(track)}

    def _create_audio_track(self, index):
        song = self._song
        track = song.create_audio_track(index)
        return {"name": track.name, "index": list(song.tracks).index(track)}

    def _delete_track(self, track_index):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        # Can't delete last track
        if len(song.tracks) <= 1:
            raise RuntimeError("Cannot delete the last remaining track")
        track = song.tracks[track_index]
        name = track.name
        song.delete_track(track_index)
        return {"deleted_track": name, "track_index": track_index}

    def _duplicate_track(self, track_index):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        song.duplicate_track(track)
        idx = list(song.tracks).index(track) + 1
        if idx < len(song.tracks):
            return {"name": song.tracks[idx].name, "index": idx}
        return {"name": "duplicate", "index": -1}

    def _set_track_name(self, track_index, name):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        song.tracks[track_index].name = name
        return {"name": name, "track_index": track_index}

    def _set_track_solo(self, track_index, solo):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        song.tracks[track_index].solo = solo
        return {"track_index": track_index, "solo": solo}

    def _set_track_mute(self, track_index, mute):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        song.tracks[track_index].mute = mute
        return {"track_index": track_index, "mute": mute}

    def _arm_track(self, track_index, arm):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if hasattr(track, "arm"):
            track.arm = arm
        return {"track_index": track_index, "arm": arm}

    # ── Mixing ────────────────────────────────────────────────────

    def _set_volume(self, track_index, volume):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        song.tracks[track_index].mixer_device.volume.value = max(0.0, min(1.0, volume))
        return {"track_index": track_index, "volume": volume}

    def _set_pan(self, track_index, pan):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        song.tracks[track_index].mixer_device.panning.value = max(-1.0, min(1.0, pan))
        return {"track_index": track_index, "pan": pan}

    def _set_send(self, track_index, send_index, value):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if send_index < len(track.mixer_device.sends):
            track.mixer_device.sends[send_index].value = max(0.0, min(1.0, value))
        return {"track_index": track_index, "send_index": send_index, "value": value}

    def _set_session_focus_point(self, track_index, clip_index):
        song = self._song
        if track_index >= 0 and track_index < len(song.tracks):
            try:
                song.view.selected_track = song.tracks[track_index]
            except Exception:
                pass
        try:
            if clip_index >= 0:
                song.view.selected_scene = song.scenes[clip_index]
        except Exception:
            pass
        return {"track_index": track_index, "clip_index": clip_index}

    # ── Master Track ──────────────────────────────────────────────

    def _set_master_volume(self, volume):
        song = self._song
        song.master_track.mixer_device.volume.value = max(0.0, min(1.0, volume))
        return {"volume": volume}

    def _set_master_pan(self, pan):
        song = self._song
        song.master_track.mixer_device.panning.value = max(-1.0, min(1.0, pan))
        return {"pan": pan}

    def _get_master_info(self):
        song = self._song
        master = song.master_track
        info = {
            "volume": master.mixer_device.volume.value,
            "pan": master.mixer_device.panning.value,
            "device_count": len(master.devices),
            "devices": [d.name for d in master.devices],
        }
        return info

    def _get_master_devices(self):
        """Get all devices on the master track (for mastering chain)."""
        song = self._song
        master = song.master_track
        devices = []
        for idx, device in enumerate(master.devices):
            d = {
                "index": idx,
                "name": device.name,
                "type": self._get_device_type(device),
                "class_name": device.class_name,
            }
            params = []
            if hasattr(device, "parameters"):
                for pi, param in enumerate(device.parameters):
                    if param and hasattr(param, "name") and param.name:
                        params.append({
                            "index": pi,
                            "name": param.name,
                            "value": param.value,
                            "min": param.min,
                            "max": param.max,
                            "is_quantized": param.is_quantized if hasattr(param, "is_quantized") else False,
                        })
            d["parameters"] = params
            devices.append(d)
        return {"devices": devices}

    def _set_master_device_parameter(self, device_index, parameter_index, value):
        """Set a parameter on a master track device."""
        song = self._song
        master = song.master_track
        if device_index < 0 or device_index >= len(master.devices):
            raise IndexError("Device index out of range")
        device = master.devices[device_index]
        if parameter_index < 0 or parameter_index >= len(device.parameters):
            raise IndexError("Parameter index out of range")
        param = device.parameters[parameter_index]
        if param:
            try:
                param.value = value
            except Exception:
                param.value = int(value)
        return {
            "device_name": device.name,
            "parameter_name": param.name if param else "?",
            "value": value,
        }

    # ── Track Routing ─────────────────────────────────────────────

    def _set_track_output(self, track_index, output_type="master", output_index=0):
        """Set a track's output routing.
        output_type: 'master', 'group', 'track'
        """
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        # Get available outputs
        outputs = track.available_output_routing_types
        target = None
        for o in outputs:
            name = str(o).lower()
            if output_type == "master" and "master" in name:
                target = o
                break
            elif output_type == "sends_only" and "send" in name:
                target = o
                break
        if target:
            track.output_routing_type = target
        return {"track_index": track_index, "output": output_type}

    # ── Plugin / VST Scanning ─────────────────────────────────────

    def _get_plugins_info(self):
        """Get information about available plugins in the browser."""
        app = self.application()
        if not app or not hasattr(app, "browser") or app.browser is None:
            raise RuntimeError("Browser not available")
        # List plugin categories from Packs/Plugins
        plugins = []
        try:
            if hasattr(app.browser, "instruments") and app.browser.instruments:
                for child in app.browser.instruments.children:
                    info = {
                        "name": child.name,
                        "is_folder": hasattr(child, "children") and bool(child.children),
                        "is_loadable": hasattr(child, "is_loadable") and child.is_loadable,
                        "uri": child.uri if hasattr(child, "uri") else None,
                    }
                    # Recursively get sub-items (limited depth)
                    if info["is_folder"] and hasattr(child, "children"):
                        sub_items = []
                        for sub in list(child.children)[:20]:
                            sub_items.append(sub.name)
                        info["contains"] = sub_items
                    plugins.append(info)
        except Exception as e:
            self.log_message("Error scanning plugins: " + str(e))
        return {"plugins": plugins, "count": len(plugins)}

    def _scan_library(self, category="all", max_depth=2):
        """Fast scan the Ableton library for loadable instruments/sounds.
        
        Returns a flat list of all loadable items for quick searching.
        Caches results per category for speed.
        """
        app = self.application()
        if not app or not hasattr(app, "browser") or app.browser is None:
            raise RuntimeError("Browser not available")

        start_time = time.time()
        results = []

        categories_to_scan = []
        if category == "all":
            for cat_name in ["instruments", "sounds", "drums", "audio_effects"]:
                if hasattr(app.browser, cat_name):
                    categories_to_scan.append((cat_name, getattr(app.browser, cat_name)))
        elif hasattr(app.browser, category):
            categories_to_scan.append((category, getattr(app.browser, category)))

        def scan(item, depth=0, path=""):
            if not item or depth > max_depth:
                return
            name = item.name if hasattr(item, "name") else ""
            is_loadable = hasattr(item, "is_loadable") and item.is_loadable
            is_folder = hasattr(item, "children") and bool(item.children)
            uri = item.uri if hasattr(item, "uri") else None

            entry = {
                "name": name,
                "category": category,
                "path": path,
                "is_loadable": is_loadable,
                "is_folder": is_folder,
                "uri": uri,
                "depth": depth,
            }
            results.append(entry)

            if is_folder and depth < max_depth and hasattr(item, "children"):
                for child in item.children:
                    child_path = path + "/" + child.name if path else child.name
                    scan(child, depth + 1, child_path)

        for cat_name, cat_root in categories_to_scan:
            scan(cat_root, 0, cat_name)

        elapsed = time.time() - start_time
        return {
            "category": category,
            "items": results,
            "count": len(results),
            "scan_time_ms": int(elapsed * 1000),
        }

    # ── Device Management ─────────────────────────────────────────

    def _get_track_devices(self, track_index):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        devices = []
        for idx, device in enumerate(track.devices):
            d = {
                "index": idx,
                "name": device.name,
                "type": self._get_device_type(device),
                "class_name": device.class_name,
            }
            params = []
            if hasattr(device, "parameters"):
                for pi, param in enumerate(device.parameters):
                    if param and hasattr(param, "name") and param.name:
                        params.append({
                            "index": pi,
                            "name": param.name,
                            "value": param.value,
                            "min": param.min,
                            "max": param.max,
                            "is_quantized": param.is_quantized if hasattr(param, "is_quantized") else False,
                        })
            d["parameters"] = params
            devices.append(d)
        return {"track_index": track_index, "devices": devices}

    def _get_device_parameters(self, track_index, device_index):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index out of range")
        device = track.devices[device_index]
        params = []
        for pi, param in enumerate(device.parameters):
            if param and hasattr(param, "name") and param.name:
                params.append({
                    "index": pi,
                    "name": param.name,
                    "value": param.value,
                    "min": param.min,
                    "max": param.max,
                    "is_quantized": param.is_quantized if hasattr(param, "is_quantized") else False,
                })
        return {"track_index": track_index, "device_index": device_index, "device_name": device.name, "parameters": params}

    def _set_device_parameter(self, track_index, device_index, parameter_index, value):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index out of range")
        device = track.devices[device_index]
        if parameter_index < 0 or parameter_index >= len(device.parameters):
            raise IndexError("Parameter index out of range")
        param = device.parameters[parameter_index]
        if param:
            try:
                param.value = value
            except Exception:
                # Some params need int values
                param.value = int(value)
        return {
            "track_index": track_index,
            "device_name": device.name,
            "parameter_name": param.name if param else "?",
            "value": value,
        }

    def _load_effect(self, track_index, effect_uri):
        """Load an audio effect onto a track by its browser URI."""
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        app = self.application()
        item = self._find_browser_item_by_uri(app.browser, effect_uri)
        if not item:
            raise ValueError("Effect with URI '{}' not found".format(effect_uri))
        song.view.selected_track = song.tracks[track_index]
        app.browser.load_item(item)
        return {"loaded": True, "effect_name": item.name, "track_index": track_index}

    def _load_drum_kit(self, track_index, rack_uri, kit_path):
        """Load a drum rack from URI, then load a kit from path."""
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        app = self.application()
        track = song.tracks[track_index]
        song.view.selected_track = track

        # Step 1: Load the drum rack
        if rack_uri:
            item = self._find_browser_item_by_uri(app.browser, rack_uri)
            if item:
                app.browser.load_item(item)

        # Step 2: Find and load kit from path
        if kit_path:
            parts = kit_path.split("/")
            current = None
            if parts[0].lower() in ["drums", "instruments", "sounds"]:
                cat = parts[0].lower()
                if cat == "drums" and hasattr(app.browser, "drums"):
                    current = app.browser.drums
                elif cat == "instruments" and hasattr(app.browser, "instruments"):
                    current = app.browser.instruments
                elif cat == "sounds" and hasattr(app.browser, "sounds"):
                    current = app.browser.sounds
            if current:
                for part in parts[1:]:
                    found = False
                    for child in current.children:
                        if child.name.lower() == part.lower():
                            current = child
                            found = True
                            break
                    if not found:
                        break
                if current and hasattr(current, "is_loadable") and current.is_loadable:
                    app.browser.load_item(current)
                    return {"loaded": True, "item_name": current.name, "track_index": track_index}

        return {"loaded": True, "track_index": track_index}

    def _get_device_type(self, device):
        """Categorize a device by type."""
        class_name = device.class_name.lower() if hasattr(device, "class_name") else ""
        if "instrument" in class_name or any(x in class_name for x in ["operator", "analog", "collision", "electric", "tension", "impulse", "drum"]):
            return "instrument"
        if "effect" in class_name or any(x in class_name for x in ["reverb", "delay", "compressor", "filter", "eq", "chorus", "flanger"]):
            return "audio_effect"
        if "midi" in class_name:
            return "midi_effect"
        return "other"

    # ── Clip Management ───────────────────────────────────────────

    def _create_clip(self, track_index, clip_index, length):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip slot index out of range")
        slot = track.clip_slots[clip_index]
        if slot.has_clip:
            slot.delete_clip()
        slot.create_clip(length)
        return {"track_index": track_index, "clip_index": clip_index, "length": length}

    def _delete_clip(self, track_index, clip_index):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip slot index out of range")
        slot = track.clip_slots[clip_index]
        if slot.has_clip:
            slot.delete_clip()
        return {"track_index": track_index, "clip_index": clip_index, "deleted": True}

    def _add_notes_to_clip(self, track_index, clip_index, notes):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip slot index out of range")
        slot = track.clip_slots[clip_index]
        if not slot.has_clip:
            raise RuntimeError("No clip at this slot")
        clip = slot.clip
        for note_data in notes:
            try:
                pitch = int(note_data.get("pitch", 60))
                start = float(note_data.get("start_time", 0.0))
                duration = float(note_data.get("duration", 0.25))
                velocity = int(note_data.get("velocity", 100))
                muted = bool(note_data.get("mute", False))
                clip.set_notes([(pitch, start, duration, velocity, muted)])
            except Exception as e:
                self.log_message("Error adding note: " + str(e))
        return {"track_index": track_index, "clip_index": clip_index, "notes_added": len(notes)}

    def _get_clip_notes(self, track_index, clip_index):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip slot index out of range")
        slot = track.clip_slots[clip_index]
        if not slot.has_clip:
            return {"track_index": track_index, "clip_index": clip_index, "notes": []}
        clip = slot.clip
        notes_data = clip.get_notes(0, 0, 128, clip.length)
        notes = []
        for pitch, start, duration, velocity, muted in notes_data:
            notes.append({
                "pitch": pitch,
                "start_time": start,
                "duration": duration,
                "velocity": velocity,
                "mute": muted
            })
        return {"track_index": track_index, "clip_index": clip_index, "notes": notes, "clip_length": clip.length}

    def _set_clip_name(self, track_index, clip_index, name):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip slot index out of range")
        slot = track.clip_slots[clip_index]
        if slot.has_clip:
            slot.clip.name = name
        return {"track_index": track_index, "clip_index": clip_index, "name": name}

    def _fire_clip(self, track_index, clip_index):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip slot index out of range")
        slot = track.clip_slots[clip_index]
        slot.fire()
        return {"track_index": track_index, "clip_index": clip_index, "fired": True}

    def _stop_clip(self, track_index, clip_index):
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip slot index out of range")
        slot = track.clip_slots[clip_index]
        slot.stop()
        return {"track_index": track_index, "clip_index": clip_index, "stopped": True}

    # ── Playback ──────────────────────────────────────────────────

    def _set_tempo(self, tempo):
        self._song.tempo = tempo
        return {"tempo": tempo}

    def _start_playback(self):
        self._song.start_playback()
        return {"playing": True}

    def _stop_playback(self):
        self._song.stop_playback()
        return {"playing": False}

    def _set_loop(self, loop_start, loop_length, looping):
        self._song.loop_start = loop_start
        self._song.loop_length = loop_length
        self._song.loop = looping
        return {"loop_start": loop_start, "loop_length": loop_length, "looping": looping}

    # ── Scenes ────────────────────────────────────────────────────

    def _get_scenes(self):
        scenes = []
        for i, scene in enumerate(self._song.scenes):
            scenes.append({
                "index": i,
                "name": scene.name,
                "color": scene.color,
            })
        return {"scenes": scenes}

    def _fire_scene(self, scene_index):
        if scene_index < 0 or scene_index >= len(self._song.scenes):
            raise IndexError("Scene index out of range")
        self._song.scenes[scene_index].fire()
        return {"scene_index": scene_index, "fired": True}

    # ── Browser ───────────────────────────────────────────────────

    def _get_browser_tree(self, category_type="all"):
        app = self.application()
        if not app or not hasattr(app, "browser") or app.browser is None:
            raise RuntimeError("Browser is not available")

        result = {"type": category_type, "categories": []}

        def process_item(item, depth=0):
            if not item:
                return None
            data = {
                "name": item.name if hasattr(item, "name") else "Unknown",
                "is_folder": hasattr(item, "children") and bool(item.children),
                "is_device": hasattr(item, "is_device") and item.is_device,
                "is_loadable": hasattr(item, "is_loadable") and item.is_loadable,
                "uri": item.uri if hasattr(item, "uri") else None,
                "children": [],
            }
            # Recurse into children (up to depth 3)
            if item.children and depth < 3:
                for child in item.children[:50]:  # Limit to 50 per folder
                    child_data = process_item(child, depth + 1)
                    if child_data:
                        data["children"].append(child_data)
            return data

        categories_map = {
            "instruments": ("instruments", hasattr(app.browser, "instruments")),
            "sounds": ("sounds", hasattr(app.browser, "sounds")),
            "drums": ("drums", hasattr(app.browser, "drums")),
            "audio_effects": ("audio_effects", hasattr(app.browser, "audio_effects")),
            "midi_effects": ("midi_effects", hasattr(app.browser, "midi_effects")),
        }

        if category_type == "all":
            for name, (attr, exists) in categories_map.items():
                if exists:
                    item = process_item(getattr(app.browser, attr))
                    if item:
                        result["categories"].append(item)
        elif category_type in categories_map:
            name, exists = categories_map[category_type]
            if exists:
                item = process_item(getattr(app.browser, name))
                if item:
                    result["categories"].append(item)

        return result

    def _get_browser_items_at_path(self, path):
        app = self.application()
        if not app or not hasattr(app, "browser") or app.browser is None:
            raise RuntimeError("Browser is not available")

        if not path:
            raise ValueError("Path is required")

        parts = path.split("/")
        current = None

        # Navigate to category root
        cat = parts[0].lower()
        if cat == "instruments" and hasattr(app.browser, "instruments"):
            current = app.browser.instruments
        elif cat == "sounds" and hasattr(app.browser, "sounds"):
            current = app.browser.sounds
        elif cat == "drums" and hasattr(app.browser, "drums"):
            current = app.browser.drums
        elif cat == "audio_effects" and hasattr(app.browser, "audio_effects"):
            current = app.browser.audio_effects
        elif cat == "midi_effects" and hasattr(app.browser, "midi_effects"):
            current = app.browser.midi_effects
        else:
            raise ValueError("Unknown category: " + cat)

        # Navigate through subfolders
        for part in parts[1:]:
            if not part:
                continue
            found = False
            if hasattr(current, "children"):
                for child in current.children:
                    if child.name.lower() == part.lower():
                        current = child
                        found = True
                        break
            if not found:
                raise ValueError("Path part '{}' not found".format(part))

        # Get items at this level
        items = []
        if hasattr(current, "children"):
            for child in current.children:
                items.append({
                    "name": child.name,
                    "is_folder": hasattr(child, "children") and bool(child.children),
                    "is_device": hasattr(child, "is_device") and child.is_device,
                    "is_loadable": hasattr(child, "is_loadable") and child.is_loadable,
                    "uri": child.uri if hasattr(child, "uri") else None,
                })

        return {"path": path, "items": items}

    def _get_browser_item(self, uri, path):
        app = self.application()
        if not app or not hasattr(app, "browser") or app.browser is None:
            raise RuntimeError("Browser is not available")
        result = {"uri": uri, "path": path, "found": False}

        if uri:
            item = self._find_browser_item_by_uri(app.browser, uri)
            if item:
                result["found"] = True
                result["item"] = {
                    "name": item.name,
                    "is_folder": item.is_folder,
                    "is_device": item.is_device,
                    "is_loadable": item.is_loadable,
                    "uri": item.uri,
                }
                return result

        if path:
            return self._get_browser_items_at_path(path)

        return result

    def _search_browser(self, query, category="all"):
        """Search browser items by name."""
        app = self.application()
        if not app or not hasattr(app, "browser") or app.browser is None:
            raise RuntimeError("Browser is not available")

        categories = []
        if category == "all":
            for cat_name in ["instruments", "sounds", "drums", "audio_effects", "midi_effects"]:
                if hasattr(app.browser, cat_name):
                    categories.append(getattr(app.browser, cat_name))
        elif hasattr(app.browser, category):
            categories.append(getattr(app.browser, category))

        results = []

        def search_item(item, depth=0, max_depth=5):
            if not item:
                return
            name = item.name.lower() if hasattr(item, "name") else ""
            if query.lower() in name:
                results.append({
                    "name": item.name,
                    "is_folder": hasattr(item, "children") and bool(item.children),
                    "is_loadable": hasattr(item, "is_loadable") and item.is_loadable,
                    "uri": item.uri if hasattr(item, "uri") else None,
                })
            if hasattr(item, "children") and item.children and depth < max_depth:
                for child in item.children:
                    search_item(child, depth + 1, max_depth)

        for cat in categories:
            search_item(cat)

        return {"query": query, "results": results, "count": len(results)}

    def _load_browser_item(self, track_index, item_uri):
        """Load a browser item (instrument/effect) onto a track by its URI."""
        song = self._song
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        app = self.application()
        item = self._find_browser_item_by_uri(app.browser, item_uri)
        if not item:
            raise ValueError("Browser item with URI '{}' not found".format(item_uri))
        song.view.selected_track = track
        app.browser.load_item(item)
        return {"loaded": True, "item_name": item.name, "track_index": track_index}

    def _find_browser_item_by_uri(self, browser_or_item, uri, max_depth=8, current_depth=0):
        """Recursively find a browser item by its URI."""
        if current_depth > max_depth:
            return None
        try:
            if hasattr(browser_or_item, "uri") and browser_or_item.uri == uri:
                return browser_or_item
            if hasattr(browser_or_item, "children") and browser_or_item.children:
                for child in browser_or_item.children:
                    result = self._find_browser_item_by_uri(child, uri, max_depth, current_depth + 1)
                    if result:
                        return result
        except Exception:
            pass
        return None
