"""
Migrations for Django's own apps, regenerated for MongoDB.

The migrations shipped inside django.contrib create AutoField primary keys,
which the MongoDB backend cannot apply. MIGRATION_MODULES in config/settings.py
redirects those three apps here, where the same tables are described with
ObjectId primary keys instead. Nothing in this package is used on the SQL
backends.
"""
