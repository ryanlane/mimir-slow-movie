# Slow Movie Player — Mimir Source Plugin

A Very Slow Movie Player source plugin for the [Mimir](https://github.com/ryanlane/mimir) platform. Plays video files one frame at a time at configurable ultra-slow speeds — from seconds per frame to hours per frame — inspired by the [Very Slow Movie Player](https://medium.com/s/story/very-slow-movie-player-499f76c48b62) concept.

**Plugin ID:** `com.mimir.slowmovie`
**Version:** 1.0.0
**Author:** Ryan Lane

---

## Features

- Plays any video file frame-by-frame at user-defined speeds (seconds, minutes, or hours per frame)
- Configurable frame skip — advance multiple source frames per display update to speed up slow videos
- Per-movie timing overrides independent of global defaults
- Random mode — picks a random frame from across the video instead of advancing linearly
- Quiet hours — pause frame advancement during specified hours without interrupting the display
- Movie library — manage multiple videos, activate one at a time
- Video upload directly through the management UI
- Directory scan to add existing videos by filesystem path
- Seek to any frame number; manually advance on demand
- Management Web Component with live "Now Playing" status and progress bar

---

## Installation

### Via Mimir Plugin Store (recommended)

Open the Mimir UI, go to **Sources**, click **Browse Store**, and search for "Slow Movie Player". Click **Install**.

### Via git URL

In **Sources → Install Source**, paste:

```
https://github.com/ryanlane/mimir-slow-movie.git
```

### Manual

```bash
git clone https://github.com/ryanlane/mimir-slow-movie.git
cp -r mimir-slow-movie/channels/slow_movie /path/to/mimir-api/channels/
pip install -r channels/slow_movie/requirements.txt
```

Restart (or hot-reload) the Mimir API — the channel is auto-discovered.

---

## Requirements

- Mimir Platform v2.1.0+
- Python 3.8+
- `fastapi`, `pillow`, `opencv-python-headless`

OpenCV is used for frame extraction. The headless build avoids GUI dependencies and is safe for server environments.

---

## Configuration

Global settings apply to all movies unless a movie has a per-movie override. Configure through the management interface or at `/api/channels/com.mimir.slowmovie/settings`.

| Setting | Type | Default | Description |
|---|---|---|---|
| `time_per_frame` | integer | `30` | How long each frame is displayed before advancing |
| `time_per_frame_unit` | string | `"minutes"` | Unit for frame duration: `seconds`, `minutes`, `hours` |
| `skip_frames` | integer | `1` | Source video frames to advance per display update |
| `use_quiet_hours` | boolean | `false` | Pause frame advancement during quiet hours |
| `quiet_start` | integer | `22` | Hour to begin quiet period (0–23, 24-hour clock) |
| `quiet_end` | integer | `7` | Hour to end quiet period (0–23, 24-hour clock) |
| `video_root_path` | string | `""` | Optional directory to scan for video files |

### Per-movie overrides

Individual movies can override `time_per_frame`, `time_per_frame_unit`, and `skip_frames`. Set `is_random` on a movie to use random frame selection instead of sequential playback.

### Supported video formats

`mp4`, `avi`, `mov`, `mkv`, `webm`

Maximum upload size: 10 GB.

---

## API Endpoints

All endpoints are prefixed with `/api/channels/com.mimir.slowmovie`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/manifest` | Channel capabilities and schema |
| `POST` | `/request_image` | Get the current frame (advances playback) |
| `GET` | `/status` | Current playback status, active movie, frame progress |
| `GET` | `/settings` | Get global settings |
| `PUT` | `/settings` | Update global settings |
| `GET` | `/movies` | List all movies in the library |
| `POST` | `/movies` | Add a movie by filesystem path |
| `GET` | `/movies/{id}` | Get a specific movie's details |
| `PUT` | `/movies/{id}` | Update a movie's settings or metadata |
| `DELETE` | `/movies/{id}` | Remove a movie from the library |
| `POST` | `/movies/{id}/activate` | Set a movie as the active (now playing) movie |
| `POST` | `/movies/{id}/advance` | Manually advance to the next frame |
| `POST` | `/movies/{id}/seek` | Seek to a specific frame number |
| `POST` | `/upload` | Upload a video file |
| `GET` | `/frame/current` | Return the current frame as an image file |
| `POST` | `/scan` | Scan `video_root_path` and add discovered videos |

---

## Management Interface

The plugin registers a management page in the Mimir UI accessible by clicking the source in **Sources**. From the management interface you can:

- See the active movie with frame progress and estimated completion
- Add movies by local path or upload a video file
- Activate any movie from the library
- Adjust per-movie timing and random mode
- Seek to any frame or manually advance
- Edit global settings

---

## File Structure

```
channels/slow_movie/
├── plugin.json          # Channel manifest (id, schema, UI registration)
├── channel.py           # SlowMovieChannel implementation
├── models.py            # Movie and GlobalSettings dataclasses + MovieDatabase
├── video_service.py     # OpenCV frame extraction and video metadata
├── requirements.txt     # Python dependencies
├── ui/
│   └── manage.esm.js   # Management page Web Component (Shadow DOM)
└── data/
    ├── movies.json      # Movie library (persisted)
    └── settings.json    # Global settings (persisted)
```

---

## Troubleshooting

**No active movie / blank display:** Add a video to the library and activate it through the management interface.

**Frame not advancing:** Check quiet hours settings. If quiet hours are active, the current frame is served without advancing. Verify the system clock is correct.

**OpenCV not available:** Ensure `opencv-python-headless` is installed in the same Python environment as the Mimir API. The channel logs a warning at startup if OpenCV is missing and falls back to a placeholder.

**Large video files:** Frame extraction on very large files can be slow on first access. Subsequent frame requests are faster once OpenCV has indexed the file.

**Health check:**
```bash
curl http://localhost:5000/api/channels/com.mimir.slowmovie/status
```

---

## License

Same terms as the Mimir platform.
