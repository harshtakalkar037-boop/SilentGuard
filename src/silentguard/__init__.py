"""SilentGuard — AI-powered autonomous safety and control system.

Pipeline: PERCEIVE -> UNDERSTAND -> DECIDE -> ACT
"""

import logging

# Library code should not emit records unless the application configures
# logging. Demos print their own output; this keeps stderr clean.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__version__ = "0.1.0"
__all__ = ["__version__"]
