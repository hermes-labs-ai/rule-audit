"""rule-audit as a Hermes Agent plugin: the `/rule-audit` slash command.

Registers one in-session command and nothing else — no model tool, so the tool
schema sent on every API call is unchanged, and no lifecycle hook, so nothing
runs unless the user asks for it. Both are deliberate; see `hermes_audit.py`.

Hermes imports a directory plugin as `hermes_plugins.<slug>` with the plugin
directory on its `__path__`, so the relative import below is how a sibling
module is reached.
"""

from __future__ import annotations

from . import hermes_audit

#: Shown in `/help`, in autocomplete, and in the Telegram bot's command menu.
DESCRIPTION = "Audit a system prompt for contradictions and gaps (bare: your SOUL.md)"


def register(ctx) -> None:
    """Hermes plugin entry point."""
    ctx.register_command(
        "rule-audit",
        handler=hermes_audit.audit,
        description=DESCRIPTION,
        # Optional, in the host's own `[name]` convention: bare `/rule-audit`
        # audits SOUL.md. Supplying a hint also sets `argument_mode="text"`,
        # which is what makes Discord surface a free-text argument field
        # instead of registering the command as parameterless.
        args_hint="[path]",
    )
