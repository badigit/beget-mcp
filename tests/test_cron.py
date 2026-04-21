"""Tests for cron tools: external param naming is consistent (task_id)."""

from mcp_beget.tools import cron


def test_cron_toggle_uses_task_id_externally(fake_client):
    fake_client.set_response("cron", "changeHiddenState", {"status": "success", "result": True})
    cron.cron_toggle(task_id=42, is_hidden=1)
    _, _, params = fake_client.calls[-1]
    # Externally task_id, internally API field row_number — must be mapped.
    assert params == {"row_number": 42, "is_hidden": 1}


def test_cron_delete_accepts_task_id(fake_client):
    fake_client.set_response("cron", "delete", {"status": "success", "result": True})
    cron.cron_delete(task_id=7)
    _, _, params = fake_client.calls[-1]
    assert params == {"row_number": 7}


def test_cron_edit_sends_only_modified_fields(fake_client):
    fake_client.set_response("cron", "edit", {"status": "success", "result": True})
    cron.cron_edit(task_id=5, command="/new/command")
    _, _, params = fake_client.calls[-1]
    assert params == {"id": 5, "command": "/new/command"}
