"""Identity of a data file, for a Streamlit cache key.

``@st.cache_data`` hashes the function source and its arguments. It does not
notice when a file that function reads is replaced on disk. Pass the tuple
from ``file_signature`` as an argument so a new history.csv, map, or CPUC
file is a cache miss.

The tuple includes mtime and size, and a content hash so a rewrite that
keeps the old mtime still misses.
"""
import hashlib
from pathlib import Path


def file_signature(path) -> tuple:
    path = Path(path)
    if not path.is_file():
        return (str(path), 0, 0, "")
    data = path.read_bytes()
    stat = path.stat()
    digest = hashlib.sha256(data).hexdigest()
    return (str(path.resolve()), stat.st_mtime_ns, stat.st_size, digest)
