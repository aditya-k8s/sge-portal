"""
App configurations for Django's own apps when running on MongoDB.

django.contrib.admin, auth and contenttypes each pin
``default_auto_field`` to AutoField. MongoDB has no integer autoincrement --
``_id`` is an ObjectId -- so the backend rejects those models with
``mongodb.E001`` and no migration can be applied. An AppConfig's choice cannot
be overridden from settings, only by subclassing it, which is what these are
for. ``config/settings.py`` swaps them into INSTALLED_APPS when DB_ENGINE is
mongodb, and leaves the stock configs in place on the SQL backends.
"""

from django.contrib.admin.apps import AdminConfig
from django.contrib.auth.apps import AuthConfig
from django.contrib.contenttypes.apps import ContentTypesConfig

OBJECT_ID_AUTO_FIELD = 'django_mongodb_backend.fields.ObjectIdAutoField'


class MongoAdminConfig(AdminConfig):
    default_auto_field = OBJECT_ID_AUTO_FIELD


class MongoAuthConfig(AuthConfig):
    default_auto_field = OBJECT_ID_AUTO_FIELD


class MongoContentTypesConfig(ContentTypesConfig):
    default_auto_field = OBJECT_ID_AUTO_FIELD
