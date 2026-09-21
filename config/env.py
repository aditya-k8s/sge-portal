"""
Minimal environment-variable helpers with .env file support.

Deliberately dependency-free: the project should not need django-environ or
python-dotenv just to read a handful of settings. Real environment variables
always win over values in the .env file, so container/systemd/CI configuration
overrides the local developer file without special-casing.
"""

from pathlib import Path


class ImproperlyConfigured(Exception):
    """Raised when a required setting is missing or unusable."""


_TRUTHY = {'1', 'true', 'yes', 'on'}
_FALSY = {'0', 'false', 'no', 'off', ''}


def read_dotenv(path, environ):
    """
    Load ``KEY=VALUE`` pairs from ``path`` into ``environ`` without overriding
    keys that are already set. Unparseable lines are skipped rather than
    raising, so a stray note in the file cannot stop the application booting.
    """
    path = Path(path)
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[len('export '):].lstrip()
        key, sep, value = line.partition('=')
        if not sep:
            continue
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        # Strip one matching pair of surrounding quotes.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        environ.setdefault(key, value)


class Env:
    """Typed reader over a mapping (normally ``os.environ``)."""

    def __init__(self, environ):
        self._environ = environ

    def str(self, key, default=None, required=False):
        value = self._environ.get(key)
        if value is None or value == '':
            if required:
                raise ImproperlyConfigured(
                    f'Required environment variable {key} is not set. '
                    f'Copy .env.example to .env and fill it in.'
                )
            return default
        return value

    def bool(self, key, default=False):
        value = self._environ.get(key)
        if value is None:
            return default
        normalised = value.strip().lower()
        if normalised in _TRUTHY:
            return True
        if normalised in _FALSY:
            return False
        raise ImproperlyConfigured(
            f'Environment variable {key}={value!r} is not a valid boolean. '
            f'Use one of: true, false, 1, 0, yes, no, on, off.'
        )

    def int(self, key, default=None, required=False):
        value = self.str(key, default=None, required=required)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError as exc:
            raise ImproperlyConfigured(
                f'Environment variable {key}={value!r} is not a valid integer.'
            ) from exc

    def list(self, key, default=None, separator=','):
        value = self.str(key)
        if value is None:
            return list(default or [])
        return [item.strip() for item in value.split(separator) if item.strip()]
