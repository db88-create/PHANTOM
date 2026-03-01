from datetime import datetime
from pathlib import Path


def _get_lock_fn():
    """Return platform-appropriate file locking function."""
    try:
        import msvcrt

        def _lock(f):
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)

        def _unlock(f):
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

        return _lock, _unlock
    except ImportError:
        import fcntl

        def _lock(f):
            fcntl.flock(f, fcntl.LOCK_EX)

        def _unlock(f):
            fcntl.flock(f, fcntl.LOCK_UN)

        return _lock, _unlock


_lock_file, _unlock_file = _get_lock_fn()


def append_note(text: str, notes_path: Path | None = None):
    if notes_path is None:
        notes_path = Path.home() / "phantom" / "notes.md"

    notes_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"## {timestamp}\n{text}\n\n"

    with open(notes_path, "a", encoding="utf-8") as f:
        _lock_file(f)
        try:
            f.write(entry)
        finally:
            _unlock_file(f)
