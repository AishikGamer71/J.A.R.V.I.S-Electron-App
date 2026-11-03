# Skill Authoring Guide: agentskills.io Manifest Format

## 1. Skill Manifest (`skill.json` / `manifest.yaml`)
Skills in J.A.R.V.I.S conform to the `agentskills.io` specification.

```yaml
name: github-operations
version: 1.0.0
description: "Perform GitHub repository, pull request, and issue management using official gh CLI"
author: jarvis-ecosystem
license: MIT

permissions:
  required:
    - shell:gh
    - network:api.github.com
  risk_level: HIGH

tools:
  - name: gh_create_issue
    description: "Create a new issue on the specified repository"
    input_schema:
      type: object
      properties:
        repo:
          type: string
          description: "Repository in owner/name format"
        title:
          type: string
        body:
          type: string
      required: [repo, title]

dependencies:
  system:
    - gh
  python: []
```

## 2. Runtime Loading

J.A.R.V.I.S loads skills from `~/.jarvis/skills/` when the core service starts.
The canonical format is a `SKILL.md` file with YAML front matter followed by the
instruction body. The legacy `manifest.yaml`, `manifest.yml`, and `skill.json`
formats are also accepted for compatibility.

```markdown
---
name: github-operations
description: Safely manage GitHub work through the approved JARVIS tools.
version: 1.0.0
author: jarvis-ecosystem
license: MIT
allowed_tools: [web_search]
agents: [research_agent, chat_agent]
tags: [github, repository]
---

Use `web_search` to find current public repository information. Ask for approval
before any action that needs a higher-risk tool.
```

The core API exposes `GET /v1/skills`, `GET /v1/skills/{name}`, and
`POST /v1/skills/reload`. Skills are instructions, not executable plugins: they
cannot bypass the tool registry, risk classifier, permission store, sandbox, or
confirmation UI.
