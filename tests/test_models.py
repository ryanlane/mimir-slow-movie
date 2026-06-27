"""Tests for slow_movie channel models — verifies mimir_utils migration."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from channels.slow_movie.models import GlobalSettings, Movie, MovieDatabase


class TestGlobalSettings:
    def test_defaults(self):
        s = GlobalSettings()
        assert s.skip_frames == 1
        assert s.video_root_path == ""

    def test_to_dict(self):
        s = GlobalSettings(skip_frames=5, video_root_path="/videos")
        d = s.to_dict()
        assert d["skip_frames"] == 5
        assert d["video_root_path"] == "/videos"

    def test_from_dict_ignores_unknown(self):
        s = GlobalSettings.from_dict({"skip_frames": 3, "bogus": True})
        assert s.skip_frames == 3

    def test_from_dict_partial(self):
        s = GlobalSettings.from_dict({"video_root_path": "/media"})
        assert s.skip_frames == 1

    def test_no_secret_fields(self):
        s = GlobalSettings(skip_frames=2, video_root_path="/movies")
        assert s.to_public_dict() == s.to_dict()

    def test_round_trip(self):
        s = GlobalSettings(skip_frames=10, video_root_path="/home/pi/movies")
        s2 = GlobalSettings.from_dict(s.to_dict())
        assert s2.skip_frames == 10
        assert s2.video_root_path == "/home/pi/movies"


class TestMovie:
    def _make_movie(self, **kwargs):
        defaults = {
            "id": "abc-123",
            "title": "2001: A Space Odyssey",
            "video_path": "/videos/2001.mp4",
            "total_frames": 10000,
            "current_frame": 500,
        }
        return Movie(**{**defaults, **kwargs})

    def test_to_dict_includes_progress_pct(self):
        m = self._make_movie(total_frames=1000, current_frame=100)
        d = m.to_dict()
        assert "progress_pct" in d
        assert 0 <= d["progress_pct"] <= 100

    def test_progress_pct_at_start(self):
        m = self._make_movie(total_frames=1000, current_frame=0)
        assert m.to_dict()["progress_pct"] == 0.0

    def test_from_dict_ignores_progress_pct(self):
        m = self._make_movie()
        d = m.to_dict()
        d["progress_pct"] = 999
        m2 = Movie.from_dict(d)
        assert not hasattr(m2, "progress_pct") or m2.__dataclass_fields__.get("progress_pct") is None

    def test_from_dict_ignores_unknown(self):
        m = self._make_movie()
        d = {**m.to_dict(), "unknown_field": "ignored"}
        m2 = Movie.from_dict(d)
        assert m2.title == m.title


class TestMovieDatabase:
    @pytest.fixture
    def db(self, tmp_path):
        return MovieDatabase(tmp_path / "data")

    def _movie_data(self, **kwargs):
        return {
            "id": "test-id-1",
            "title": "Solaris",
            "video_path": "/videos/solaris.mp4",
            **kwargs,
        }

    def test_empty_on_new_db(self, db):
        assert db.list_movies() == []

    def test_add_and_get_movie(self, db):
        m = Movie(**self._movie_data())
        db.add_movie(m)
        assert db.get_movie("test-id-1").title == "Solaris"

    def test_list_movies(self, db):
        db.add_movie(Movie(**self._movie_data(id="m1", title="Film A")))
        db.add_movie(Movie(**self._movie_data(id="m2", title="Film B")))
        assert len(db.list_movies()) == 2

    def test_update_movie(self, db):
        db.add_movie(Movie(**self._movie_data()))
        updated = db.update_movie("test-id-1", {"current_frame": 999})
        assert updated.current_frame == 999

    def test_update_nonexistent_returns_none(self, db):
        assert db.update_movie("no-such-id", {"title": "X"}) is None

    def test_delete_movie(self, db):
        db.add_movie(Movie(**self._movie_data()))
        assert db.delete_movie("test-id-1") is True
        assert db.get_movie("test-id-1") is None

    def test_delete_nonexistent(self, db):
        assert db.delete_movie("nope") is False

    def test_settings_defaults(self, db):
        s = db.get_settings()
        assert s.skip_frames == 1

    def test_update_settings(self, db):
        db.update_settings({"skip_frames": 5, "video_root_path": "/media"})
        assert db.get_settings().skip_frames == 5

    def test_persists_movies_to_disk(self, tmp_path):
        db1 = MovieDatabase(tmp_path / "data")
        db1.add_movie(Movie(**self._movie_data()))
        db2 = MovieDatabase(tmp_path / "data")
        assert db2.get_movie("test-id-1").title == "Solaris"

    def test_persists_settings_to_disk(self, tmp_path):
        db1 = MovieDatabase(tmp_path / "data")
        db1.update_settings({"skip_frames": 7})
        db2 = MovieDatabase(tmp_path / "data")
        assert db2.get_settings().skip_frames == 7
