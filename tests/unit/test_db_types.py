from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.dialects import sqlite

from evidenceforge.db.types import UTCDateTime


def test_utc_datetime_rejects_naive_values() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        UTCDateTime().process_bind_param(datetime(2026, 7, 24, 12), sqlite.dialect())


def test_utc_datetime_normalizes_offset_and_restores_awareness() -> None:
    database_type = UTCDateTime()
    source = datetime(2026, 7, 24, 12, tzinfo=timezone(timedelta(hours=-5)))

    bound = database_type.process_bind_param(source, sqlite.dialect())
    restored = database_type.process_result_value(bound, sqlite.dialect())

    assert bound == datetime(2026, 7, 24, 17)
    assert restored == datetime(2026, 7, 24, 17, tzinfo=UTC)
