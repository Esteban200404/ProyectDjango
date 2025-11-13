from __future__ import annotations

from typing import Literal


DATA_SOURCE_SQL: Literal['sql'] = 'sql'
DATA_SOURCE_MONGO: Literal['mongo'] = 'mongo'
DATA_SOURCE_CHOICES = {DATA_SOURCE_SQL, DATA_SOURCE_MONGO}
SESSION_KEY = 'library_data_source'


def get_active_data_source(request) -> str:
    source = request.session.get(SESSION_KEY, DATA_SOURCE_SQL)
    if source not in DATA_SOURCE_CHOICES:
        source = DATA_SOURCE_SQL
    return source


def set_active_data_source(request, source: str) -> None:
    if source not in DATA_SOURCE_CHOICES:
        source = DATA_SOURCE_SQL
    request.session[SESSION_KEY] = source


def is_mongo_source(request) -> bool:
    return get_active_data_source(request) == DATA_SOURCE_MONGO


def next_data_source(current: str) -> str:
    return DATA_SOURCE_MONGO if current == DATA_SOURCE_SQL else DATA_SOURCE_SQL
