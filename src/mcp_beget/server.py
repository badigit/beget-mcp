import logging
import os
import sys

from .app import mcp
from .client import init_client
from .config import load_config

# Configure logging to stderr (stdout is reserved for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger(__name__)


def main() -> None:
    log.info("Starting Beget MCP server")

    try:
        config = load_config()
    except ValueError as e:
        log.error("Configuration error: %s", e)
        sys.exit(1)

    init_client(config)

    # Import tools so @mcp.tool() decorators register them
    import mcp_beget.tools  # noqa: F401

    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport in ("sse", "streamable-http"):
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8322"))

        mcp.settings.host = host
        mcp.settings.port = port
        mcp.settings.stateless_http = True

        from mcp.server.transport_security import TransportSecuritySettings

        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )

        log.info("Tools registered, starting %s server on %s:%d", transport, host, port)
        mcp.run(transport=transport)
    else:
        log.info("Tools registered, running stdio server")
        mcp.run(transport="stdio")
