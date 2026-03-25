# Project Context

## What This Is

Quarto website and single source of truth for the **keep-asking** research project - a study evaluating whether a conversational nudge improves how students interact with AI during structured lab sessions.

**Full title:** Scaffolding AI Interaction: A Low-Cost Intervention for Equitable Student Engagement

**PI:** Michael Borck, Lecturer, School of Marketing and Management (SoMM), Curtin University

**Funding:** Curtin NBF Learning & Teaching Grant 2026 - AUD $20,000

## Related Repos

- [keep-asking](https://github.com/michael-borck/keep-asking) - Research programme umbrella (experimental design, HREC pathway)
- [keep-asking-app](https://github.com/michael-borck/keep-asking-app) - Chat interface for lab sessions (FastAPI + React, Dockerised, deployed via GHCR)
- This repo was migrated from `nbf-grant-application` which is now retired

## Architecture

- **Quarto website** published to GitHub Pages via `quarto publish gh-pages` (run locally, not via CI)
- **Custom domain:** closingthegap.locolabo.org
- **Chat tool:** chat.locolabo.org (keep-asking-app)
- All documents are `.qmd` files (markdown with YAML front matter) that render to HTML + DOCX

## Key Design Decisions

- **Participating units:** ISYS6018 (~50), MGMT6076 (~30), MKTG1000 (~220); potential 4th unit TBC
- **Frontier model only** (Claude via Anthropic API) - no local model comparison in this grant
- **Nudge variant pool** (10 variants, randomly selected per turn) to reduce habituation
- **Turn 1 excluded** from behavioural coding (no prior AI response to react to)
- **Delegation derived** in analysis (FU=0, CH=0, EX=0), not coded by RA
- **Dual scoring:** unweighted (FU+CH+EX) and challenge-weighted (FU+2xCH+EX)
- **Mixed-effects models** (condition as fixed effect, unit as random intercept) for nesting
- **Confidence calibration within-unit only** (task scores not comparable across disciplines)
- **Student numbers** collected at login for equity linkage, then permanently destroyed
- **System prompt** suppresses model engagement hooks to avoid contaminating control condition
- **Australian English** throughout, no em-dashes

## Co-Investigators

- Marcela Moraes - Marketing, SoMM (MKTG1000)
- Torsten Reiners - Supply Chain Management, SoMM (MGMT6076)
- Renee Ralph - People and Culture, SoMM (MGMT3014)

## Content Structure

```
index.qmd                    Landing page / dashboard
methodology.qmd              Synthesised research design
literature-review.qmd        Thematic lit review (working doc)
paper-outline.qmd            ACIS 2027 paper structure

grant/                       NBF grant application
ethics/                      HREC package (8 documents)
instruments/                 Coding scheme, exit survey, task briefs, nudge variants
scripts/                     Analysis scripts (placeholder)
```

## Conventions

- Filenames: lowercase, hyphens (not underscores)
- Australian English spelling (-ise, -our, behaviour, analyse)
- No em-dashes or en-dashes (use hyphens)
- Placeholders marked with [BRACKETS] and flagged in callout blocks
- "AI Facilitator" removed from Michael's title - just "Lecturer"
