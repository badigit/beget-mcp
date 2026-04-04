import logging
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

    log.info("Tools registered, running server")
    mcp.run()
