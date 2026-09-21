"""
Register PyMySQL as the MySQLdb driver, if it is installed.

Django's MySQL backend imports MySQLdb; PyMySQL provides a drop-in
replacement that needs no C toolchain. The import is guarded because the
project can also run on MongoDB or SQLite, where PyMySQL is not installed at
all -- an unconditional import made the whole application fail to start.
"""

try:
    import pymysql
except ImportError:  # pragma: no cover - depends on the configured backend
    pass
else:
    pymysql.install_as_MySQLdb()
