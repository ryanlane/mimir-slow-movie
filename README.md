# Slow Movie Player — Mimir Source Plugin

A Very Slow Movie Player source plugin for the [Mimir](https://github.com/ryanlane/mimir) platform. Plays video files one frame at a time at configurable ultra-slow speeds — from seconds per frame to hours per frame — inspired by the [Very Slow Movie Player](https://medium.com/s/story/very-slow-movie-player-499f76c48b62) concept.

**Plugin ID:** `com.mimir.slowmovie`
**Version:** 1.0.0
**Author:** Ryan Lane

---

## Features

- Plays any video file frame-by-frame at user-defined speeds (seconds, minutes, or hours per frame)
- Configurable frame skip — advance multiple source frames per display update to speed up slow videos
- Per-movie settings — clip range, fit mode, loop, and frame skip independent of global defaults
- Random mode — picks a random frame from across the video instead of advancing linearly
- Movie library — manage multiple videos, each independently accessible as a sub-channel
- Video upload directly through the management UI
- Browse the server's filesystem to add existing videos without uploading
- Directory scan to add all videos in a folder at once
- Seek to any frame number; manually advance on demand
- Frame preview when setting start/end points for a clip
- Management Web Component with live status and per-movie progress bars

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
- `fastapi`, `pillow`
- `ffmpeg` and `ffprobe` system packages (installed via apt in the Mimir Docker image)

`ffmpeg` handles all frame extraction and video introspection. It is bundled in the standard Mimir Docker image — no separate installation is needed when running under Docker.

---

## Configuration

Global settings apply to all movies unless a movie has a per-movie override. Configure through the management interface or at `/api/channels/com.mimir.slowmovie/settings`.

| Setting | Type | Default | Description |
|---|---|---|---|
| `skip_frames` | integer | `1` | Source video frames to advance per display update |
| `video_root_path` | string | `""` | Optional directory to scan for video files |

### Per-movie settings

Each movie in the library can be configured independently:

| Field | Description |
|---|---|
| `title` | Display name |
| `start_frame` / `end_frame` | Clip the movie to a frame range |
| `skip_frames` | Per-movie override for the global skip setting |
| `fit_mode` | How the frame fills the display: `letterbox`, `crop`, or `stretch` |
| `loop` | Whether to restart from `start_frame` after reaching `end_frame` |
| `is_random` | Pick a random frame instead of advancing sequentially |

### Supported video formats

`mp4`, `avi`, `mov`, `mkv`, `webm`

Maximum upload size: 10 GB.

---

## API Endpoints

All endpoints are prefixed with `/api/channels/com.mimir.slowmovie`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/manifest` | Channel capabilities and schema |
| `POST` | `/request-image` | Get the current frame as image bytes (used by the platform) |
| `GET` | `/status` | Current playback status and per-movie progress |
| `GET` | `/settings` | Get global settings |
| `PUT` | `/settings` | Update global settings |
| `GET` | `/movies` | List all movies in the library |
| `POST` | `/movies` | Add a movie by filesystem path |
| `GET` | `/movies/{id}` | Get a specific movie's details |
| `PUT` | `/movies/{id}` | Update a movie's settings or metadata |
| `DELETE` | `/movies/{id}` | Remove a movie from the library |
| `POST` | `/movies/{id}/advance` | Manually advance to the next frame |
| `POST` | `/movies/{id}/seek` | Seek to a specific frame number |
| `GET` | `/movies/{id}/frame/{n}` | Return frame `n` as a JPEG (used by the UI preview) |
| `GET` | `/subchannels` | List movies as sub-channels (used by the program builder) |
| `POST` | `/upload` | Upload a video file |
| `GET` | `/browse?path=…` | List supported video files in a server directory |
| `POST` | `/scan` | Scan `video_root_path` and add all discovered videos |
| `GET` | `/frame/current` | Return the current frame as an image file |

---

## Management Interface

The plugin registers a management page in the Mimir UI accessible by clicking the source in **Sources**. From the management interface you can:

- Upload a video file directly from your browser
- Browse the server's filesystem to add videos already on the host (see [Using an existing media library](#using-an-existing-media-library))
- Add a movie by entering its full server path
- View each movie's frame progress and playback position
- Adjust per-movie settings (clip range, fit mode, loop, random)
- Preview any frame when setting start/end points
- Seek to any frame or manually advance
- Edit global defaults

---

## Using an existing media library

The **Browse Server** tab in the management UI lets you navigate directories on the host machine and add videos without uploading them. This is the recommended workflow when your videos are already on the same server running Mimir (e.g. a Plex or Jellyfin library).

Because Mimir runs inside Docker, the host path must be mounted into the API container. The cleanest way to do this — without modifying Mimir's shipped `docker-compose.yml` — is a **`docker-compose.override.yml`** file. Docker Compose automatically merges this file with the base compose on every `up`, so it survives updates.

### Setup

1. In the same directory as Mimir's `docker-compose.yml`, create `docker-compose.override.yml`:

```yaml
services:
  api:
    volumes:
      - /your/media/path:/your/media/path:ro
```

Replace `/your/media/path` with the actual path on the host. Using the same path inside the container keeps things simple — the path you type in the browser matches the path on disk.

**Example — Plex library:**
```yaml
services:
  api:
    volumes:
      - /new-pool/PlexMedia:/new-pool/PlexMedia:ro
```

**Example — multiple libraries:**
```yaml
services:
  api:
    volumes:
      - /mnt/media/movies:/mnt/media/movies:ro
      - /mnt/media/series:/mnt/media/series:ro
```

2. Apply the change:

```bash
docker compose up -d
```

3. Open the Slow Movie Player management page, click **Browse Server**, and enter the path (e.g. `/new-pool/PlexMedia/Movies`). Supported video files appear in a list — click **Add** next to any file to add it to the library.

> The `:ro` flag mounts the path read-only. Mimir never writes to your media directories.

---

## File Structure

```
channels/slow_movie/
├── plugin.json          # Channel manifest (id, schema, UI registration)
├── channel.py           # SlowMovieChannel implementation
├── models.py            # Movie and GlobalSettings dataclasses + MovieDatabase
├── video_service.py     # ffmpeg/ffprobe frame extraction and video metadata
├── requirements.txt     # Python dependencies
├── ui/
│   └── manage.esm.js   # Management page Web Component (Shadow DOM)
└── data/
    ├── movies.json      # Movie library (persisted)
    └── settings.json    # Global settings (persisted)
```

---

## Troubleshooting

**No image delivered to a screen:** Confirm the movie's video file is still accessible at the path stored in the library. If you moved or renamed the file, delete the movie entry and re-add it.

**Browse Server shows no files:** The directory must be mounted into the API container (see [Using an existing media library](#using-an-existing-media-library)). If the path exists on the host but not in the container, the API returns a "Path not found" error.

**Frame extraction fails / upload rejected:** `ffmpeg` and `ffprobe` must be available inside the container. Both are installed in the standard Mimir Docker image. Check with:
```bash
docker exec mimir-api ffmpeg -version
```

**Large video files are slow on first frame:** `ffmpeg` must decode from the nearest keyframe to the target frame. Files with infrequent keyframes (common in MKV re-encodes) can take several seconds for seeks deep into the file. Subsequent requests to nearby frames are faster.

**Health check:**
```bash
curl http://localhost:5000/api/channels/com.mimir.slowmovie/status
```

---

## License

Same terms as the Mimir platform.
