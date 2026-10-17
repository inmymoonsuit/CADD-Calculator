# Developer documentation

| Document | Purpose | Update it when… |
|---|---|---|
| [architecture.md](architecture.md) | How the pieces fit | the structure changes |
| [decisions/](decisions/README.md) | ADRs: why we chose what we chose | you make a hard-to-reverse choice |
| [known-issues.md](known-issues.md) | Limitations and formula doubts (`KI-NNN`) | you find or fix one |
| [engineering-log.md](engineering-log.md) | Attempts that failed or were reverted | something didn't work, even if never committed |
| [roadmap.md](roadmap.md) | Scope, milestones, open decisions | priorities change |
| [packaging.md](packaging.md) | Building the app, the two editions, branding packs | the build or the pack format changes |
| [design/palette.md](design/palette.md) | UI colors, their roles, and contrast rules | the palette or the themes change |
| [design/icons.md](design/icons.md) | Vendored Tabler icons: pinning, adding, recoloring | you add or update an icon |
| [legacy-workbooks.md](legacy-workbooks.md) | Transcription of the original Excel tools | never, except corrections. It is a historical record. |

Day-to-day work items live in GitHub Issues, which link back to `KI-` and `ADR-` IDs.

## Documentation rules

1. Docs change in the **same pull request** as the behavior they describe.
2. Every formula has a source: a cited reference, or "legacy course spreadsheet". Cite
   edition, section, and page. Never copy copyrighted text or tables (ADR-0008).
3. Record decisions in ADRs and dead ends in the engineering log, even small ones.
4. Use the project's terms: *bend angle* (from flat), *outside setback*, *K-factor*, and so on.
   See the [glossary](../user/glossary.md).
