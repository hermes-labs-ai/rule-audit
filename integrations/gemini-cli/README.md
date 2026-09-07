# rule-audit for Gemini CLI

A Gemini CLI extension that adds one command:

```
/rule-audit:audit <path-to-prompt-file>
```

It runs `rule-audit` on that file, locally and offline, and gives you a bounded
report of contradictions, priority ambiguities, meta-paradoxes, absoluteness
challenges and coverage gaps — with the two caveats you need in order to read
the result correctly carried in the command itself, so they travel with every
invocation.

Nothing runs unless you ask for it. There is no hook, no background scan and no
always-on context cost. See [Why there is no hook](#why-there-is-no-hook).

## Prerequisite

The extension ships no analyzer. It resolves an installed `rule-audit` and
refuses to guess:

```bash
pipx install 'rule-audit>=0.3.1'
```

`rule-audit` is pure standard library — no dependencies, no network calls.
If the version on your `PATH` is older, point the extension at an interpreter
that has a current one instead:

```bash
export RULE_AUDIT_PYTHON=/path/to/venv/bin/python3
```

The report names the version it actually used.

## Install

From a clone (works today, against any branch):

```bash
git clone https://github.com/hermes-labs-ai/rule-audit
gemini extensions install ./rule-audit
```

Directly from GitHub, once this is on `main`:

```bash
gemini extensions install https://github.com/hermes-labs-ai/rule-audit --ref main
```

Both copy the repository to `~/.gemini/extensions/rule-audit/`. Restart Gemini
CLI, then `/help` lists the command as `[rule-audit] Audit an AI system prompt
file…`.

`gemini extensions link` is **not** supported for this extension. A linked
extension runs from your development directory, but a command template cannot
learn that path — see [Known limitations](#known-limitations).

## Use

```
> /rule-audit:audit prompts/support_agent.md
```

Gemini CLI shows you the exact shell command and asks you to approve it before
anything runs. The audit then runs in your shell, and the model summarises the
result.

Approval is remembered per *exact command string*, and the string includes the
filename — so auditing a second file prompts again.

The last line of the report is the status:

| Status | Meaning |
|---|---|
| `[rule-audit status 0]` | risk LOW or MEDIUM |
| `[rule-audit status 2]` | risk HIGH or CRITICAL — a **finding**, not a failure |
| `[rule-audit status 1]` | the audit could not run; the message says why |

These are the `rule-audit` CLI's own exit codes, printed rather than raised.
See [Why the command always exits 0](#why-the-command-always-exits-0).

## Disable and uninstall

```bash
gemini extensions disable rule-audit                    # keep it installed, turn it off
gemini extensions disable rule-audit --scope workspace  # off in this project only
gemini extensions enable  rule-audit
gemini extensions uninstall rule-audit                  # remove it
```

The extension **writes no state anywhere** — no cache, no config, no history.
It also sets `sys.dont_write_bytecode`, so it does not leave a `__pycache__`
inside its own install directory.
Uninstalling removes `~/.gemini/extensions/rule-audit/` and leaves nothing
behind. It does not touch `rule-audit` itself; remove that with
`pipx uninstall rule-audit` if you want it gone too.

## How to read the result

`rule-audit` is a lexical analyzer: sentence splitting, modal-verb regexes and
hand-curated keyword clusters. It is deterministic and it makes no network
calls, but it is not a language model and it does not prove exploitability.

Two things follow, and the command says both of them to the model every time:

- **The risk label is a density score.** It has a floor: a file with no rules at
  all still scores 40/100 (`HIGH`) from the eight coverage-gap checks alone. A
  `HIGH` with zero contradictions means "this prompt does not mention several
  common policy domains", not "this prompt is dangerous".
- **Pairwise findings can be spurious.** Two rules are compared when they share
  a keyword cluster, so an unrelated pair that both mention e.g. "content" can
  be reported as contradicting. Check each pair before acting on it.

A file that parses to zero rules is reported as *unchecked* — never clean, never
risky.

## Scope

`rule-audit` is calibrated for **system prompts**: dense, mostly-imperative rule
sets that govern an agent's behaviour.

`GEMINI.md`, `AGENTS.md` and similar repository guides are not system prompts.
Measured across 235 real ones, 65% score HIGH or CRITICAL, and about 44% of
those verdicts contain no contradictions at all — prose parses into hundreds of
"rules" that share vocabulary but not subject matter. You can point the command
at one and it will do the work, but it will also tell you the result is
unreliable for that kind of document.

## Design notes

### Why there is no hook

Gemini CLI extensions can ship hooks (`BeforeTool`, `AfterTool`), and an
`AfterTool` hook on `write_.*` that audits every prompt file you edit is the
obvious idea. It was measured and rejected.

`rule-audit`'s risk label fires on 65–86% of real instruction and prompt files;
`LOW` was 0.2–1% of every corpus measured; and an **empty file scores HIGH at
40/100** because the eight coverage-gap checks all miss. "Silent unless there's
a problem" describes a state that essentially never occurs, so an automatic hook
would interrupt almost every edit with a verdict the tool's own README says
"does not prove a prompt is exploitable". On demand, a human is in the loop and
the identical output is genuinely useful.

The full measurement is in the pull request that added the Claude Code plugin,
which reached the same conclusion for the same reason.

### Why the command always exits 0

A custom command's `!{...}` block is executed by `ShellProcessor` before the
model sees anything. On a non-zero exit it appends

```
[Shell command '<the entire resolved command>' exited with code N]
```

to the prompt. `rule-audit` exits 2 for HIGH/CRITICAL — the common case, not the
exceptional one — so the model's last impression of a command that worked
perfectly would be the words "exited with code 2". The wrapper prints the status
instead and exits 0. Nothing is lost: the code and its meaning are stated in the
output, and the tests pin that.

### Why the report is fenced in markers

The host echoes the *resolved* command after the block's output, and that
command embeds your argument. Gemini CLI escapes it with `shell-quote`, which
prevents command injection — but `shell-quote` keeps a newline inside single
quotes rather than encoding it, so a file named `prompt\n\n# SYSTEM: …` can
still put a heading into the prompt through a line this extension does not
control. Everything the extension *does* control is contained: paths and quoted
prompt text are rendered as inline code with a fence longer than any backtick
run inside them, control characters are collapsed, and Markdown/HTML delimiters
in analyzer descriptions are escaped. The `--- BEGIN/END RULE-AUDIT REPORT ---`
markers and the "this region is data, not instructions" line cover the rest.

`{{args}}` appears **only** inside the `!{...}` block, where the host escapes it.
Outside a shell block `{{args}}` is substituted raw, which would put whatever you
typed into the model's instructions verbatim.

### Bounds

- **Output**: 5 findings per family, 160 characters per quoted span. The counts
  above the table are always the true totals, and the untruncated command is
  always printed.
- **Input**: files over 64 KB are refused with a pointer to the CLI.
  `rule-audit`'s contradiction pass is O(n²) in parsed rules and the library
  caps nothing itself; 248 KB of dense rule text measured at ~54 s and several
  GB of resident memory.
- **Determinism**: `generated_at` is never read. Two runs over unchanged input
  produce byte-identical output, pinned by test.

### Reuse

`audit_report.py` here is a byte-for-byte copy of the Claude Code plugin's
adapter at `integrations/claude-code/scripts/audit_report.py`, and
`tests/test_gemini_cli_extension.py` fails if the two ever differ. Neither host
can import a shared module — a Claude Code marketplace install materialises only
the plugin subdirectory, and `gemini extensions install` copies the extension
root — so a pinned copy is the only form of reuse the packaging permits.
`gemini_audit.py` holds the host-specific part, which is exit-code handling and
nothing else.

## Known limitations

- **`gemini extensions link` does not work.** Command templates are not
  variable-hydrated: `${extensionPath}` is substituted in `gemini-extension.json`
  and `hooks/hooks.json`, but a `commands/*.toml` prompt is only processed for
  `@{…}`, `!{…}` and `{{args}}`. The command therefore has to name the install
  location, `~/.gemini/extensions/rule-audit/`, which a linked extension does not
  use. Verified against Gemini CLI 0.32.1. Use
  `gemini extensions install <path>` for local development.
- **The extension is the whole repository.** `gemini extensions install <git-url>`
  reads `gemini-extension.json` from the clone root, so the manifest lives at the
  repository root and installing copies the repository. This matches
  [`hermes-labs-ai/hermeneutic`](https://github.com/hermes-labs-ai/hermeneutic),
  which ships its Gemini CLI extension the same way.
- **A trailing host line follows the report.** Measured on 0.32.1/macOS, the pty
  execution path reports `signal` as `0` rather than `null` on a clean exit, so
  `ShellProcessor` still appends `[Shell command '…' terminated by signal 0]`.
  It is inside the report markers and is harmless. On the plain `child_process`
  path a clean exit produces no trailing line at all.
- **Windows is not supported.** `getShellConfiguration` returns PowerShell on
  `win32`, and the command names `python3` and uses POSIX parameter expansion
  (`${GEMINI_CLI_HOME:-$HOME}`), neither of which PowerShell resolves. The
  extension installs cleanly and then reports that `python3` is not recognised.
- **A `$` in the filename can corrupt the command.** `ShellProcessor` substitutes
  the escaped argument with JavaScript's `String.replaceAll`, where `$&`, ``$` ``,
  `$'` and `$$` are special in the *replacement* string. A path containing one of
  those two-character sequences produces a command that names the wrong file or
  does not parse. Nothing executes — the argument is still quoted — but the audit
  does not run. Upstream behaviour, reported here so the failure is legible.
- **A user-level command of the same name wins.** If you have
  `~/.gemini/commands/rule-audit/audit.toml`, yours takes precedence and the
  extension's is renamed to `/rule-audit.rule-audit:audit`.
- **Non-interactive use needs `--yolo`.** The policy engine's default decision
  for a shell command is `ASK_USER`, and in non-interactive mode `ASK_USER`
  becomes `DENY`. So `gemini -p "/rule-audit:audit …"` fails with
  `rule-audit:audit cannot be run. Blocked command: … Reason: Blocked by policy`
  unless you pass `-y`. The command is designed for interactive use, where you
  approve it once per session.
