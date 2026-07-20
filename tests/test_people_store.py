"""Tests for durable people/token storage."""

from __future__ import annotations

import pytest

import oura_fun.people_store as ps


@pytest.fixture(autouse=True)
def tmp_people_db(tmp_path, monkeypatch):
    """Redirect the people store to a temp DB for each test."""
    db_file = tmp_path / "people.duckdb"
    monkeypatch.setenv("OURA_PEOPLE_DB_PATH", str(db_file))
    yield db_file


def test_add_and_get_tokens():
    ps.add_person("alice", "tok_alice")
    ps.add_person("Bob", "tok_bob")  # should be lowercased

    tokens = ps.get_tokens()
    assert tokens["alice"] == "tok_alice"
    assert tokens["bob"] == "tok_bob"


def test_add_person_upsert():
    ps.add_person("alice", "old_token")
    ps.add_person("alice", "new_token")

    tokens = ps.get_tokens()
    assert tokens["alice"] == "new_token"
    assert len(tokens) == 1


def test_remove_person():
    ps.add_person("alice", "tok_alice")
    ps.add_person("bob", "tok_bob")
    ps.remove_person("alice")

    tokens = ps.get_tokens()
    assert "alice" not in tokens
    assert tokens["bob"] == "tok_bob"


def test_get_tokens_empty_db():
    assert ps.get_tokens() == {}


def test_list_people_store():
    ps.add_person("alice", "tok_alice")
    ps.add_person("bob", "tok_bob")

    rows = ps.list_people_store()
    assert len(rows) == 2
    ids = {r["person_id"] for r in rows}
    assert ids == {"alice", "bob"}
    for row in rows:
        assert "added_at" in row
        assert "token" in row


def test_list_people_store_empty():
    assert ps.list_people_store() == []
