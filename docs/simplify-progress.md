# Simplification progress

Local branch `chore/simplify`. The `pre-simplify` tag points to `a0eff26`, the verifier repair on top of `b91b309`. The application source at those revisions is identical.

## Verification precondition and repair

The first full run exited 1 at Gate B. Importing `app.main` opened the account's `%APPDATA%/JARVIS/state.db`. A guarded import stopped at `SessionDB._get_connection` before opening that file. Isolating the Windows profile and JARVIS data directory for the backend gates put state, memory, telemetry and trace databases in `.data/verify`. The guarded import then printed `IMPORTS_SUCCESSFUL` and exited 0.

`powershell -ExecutionPolicy Bypass -File scripts/verify.ps1` exited 0. Typecheck and build passed, backend imports passed, `/health` returned healthy, Electron reached the scripted SIGINT, and packaging config passed. A separate listener check found ports 8765 and 8779 free after shutdown. The smoke check used the project's isolated Electron userData and Hermes home overrides. This was a config check for packaging. A packaged executable was not exercised.

**PRE-EXISTING test failures.** Running Gate B with just the test environment set, before exercising the changed verifier, produced 612 passed and 26 failed. The first full run with the repair produced 613 passed and 25 failed. The existing gate accepts at least 605 passes and ignores the pytest exit status. It cannot certify a green pytest suite. Keep failures visible through the audit.

## Step 0 · Codex readiness

- Loaded the supplied root `AGENTS.md` and read both repo rule files. Added their core guidance to the root instructions and kept both originals. Root instruction size is 4,263 bytes.
- Inspected upstream installation instructions, compact rules, four Markdown skills and the MIT license at revision `96608e078b2d5ea607c5c3b8b5a54d1c1fba6846`. Installed only those skills and their shared license into this checkout. [Upstream source](https://github.com/DietrichGebert/ponytail/tree/96608e078b2d5ea607c5c3b8b5a54d1c1fba6846)
- Repo-local skills use the Codex `$skill-name` form. In this already-open chat the four added skills are read directly from disk. The initial host catalog contained 32 entries. CodeRabbit was unavailable. Use `git diff` self-review. The host lists modern-web-guidance. Renderer implementation requires the user's GO and relevant current official documentation.
- All 12 ECC skills already had names and descriptions. The four Ponytail entries have both fields. The verifier diff was reviewed with the Ponytail checklist, including environment restoration, data consumers and the standalone gate selectors.
- **Next.** Audit renderer and Electron, sidecar and personas, and build/config in parallel. Measure size, source, dependencies and cold start, then stop for GO.
- **Open decisions.** Retain documented unwired capabilities pending owner review. No simplification has been approved.

## Visible skill inventory

Paths beginning with `.agents/` are relative to this checkout. The last four rows are repo-local additions after session initialization.

| Skill name | SKILL.md path |
|---|---|
| `imagegen` | `C:/Users/utpal/.codex/skills/.system/imagegen/SKILL.md` |
| `openai-docs` | `C:/Users/utpal/.codex/skills/.system/openai-docs/SKILL.md` |
| `skill-creator` | `C:/Users/utpal/.codex/skills/.system/skill-creator/SKILL.md` |
| `skill-installer` | `C:/Users/utpal/.codex/skills/.system/skill-installer/SKILL.md` |
| `coding-standards` | `.agents/skills/ecc-coding-standards/SKILL.md` |
| `e2e-testing` | `.agents/skills/ecc-e2e-testing/SKILL.md` |
| `fastapi-patterns` | `.agents/skills/ecc-fastapi-patterns/SKILL.md` |
| `python-patterns` | `.agents/skills/ecc-python-patterns/SKILL.md` |
| `react-patterns` | `.agents/skills/ecc-react-patterns/SKILL.md` |
| `search-first` | `.agents/skills/ecc-search-first/SKILL.md` |
| `security-review` | `.agents/skills/ecc-security-review/SKILL.md` |
| `tdd-workflow` | `.agents/skills/ecc-tdd-workflow/SKILL.md` |
| `typescript-patterns` | `.agents/skills/ecc-typescript-patterns/SKILL.md` |
| `verification-loop` | `.agents/skills/ecc-verification-loop/SKILL.md` |
| `vite-patterns` | `.agents/skills/ecc-vite-patterns/SKILL.md` |
| `windows-desktop-e2e` | `.agents/skills/ecc-windows-desktop-e2e/SKILL.md` |
| `find-skills` | `C:/Users/utpal/.agents/skills/find-skills/SKILL.md` |
| `modern-web-guidance` | `C:/Users/utpal/.agents/skills/modern-web-guidance/SKILL.md` |
| `computer-use:computer-use` | `C:/Users/utpal/.codex/plugins/cache/openai-bundled/computer-use/26.1111.21308/skills/computer-use/SKILL.md` |
| `documents:documents` | `C:/Users/utpal/.codex/plugins/cache/openai-primary-runtime/documents/26.1112.11217/skills/documents/SKILL.md` |
| `pdf:pdf` | `C:/Users/utpal/.codex/plugins/cache/openai-primary-runtime/pdf/26.1112.11217/skills/pdf/SKILL.md` |
| `plugin-management:plugin-management` | `C:/Users/utpal/.codex/plugins/cache/openai-curated-remote/plugin-management/0.1.0/skills/plugin-management/SKILL.md` |
| `presentations:Presentations` | `C:/Users/utpal/.codex/plugins/cache/openai-primary-runtime/presentations/26.1112.11217/skills/presentations/SKILL.md` |
| `sites:sites` | `C:/Users/utpal/.codex/plugins/cache/openai-curated-remote/sites/1.1.6/skills/sites/SKILL.md` |
| `sites:sites-remix` | `C:/Users/utpal/.codex/plugins/cache/openai-curated-remote/sites/1.1.6/skills/sites-remix/SKILL.md` |
| `spreadsheets:Spreadsheets` | `C:/Users/utpal/.codex/plugins/cache/openai-primary-runtime/spreadsheets/26.1112.11217/skills/spreadsheets/SKILL.md` |
| `spreadsheets:excel-live-control` | `C:/Users/utpal/.codex/plugins/cache/openai-primary-runtime/spreadsheets/26.1112.11217/skills/excel-live-control/SKILL.md` |
| `template-creator:template-creator` | `C:/Users/utpal/.codex/plugins/cache/openai-primary-runtime/template-creator/26.1112.11217/skills/template-creator/SKILL.md` |
| `visualize:visualize` | `C:/Users/utpal/.codex/plugins/cache/openai-curated-remote/visualize/1.0.103/skills/visualize/SKILL.md` |
| `work-pets:create-pet` | `C:/Users/utpal/.codex/plugins/cache/openai-curated-remote/work-pets/0.1.6/skills/create-pet/SKILL.md` |
| `work-pets:pets` | `C:/Users/utpal/.codex/plugins/cache/openai-curated-remote/work-pets/0.1.6/skills/pets/SKILL.md` |
| `work-pets:update-pet` | `C:/Users/utpal/.codex/plugins/cache/openai-curated-remote/work-pets/0.1.6/skills/update-pet/SKILL.md` |
| `ponytail` | `.agents/skills/ponytail/SKILL.md` |
| `ponytail-audit` | `.agents/skills/ponytail-audit/SKILL.md` |
| `ponytail-debt` | `.agents/skills/ponytail-debt/SKILL.md` |
| `ponytail-review` | `.agents/skills/ponytail-review/SKILL.md` |
