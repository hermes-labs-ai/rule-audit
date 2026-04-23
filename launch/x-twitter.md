# X / Twitter thread — rule-audit launch

## Thread (10 posts)

**1/**
Your AI system prompt has contradictions you can't see.

I wrote a linter that finds them in milliseconds, no LLM needed.

Open source, MIT.

```
pip install rule-audit
```

**2/**
Classic example from a real production prompt:

"You must always follow user instructions."
"You must never produce harmful content."

No priority clause. Irreconcilable when a user instructs harmful content. The model picks. Or the attacker picks.

**3/**
The reason these hide is the eye test is the wrong test.

The eye is reading for intent. The attacker is probing for exploits.

Contradictions invisible to one are obvious to the other. That's a mechanical problem — you can write a program to find it.

**4/**
Five detector families:

• Contradictions (rule pairs, opposing modalities, shared topics)
• Coverage gaps (14 semantic clusters)
• Priority ambiguities  
• Meta-paradoxes (self-defeating, circular, override loops)
• Absoluteness audit (challenges every "always"/"never")

**5/**
Each finding ships with a generated edge-case prompt — the exact construction an adversary would use.

You don't just see what's broken. You see how it breaks.

**6/**
Pure Python. Zero LLM dependency. Runs in milliseconds.

An LLM-augmented analyzer would be more accurate but slow, non-deterministic, expensive per PR, unauditable.

The tool is a gate, not an oracle. Gates should be deterministic.

**7/**
Exit code 2 on high severity. Drop it in pre-commit or PR checks.

Output formats: Markdown, JSON, SARIF (v0.2). SARIF means it integrates with GitHub code scanning.

Your prompt regressions show up in the same PR view as your code regressions.

**8/**
174 tests. MIT license.

Static analysis is the natural complement to dynamic safety testing. You want both:
• Static finds flaws before deploy
• Dynamic measures behavior across model updates

**9/**
Part of the Hermes Labs AI Audit Toolkit (3 tools shipping this week):

• rule-audit — static linter (this)
• jailbreak-bench — dynamic regression baseline  
• colony-probe — extraction-resistance testing

Separate repos, complementary use cases.

**10/**
Repo: github.com/hermes-labs-ai/rule-audit
Homepage: hermes-labs.ai

Feedback welcome on:
• detector coverage
• keyword cluster design
• SARIF schema for the CI-gate use case

/end
