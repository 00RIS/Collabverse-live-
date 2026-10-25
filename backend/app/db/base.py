"""
app/db/base.py

WHAT THIS FILE IS:
Defines `Base`, the declarative base class every SQLAlchemy model
inherits from.

WHY IT EXISTS:
SQLAlchemy needs one shared "registry" class so it knows about every
table you define as a Python class. When Alembic (our migration tool)
looks for "what tables should exist", it inspects everything that
inherits from this same `Base`. If two files each created their own
Base, Alembic would only see half your models — so there must be
exactly one Base for the whole project, imported everywhere.
"""

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
