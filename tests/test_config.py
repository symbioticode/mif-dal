"""Tests for dal/core/config.py — DALConfig per spec §7."""

from __future__ import annotations

import dataclasses

import pytest

from dal.core.config import DALConfig


class TestDefaults:
    def test_defaults(self) -> None:
        config = DALConfig()
        assert config.cache_dir is None
        assert config.request_timeout == 30


class TestCustomValues:
    def test_explicit_values(self) -> None:
        config = DALConfig(cache_dir=".dal_cache", request_timeout=60)
        assert config.cache_dir == ".dal_cache"
        assert config.request_timeout == 60


class TestValidation:
    def test_zero_timeout_raises(self) -> None:
        with pytest.raises(ValueError, match="request_timeout"):
            DALConfig(request_timeout=0)

    def test_negative_timeout_raises(self) -> None:
        with pytest.raises(ValueError, match="request_timeout"):
            DALConfig(request_timeout=-1)

    def test_empty_cache_dir_raises(self) -> None:
        with pytest.raises(ValueError, match="cache_dir"):
            DALConfig(cache_dir="")

    def test_none_cache_dir_disables_cache(self) -> None:
        config = DALConfig(cache_dir=None)
        assert config.cache_dir is None


class TestFrozen:
    def test_setattr_raises(self) -> None:
        config = DALConfig()
        with pytest.raises(dataclasses.FrozenInstanceError):
            config.request_timeout = 60  # type: ignore[misc]
