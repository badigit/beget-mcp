from mcp.types import ToolAnnotations


READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
)

MUTATING = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    openWorldHint=False,
)

DESTRUCTIVE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    openWorldHint=False,
)
