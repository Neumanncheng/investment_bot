"""Tests for scheduler module."""

import json
import tempfile
from pathlib import Path

import pytest

# We patch the global paths before importing scheduler
from unittest import mock
from src import scheduler


class TestBuildCronExpr:
    def test_basic(self):
        assert scheduler._build_cron_expr("16:30", "1-5") == "30 16 * * 1-5"

    def test_midnight(self):
        assert scheduler._build_cron_expr("00:05", "0") == "5 0 * * 0"

    def test_multi_days(self):
        assert scheduler._build_cron_expr("09:15", "1,3,5") == "15 9 * * 1,3,5"


class TestValidate:
    def test_valid(self):
        scheduler._validate({"time": "09:30", "days": "1-5", "tz": "UTC"})

    def test_invalid_time_format(self):
        with pytest.raises(ValueError):
            scheduler._validate({"time": "9:30", "days": "1-5", "tz": "UTC"})

    def test_invalid_hour(self):
        with pytest.raises(ValueError):
            scheduler._validate({"time": "25:00", "days": "1-5", "tz": "UTC"})

    def test_invalid_days(self):
        with pytest.raises(ValueError):
            scheduler._validate({"time": "09:30", "days": "abc", "tz": "UTC"})


class TestDescribe:
    def test_weekdays(self):
        assert "周一-五" in scheduler.describe({"time": "16:30", "days": "1-5", "tz": "Asia/Hong_Kong"})

    def test_single_day(self):
        assert "周三" in scheduler.describe({"time": "10:00", "days": "3", "tz": "UTC"})

    def test_multi_days(self):
        assert "周一,三,五" in scheduler.describe({"time": "14:00", "days": "1,3,5", "tz": "UTC"})
