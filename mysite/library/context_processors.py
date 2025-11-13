from .data_sources import (
    DATA_SOURCE_MONGO,
    DATA_SOURCE_SQL,
    get_active_data_source,
    next_data_source,
)


def data_source_meta(request):
    current = get_active_data_source(request)
    alternate = next_data_source(current)
    return {
        'current_data_source': current,
        'alternate_data_source': alternate,
        'DATA_SOURCE_SQL': DATA_SOURCE_SQL,
        'DATA_SOURCE_MONGO': DATA_SOURCE_MONGO,
    }
