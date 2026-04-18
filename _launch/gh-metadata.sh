#!/usr/bin/env bash
# Set rule-audit GitHub repo metadata. Run ONCE after the repo is public.

gh repo edit roli-lpci/rule-audit \
  --description "Static linter for LLM system prompts: contradictions, gaps, priority ambiguities. No LLM calls. 174 tests. Hermes Labs." \
  --homepage "https://hermes-labs.ai" \
  --add-topic llm \
  --add-topic static-analysis \
  --add-topic linter \
  --add-topic ai-audit \
  --add-topic system-prompt \
  --add-topic prompt-engineering \
  --add-topic hermes-labs \
  --add-topic python-cli \
  --add-topic eu-ai-act \
  --add-topic ci-gate
