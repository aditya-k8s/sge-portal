"""
File storage backed by MongoDB GridFS.

The application runs on hosts with no writable disk -- Vercel's filesystem is
read-only apart from /tmp, and a container's disk is wiped on every deploy --
so uploaded drawings, invoices and images cannot live on the filesystem. They
go into GridFS on the same cluster as everything else, which means no second
service to run and no separate credentials.

GridFS splits each file into chunks in ``<bucket>.chunks`` and keeps one record
per file in ``<bucket>.files``. The document's ``filename`` is the upload path
Django generated, e.g. ``project_files/2026/09/drawing.pdf``, so the name held
in a FileField column is unchanged and existing rows keep working.

Files are not reachable over HTTP by themselves; apps.core.views.serve_media
streams them out, and enforces who may read which.

Size: a free Atlas tier is 512 MB shared with the application data, so this is
comfortable for drawings and invoices but is not an object store. Moving to S3
or R2 later means changing STORAGES in config/settings.py, nothing else.
"""

import threading
from urllib.parse import quote

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

_client_lock = threading.Lock()
_client = None


def _get_bucket():
    """
    Return the GridFS bucket, opening the connection on first use.

    A module-level client, not one per Storage instance: PyMongo's client owns
    a connection pool and is thread-safe, and building one per request would
    re-do the TLS handshake and SRV lookup every time.
    """
    global _client
    import gridfs
    from pymongo import MongoClient

    if _client is None:
        with _client_lock:
            if _client is None:
                _client = MongoClient(settings.MONGODB_URI)
    database = _client[settings.MONGODB_DATABASE]
    return gridfs.GridFSBucket(database, bucket_name=settings.GRIDFS_BUCKET)


@deconstructible
class GridFSStorage(Storage):
    """Django storage over a GridFS bucket. Deconstructible, so it may be
    named in a migration without freezing a connection into it."""

    def _open(self, name, mode='rb'):
        # GridFS is immutable: a file is written once and read back. Django
        # only ever opens media for reading, so a write mode is a programming
        # error rather than something to emulate.
        if 'w' in mode or 'a' in mode:
            raise ValueError(
                f'GridFSStorage cannot open {name!r} in mode {mode!r}. '
                f'Files are written once, through save().'
            )
        bucket = _get_bucket()
        with bucket.open_download_stream_by_name(name) as stream:
            return ContentFile(stream.read(), name=name)

    def _save(self, name, content):
        bucket = _get_bucket()
        # Django has already passed the name through available_name(), so it
        # does not collide with an existing file.
        content.open()
        try:
            bucket.upload_from_stream(name, content)
        finally:
            content.close()
        return name

    def delete(self, name):
        bucket = _get_bucket()
        for record in bucket.find({'filename': name}):
            bucket.delete(record._id)

    def exists(self, name):
        bucket = _get_bucket()
        for _ in bucket.find({'filename': name}).limit(1):
            return True
        return False

    def size(self, name):
        bucket = _get_bucket()
        for record in bucket.find({'filename': name}).sort('uploadDate', -1).limit(1):
            return record.length
        return 0

    def get_created_time(self, name):
        bucket = _get_bucket()
        for record in bucket.find({'filename': name}).sort('uploadDate', -1).limit(1):
            return record.upload_date
        raise FileNotFoundError(name)

    # Django calls this for FileField.url in templates.
    def url(self, name):
        if not name:
            return ''
        return settings.MEDIA_URL + quote(name)

    def listdir(self, path):
        # Not used by the application; media is always addressed by full name.
        raise NotImplementedError('GridFSStorage does not support listdir().')
