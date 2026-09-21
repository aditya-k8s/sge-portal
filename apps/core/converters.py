"""
URL path converter for primary keys.

Primary keys are ObjectIds on MongoDB and integers on the SQL backends, so the
``<int:pk>`` converter Django ships with matches nothing once the project runs
on MongoDB: reverse() raises NoReverseMatch for every detail URL, and an
incoming ObjectId in a path 404s. This converter picks the right pattern from
the configured engine, so the URLconf stays the same on either.
"""

from django.conf import settings

OBJECT_ID = r'[0-9a-fA-F]{24}'
INTEGER = r'[0-9]+'


class PrimaryKeyConverter:
    """Matches an ObjectId on MongoDB, a positive integer on SQL backends."""

    regex = OBJECT_ID if settings.DB_ENGINE in ('mongodb', 'mongo') else INTEGER

    def to_python(self, value):
        # Left as a string. The ObjectIdAutoField and the integer field both
        # accept one in a queryset lookup, so no conversion is needed here.
        return value

    def to_url(self, value):
        return str(value)
