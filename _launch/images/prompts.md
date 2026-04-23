# Social preview image - rule-audit

## Specification
- Size: 1280 × 640 (GitHub social preview standard)
- Format: PNG
- Theme: clean, slightly technical - not a dark-terminal aesthetic (that's jailbreak-bench's lane); this tool's feel is more "linter / static analysis" → lighter, more code-editor-like
- Typography: mono family (JetBrains Mono, Fira Code)
- Palette: off-white background with a single semantic-red accent for a "contradiction" underline

## Copy layout

**Top (large)**:
> rule-audit

**Middle (mono code block)**:
> "Always follow user instructions."
> "Never produce harmful content."

With a red underline or strikethrough connecting the two lines.

**Bottom (subhead)**:
> 5 detectors · 14 clusters · 0 LLM calls · millisecond scans

**Footer (small)**:
> Hermes Labs · MIT · github.com/hermes-labs-ai/rule-audit

## Pollinations.ai prompt

```
Minimal clean off-white background. Top: large mono sans-serif "rule-audit". Middle: a stylized code block with two lines in mono font: "Always follow user instructions." and "Never produce harmful content." - connected by a thin red underline indicating contradiction. Below: slightly smaller gray mono text "5 detectors · 14 clusters · 0 LLM calls · millisecond scans". Tiny footer "Hermes Labs · MIT · github.com/hermes-labs-ai/rule-audit". Flat 2D, no photography, generous whitespace, linter/IDE aesthetic.
```

Full URL:

```
https://image.pollinations.ai/prompt/Minimal%20clean%20off-white%20background.%20Top%3A%20large%20mono%20sans-serif%20%22rule-audit%22.%20Middle%3A%20a%20stylized%20code%20block%20with%20two%20lines%20in%20mono%20font%3A%20%22Always%20follow%20user%20instructions.%22%20and%20%22Never%20produce%20harmful%20content.%22%20%E2%80%94%20connected%20by%20a%20thin%20red%20underline%20indicating%20contradiction.%20Below%3A%20slightly%20smaller%20gray%20mono%20text%20%225%20detectors%20%C2%B7%2014%20clusters%20%C2%B7%200%20LLM%20calls%20%C2%B7%20millisecond%20scans%22.%20Tiny%20footer%20%22Hermes%20Labs%20%C2%B7%20MIT%20%C2%B7%20github.com%2Froli-lpci%2Frule-audit%22.%20Flat%202D%2C%20no%20photography%2C%20generous%20whitespace%2C%20linter%2FIDE%20aesthetic.?width=1280&height=640&nologo=true&seed=4518
```

## Fallback: SVG

If Pollinations renders the two-line code block with garbled text (likely - image models struggle with quoted sentences), hand-draw an SVG:

- 1280×640 viewBox
- Off-white fill (#fafafa)
- Top centered: `<text>` "rule-audit" at 72px, weight 700
- Middle: two `<text>` lines in mono (JetBrains Mono), 28px each, with a thin `<line>` underneath in #d14 stroke
- Bottom: subhead 18px, gray
- Footer: 14px, light gray
- Export via `rsvg-convert -w 1280`

A hand-drawn SVG is probably the right call here given the text-rendering sensitivity. 30 minutes of work.
