# rule-audit for Hermes Agent

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin that adds one
in-session slash command:

```
/rule-audit                       # audits your own SOUL.md
/rule-audit prompts/support.md    # audits any prompt file
```

It reports contradictions, priority ambiguities, meta-paradoxes, absoluteness
challenges and coverage gaps in a system prompt — locally, offline, in
milliseconds, with no model call and no network.

`SOUL.md` is the default target because it *is* a system prompt: Hermes puts it
first in the assembled prompt and it replaces the default agent identity. That
is the input rule-audit is calibrated for.

Validated against **Hermes Agent 0.21.0**.

## Install

Requires `rule-audit` 0.3.1 or newer on the machine. It is pure stdlib — no
dependencies, no network:

```bash
pipx install 'rule-audit>=0.3.1'
```

If the `rule-audit` on your `PATH` is older than 0.3.1, point the plugin at an
interpreter that has a new enough one instead of upgrading globally:

```bash
export RULE_AUDIT_PYTHON=/path/to/venv/bin/python
```

The plugin says which of these two it is when it cannot find a usable runtime.

Then install and enable the plugin:

```bash
hermes plugins install hermes-labs-ai/rule-audit/integrations/hermes-agent
hermes plugins enable rule-audit
```

Hermes clones the repository and copies only that subdirectory into
`~/.hermes/plugins/rule-audit/`. Plugins are opt-in, so the `enable` step is
required — a fresh install is inert until you run it. For a reproducible
install, pin a full 40-character commit with `--ref`.

To install from a local clone instead, copy `integrations/hermes-agent/` to
`~/.hermes/plugins/rule-audit/` and run the `enable` command.

The plugin declares **no capabilities**, so `hermes plugins enable` has nothing
to ask you to consent to. It cannot override built-in tools, cannot touch your
LLM provider or credentials, and cannot act on connected chat platforms.

## Use

Type `/rule-audit` in any Hermes session. It appears in `/help`, in
autocomplete, and in the Telegram bot's command menu.

- `/rule-audit` — audits the `SOUL.md` of the active profile, resolved through
  Hermes' own `get_hermes_home()`, so a non-default profile audits *its* SOUL.md.
  The report names the file it chose.
- `/rule-audit <path>` — audits that file. The path is taken as typed: spaces
  need no escaping, `~` is expanded, and surrounding quotes are stripped if you
  add them out of habit.

The report always ends with a status line:

| Line | Meaning |
|---|---|
| `[rule-audit status 0]` | risk LOW or MEDIUM |
| `[rule-audit status 2]` | risk HIGH or CRITICAL — a finding, not a failure |
| `[rule-audit status 1]` | the audit could not run; the message above says why |

These are the `rule-audit` CLI's own exit codes. A slash command returns a
string rather than an exit code, so the status is carried in the text. **If
there is no status line, the audit did not run.**

## How to read the result

Two things to know, or you will misread a `HIGH`.

**1. `HIGH` is common, and the label is lexical.** Measured across 235 real
`CLAUDE.md`/`AGENTS.md` files, 65% score HIGH or CRITICAL; across a wider corpus
of prompt files, 86%. About 44% of those verdicts contain **no contradiction at
all**. rule-audit parses with sentence splitting and modal-verb regexes, so it
both misses rules that need semantic reading and pairs unrelated rules that
share a keyword. rule-audit's own README says a `CRITICAL` label does not prove
a prompt is exploitable. Read the findings, not the label.

**2. There is a coverage-gap floor at 40/100.** The risk score adds 5 points per
uncovered domain out of eight hard-coded domains, and `HIGH` starts at 40. An
**empty file scores HIGH at 40/100**. The score is therefore inverted with
length — a short prompt covers fewer domains and scores worse. The per-family
counts are always printed so you can see when a `HIGH` is made entirely of gaps,
and a file with no parseable rules is reported as *unchecked* rather than clean
or risky.

## Why a command and not a hook

Hermes offers `on_session_start` and `post_tool_call`, and this plugin
deliberately registers neither.

The numbers above are why. A hook that fires on every session start would fire
on roughly two of every three real prompt files, ~44% of the time with no
contradiction behind it, and would fire hardest on the *shortest* files because
of the coverage-gap floor. Those numbers are fine for an audit you asked for and
are reading. They are not a basis for interrupting a session unbidden. This
would also spend the audit on every session rather than when it is useful.

The measurements are host-independent — they are a property of rule-audit's
scoring, not of Hermes — and the same conclusion is recorded in this repository's
Claude Code and Gemini CLI integrations.

## What it costs you

- **No tool-schema cost.** The plugin registers no model tool, so the tool
  schema sent on every API call is byte-for-byte unchanged.
- **No prompt-cache cost.** It adds nothing to the system prompt and mutates no
  prompt state, so per-conversation prompt caching is untouched.
- **Nothing runs unless you ask.** No hooks, no background scanning, no
  scheduled work.

## Scope and limits

- **Bounded input.** Files over 64 KB are refused with a pointer to the CLI.
  rule-audit's contradiction pass is O(n²) in parsed rules and the library caps
  nothing itself.
- **Bounded output.** 5 findings per family and 160 characters per quoted span.
  True totals are always printed, along with the command for the full report.
- **Bounded time.** The audit is stopped at 60 seconds so your session stays
  responsive. Hermes dispatches slash commands synchronously, so a long audit
  blocks the prompt.
- **Deterministic.** Two runs over an unchanged file produce identical text; the
  report's timestamp field is never read.
- **This is not a linter for repository guides.** Pointed at an `AGENTS.md` or a
  `README.md` it will produce findings, and per the measurements above most will
  not hold. It is calibrated for system prompts — `SOUL.md` is one.

## Where the output goes

To you — never to the model. Hermes dispatches a plugin slash command before any
API call and shows you the returned string directly: printed to the terminal in
the CLI, returned over JSON-RPC in the TUI, sent as the reply message on
Telegram, Discord and Slack. Nothing the report contains can instruct your agent,
even when the audited file is hostile.

The report is Markdown, which renders on the chat platforms and appears as plain
text in a terminal. The handler cannot tell which surface will display its
return value — it receives only the argument string — so it emits one rendering
that is safe on the strictest one. That is why text quoted from the audited file
stays escaped even in a terminal, where the escaping is visible as backslashes:
on Telegram and Discord that escaping is what stops a hostile prompt file from
restyling the message.

Control characters are stripped from everything returned, because the CLI
renders it through prompt_toolkit's ANSI parser and an escape sequence in an
audited file would otherwise drive your terminal.

## Disable and uninstall

```bash
hermes plugins disable rule-audit    # keep it installed, stop loading it
hermes plugins remove rule-audit     # delete it
```

Disabling takes effect on the next session. Removing deletes the whole
directory.

The plugin writes no state of its own — no cache, no logs, no config. Python's
importer does write `__pycache__/` inside the install directory when Hermes
loads the plugin; a plugin cannot prevent that without setting
`sys.dont_write_bytecode` process-wide, which is not a plugin's decision to make
for its host. `hermes plugins remove` deletes it along with everything else.

Uninstalling the plugin does not touch `rule-audit` itself. Remove that with
`pipx uninstall rule-audit`.

## How it fits together

| File | Role |
|---|---|
| `plugin.yaml` | Manifest. Name, version, no capabilities, no tools, no hooks. |
| `__init__.py` | `register(ctx)` — registers the one slash command. |
| `hermes_audit.py` | The only host-specific logic: SOUL.md resolution, argument handling, the status line, terminal containment, the timeout. |
| `audit_report.py` | The shared adapter over the `rule-audit` CLI. Byte-identical to the Claude Code plugin's copy, pinned by test. |

`audit_report.py` shells out to `rule-audit --file PATH --format json` and
renders what comes back. It adds nothing to detection and decides nothing about
severity. `hermes plugins install` copies a single directory out of the
repository, so this tree cannot import a shared module from a common parent — a
vendored copy with an equality test is the only reuse the packaging permits, and
detection and rendering still exist exactly once.

## Links

- rule-audit: <https://github.com/hermes-labs-ai/rule-audit>
- Hermes Agent plugins: <https://hermes-agent.nousresearch.com/docs/developer-guide/plugins>
