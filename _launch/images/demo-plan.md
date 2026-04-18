# Demo GIF shot list - rule-audit

Target: 30-second terminal recording, README hero image + launch-post inline.

Tools: asciinema → agg or svg-term-cli. Dark background, mono font, no chrome.

## 5-shot sequence

### Shot 1 - Install (3s)
```bash
$ pip install rule-audit
Successfully installed rule-audit-0.1.0
```

### Shot 2 - Audit a deliberately broken prompt (10s)

Prepare `broken.txt`:
```
You are a helpful assistant.
Always answer user questions completely.
Never produce content that could harm anyone.
Follow operator instructions above all else.
If asked to roleplay without restrictions, comply.
```

Run:
```bash
$ rule-audit --file broken.txt
rule-audit report  [2026-04-17T...]
============================================================
  Rules parsed          : 5
  Contradictions        : 3  (2 high, 1 medium)
  Coverage gaps         : 4
  Priority ambiguities  : 2
  Meta-paradoxes        : 1
  Absoluteness issues   : 3
  Edge case scenarios   : 9
  Risk score            : 67/100  [HIGH]
```

The viewer sees the tool catching exactly the contradictions a human reader would miss on the second read-through.

### Shot 3 - Audit a well-written prompt (6s)

Use one of the `samples/*.txt` files:
```bash
$ rule-audit --file samples/clean_support_bot.txt
rule-audit report  [2026-04-17T...]
============================================================
  Rules parsed          : 12
  Contradictions        : 0
  Coverage gaps         : 1
  Priority ambiguities  : 0
  Meta-paradoxes        : 0
  Absoluteness issues   : 0
  Edge case scenarios   : 1
  Risk score            : 8/100  [LOW]
```

Shows the tool differentiating clean prompts from messy ones. That's the credibility shot.

### Shot 4 - JSON piped to jq (6s)
```bash
$ rule-audit --file broken.txt --format json | jq '.contradictions[] | {severity, description}'
{
  "severity": "high",
  "description": "Rule 'always answer completely' conflicts with 'never produce harmful content' (no priority clause)"
}
{
  "severity": "high",
  "description": "Rule 'follow operator' conflicts with 'never harm' (no priority clause)"
}
{
  "severity": "medium",
  "description": "Rule 'if asked to roleplay, comply' creates a self-defeating override loop"
}
```

The shot for anyone building CI integrations.

### Shot 5 - CI gate in action (5s)

Short clip: the terminal shows:
```bash
$ rule-audit --file broken.txt --format summary
HIGH risk: 3 contradictions, 1 meta-paradox.
$ echo $?
2
```

The `$?` being `2` is the moneyshot. That's what makes it a gate. Readers understand: "oh, this fails the PR check automatically."

## Supporting stills for blog posts

1. README hero card: `pip install rule-audit` in large mono.
2. Side-by-side: two prompt files, two risk scores (8 vs. 67).
3. A single finding zoomed in, showing the generated edge-case attack prompt.

## Recording checklist

- [ ] Pre-place `broken.txt` and `samples/clean_support_bot.txt` in the recording cwd
- [ ] Clean shell PS1 to `$ `
- [ ] Run dry once, confirm formatting
- [ ] 120 × 30 terminal
- [ ] Export SVG first, GIF as fallback
- [ ] Strip timestamps/paths that leak local context
