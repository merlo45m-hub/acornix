"""Atomic file writes for app generation/editing.

Failure recovery primitive. Writing a generated app straight over a working
one means a crash, a battery death, or a full /storage mid-write leaves the
user with a truncated index.html and no way back. Every path that overwrites
an existing app file goes through here instead.
"""

import os


def atomic_write_text(file_path, text, encoding="utf-8"):
    """Write ``text`` to ``file_path`` atomically.

    Builds the new content in ``<file_path>.tmp`` beside the target, then swaps
    it in with ``os.replace``, which is atomic on the same filesystem. On
    failure the temp file is cleaned up and the original file is left exactly
    as it was.

    Returns True on success, False on OSError (message printed for the CLI).
    """
    tmp_path = file_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
        return True
    except OSError as e:
        print(f"❌ Could not save {file_path}: {e}")
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return False
