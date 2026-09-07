# rule-audit for Codex

A Codex plugin that contributes one skill, `$rule-audit:audit`, for auditing a
named AI system-prompt file with the [`rule-audit`](https://github.com/hermes-labs-ai/rule-audit)
static analyzer — locally, offline, deterministically, and only inside a turn
you send.

```
> Audit prompts/support_agent.md with $rule-audit:audit
```

Codex runs the bundled adapter locally, shows you the command and its output in
the transcript, and summarises the findings: contradictions, priority
ambiguities, meta-paradoxes, absoluteness issues and coverage gaps.

Validated against Codex CLI **0.145.0**.

---

## Prerequisite

`rule-audit` itself, on your `PATH`:

```bash
pipx install 'rule-audit>=0.3.1'
```

It is pure standard library — no dependencies, no network calls. Alternatively
set `RULE_AUDIT_PYTHON` to a Python interpreter that has it. The plugin adds no
runtime dependency to anything, and the adapter checks the version it found and
prints it in every report.

## Install

The repository is itself a Codex plugin marketplace, so installing is two
commands:

```bash
codex plugin marketplace add hermes-labs-ai/rule-audit
codex plugin add rule-audit@rule-audit
```

**No `--ref` needed.** Measured, not inferred: `codex plugin marketplace add`
runs a plain `git clone` with no `--branch`, so it gets the remote's default
branch and then looks for `.agents/plugins/marketplace.json` at the clone root.
That file is on `main`, so the bare form above resolves the marketplace;
`--ref main` is the same thing said twice. Pass `--ref` only to install from
some other branch or a pinned commit.

To install from a local clone instead — which is also how you test a change:

```bash
codex plugin marketplace add /path/to/rule-audit
codex plugin add rule-audit@rule-audit
```

`codex plugin list` shows what a marketplace offers before you install anything.

Installing copies `integrations/codex/` to
`$CODEX_HOME/plugins/cache/rule-audit/rule-audit/<version>/` and enables the
plugin. Start a new Codex session to pick it up.

**Not published.** This plugin has not been submitted to the universal plugin
directory that ChatGPT and Codex share. The marketplace above is this
repository, which you add yourself and can remove.

## Use

Type `$` in the composer and pick `rule-audit:audit`, or type the mention
directly, and name the file in the same message:

```
> Audit prompts/support_agent.md with $rule-audit:audit
```

`/skills` opens the same picker. Either way, selecting the skill inserts the
mention into the composer — you still press Enter, so nothing runs until you
send it.

You can also just describe the task (“check my system prompt for contradictions,
it’s in prompts/support.md”) and Codex may reach for the skill on its own —
**skills are implicitly invocable by default**, and the instructions Codex
injects tell the model to use a skill when "the task clearly matches a skill's
description". That is the mechanism, not something this plugin opts into; the
description is written to make it fire on prompt-audit requests and not on
general code review. Nothing runs in the background and nothing runs until you
send a turn, but "the model never picks this up unless you name it" would be
false, so: it can, and it is meant to.

To make the skill explicit-only, add `policy: {allow_implicit_invocation: false}`
to the front matter of the installed `SKILL.md`. Do not reach for "disable the
skill instead" — a disabled skill is dropped from the mention resolver along
with the implicit catalog (`core-skills/src/injection.rs:183`,
`config_rules.rs:57-84`), so `$rule-audit:audit` would no longer resolve either.
Disabling and the `$` mention are not substitutes for one another: disabling
turns the skill off entirely, `allow_implicit_invocation: false` narrows it to
mention-only.

## What you get

A bounded, deterministic report:

- **Per-family counts**, always, so a coverage-gap-driven `HIGH` is visible as
  one rather than being mistaken for a pile of contradictions.
- **At most 5 findings per family** and **160 characters per quoted span**, with
  the true totals stated and the untruncated `rule-audit --file` command printed.
- **Files over 64 KB refused**, because rule-audit's contradiction pass is
  O(n²) in parsed rules and the library caps nothing itself.
- **A final `[rule-audit status N]` line** carrying the CLI's exit code as text.

### Reading the result honestly

Two properties of the analyzer that the skill also tells the model, because they
change what a `HIGH` label means:

- **The risk label is a density score.** It means "this many absolute rules and
  detected conflicts for a document this size". It has a floor: a file with *no
  rules at all* still scores 40/100 (`HIGH`) from the eight coverage-gap checks
  alone. A `HIGH` with zero contradictions is saying "this prompt does not
  mention several common policy domains", not "this prompt is dangerous".
- **Pairwise findings can be spurious.** Two rules are compared when they share a
  keyword cluster, so an unrelated pair that both mention e.g. "content" can be
  reported as conflicting. Check each pair before acting on it.

Measured on real files: `rule-audit`'s label is `HIGH` or `CRITICAL` for 65% of
real `AGENTS.md`/`CLAUDE.md` files and 86% of prompt files, and about 44% of
those verdicts contain no contradiction at all. That is why this ships as a
skill you invoke and read, and not as a hook that interrupts you.

### Scope

rule-audit is calibrated for **system prompts**: dense, mostly-imperative rule
sets that govern an agent's behaviour. `AGENTS.md`, `CLAUDE.md` and similar
repository guides are prose documentation; they parse into hundreds of "rules"
that share vocabulary but not subject matter, which produces large numbers of
spurious pairings. The skill audits them if you ask and then says the result is
unreliable.

## What it costs when you are not using it

Honestly: one line. An installed, enabled skill has its name, description and
path injected into the developer instructions of **every turn**, inside a budget
Codex caps at 2% of the model's context window. There is no tool schema, no MCP
server, no hook, and nothing runs — but the catalog line is not free, and this
plugin will not claim otherwise.

If you want it installed but silent, disable the skill (below); the line
disappears and the plugin stays.

## Disable

Stop the skill contributing anything, without uninstalling — add to
`$CODEX_HOME/config.toml`:

```toml
[[skills.config]]
name = "rule-audit:audit"
enabled = false
```

Or disable the whole plugin:

```toml
[plugins."rule-audit@rule-audit"]
enabled = false
```

You can also toggle skills interactively from `/skills`.

## Uninstall

```bash
codex plugin remove rule-audit@rule-audit
codex plugin marketplace remove rule-audit
```

The first deletes `$CODEX_HOME/plugins/cache/rule-audit/rule-audit/` and the
plugin's `config.toml` entry; the second removes the marketplace entry. An empty
`plugins/cache/rule-audit/` directory is left behind by the host, and nothing
else is. Neither command touches `rule-audit` itself — remove that with
`pipx uninstall rule-audit`.

The plugin writes no state of its own anywhere, and running it writes no
`__pycache__` into its install directory — the adapter is executed as a
subprocess script rather than imported, so Python caches nothing.

One caveat for the local-clone install path: `codex plugin add` copies the
source directory *verbatim*, so if your clone already contains a `__pycache__/`
under `skills/audit/scripts/` — which running this repository's test suite
creates — that directory is copied in too. It is inert, and `codex plugin
remove` deletes it with everything else. A Git-sourced install never has one,
because `__pycache__` is gitignored.

## How it is put together

```
integrations/codex/
├── .codex-plugin/plugin.json          # the manifest Codex's installer reads
└── skills/audit/
    ├── SKILL.md                       # what the model is told, and the caveats
    └── scripts/
        ├── codex_audit.py             # the host-specific wrapper
        └── audit_report.py            # the shared adapter, vendored
```

`audit_report.py` is a **byte-for-byte copy** of
`integrations/claude-code/scripts/audit_report.py`, pinned by
`tests/test_codex_plugin.py`. `codex plugin add` copies one directory out of the
repository, so this tree cannot import a shared module from a common parent —
the same packaging constraint the Gemini CLI extension and the Hermes Agent
plugin document. Detection and rendering still exist once; `codex_audit.py`
holds only what this host requires, and a test asserts it imports nothing from
`rule_audit`.

### Why the wrapper exists

In the other three integrations the command is expanded from a template. Here it
is not: a Codex skill is *text*, injected into the turn as a user-role message,
and the model writes the shell call itself. So every guarantee is made by the
wrapper process rather than by a template, which is strictly more reliable —
there is no phrasing the model could choose that removes them:

- **It always exits 0** and states the status in-band. `rule-audit` exits 2 for
  `HIGH`/`CRITICAL`, which is the common case, and Codex renders a non-zero exit
  as a failed command to both you and the model.
- **It always fences its output.** The report quotes text out of a file you have
  been told not to trust, and here that text lands in two hazardous places at
  once: the model's context, and your terminal.
- **It strips Unicode categories Cc and Cf**, not just control characters. The
  bidi overrides are Cf, and a prompt file containing U+202E can otherwise make
  a quoted rule render reversed — so the report shows the opposite of what it
  found.
- **It checks the argument count** rather than joining words, so an unquoted path
  with a space is reported back instead of silently auditing a different file.
- **It bounds the audit at 60 seconds and kills the whole process tree**, not
  just the adapter. The analyzer is a grandchild, and it is the O(n²) half —
  killing the direct child would leave the expensive work running while claiming
  it had been stopped. POSIX uses a process group, Windows uses `taskkill /T`,
  and if neither reaches the tree the message says the analyzer may still be
  running instead of claiming otherwise.

### No hook

Codex has lifecycle hooks and this plugin declares none, for the calibration
reasons above: an unsolicited interrupt firing on two of every three prompt
files — hardest on the shortest ones, since the score is inverted with length —
is not a signal. The same conclusion was reached independently for Claude Code,
Gemini CLI and Hermes Agent.

## Licence

MIT, same as the rest of the repository.
