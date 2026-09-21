"""On-demand control: text command -> intent -> appliance action."""

from .intent import Intent, IntentType
from .command_parser import CommandParser, ParseError

__all__ = ["CommandParser", "Intent", "IntentType", "ParseError"]
