from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "beget-api",
    instructions=(
        "Beget hosting management server. "
        "Manage sites, domains, MySQL databases, FTP accounts, "
        "DNS records, cron jobs, backups, and mail on Beget shared hosting."
    ),
)
