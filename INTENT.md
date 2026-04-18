This tool exists to statically analyze an AI system prompt for logical contradictions, gaps, and exploitable edge cases using regex and heuristic rule extraction.
Accepts: Raw text system prompts (inline string or --file path), .txt/.md files containing system prompts, multi-rule instruction sets
Rejects: Source code files (will parse code syntax as rules and produce false findings), JSON/YAML configs (expects natural language instructions, not structured data), conversation transcripts
