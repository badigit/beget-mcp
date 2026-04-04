"""Import all tool modules so their @mcp.tool() decorators fire."""

import json


def _json(data: dict) -> str:
    """Serialize API response for MCP output."""
    return json.dumps(data, ensure_ascii=False, indent=2)


from . import account, backup, cron, dns, domains, ftp, mail, mysql, sites  # noqa: F401, E402
