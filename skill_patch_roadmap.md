# Visual Orchestrator - SkillPatch Roadmap

This document outlines the roadmap for developing, testing, and publishing the `visual-orchestrator` skill to [SkillPatch.dev](https://skillpatch.dev).

## Vision
To create a LatentCode skill that spins up a local drag-and-drop GUI canvas, unifying draw.io architecture diagramming and n8n workflow execution. The AI agent acts as a live compiler, translating visual blocks into code, infrastructure, or executable workflow files.

---

## 1. Skill Architecture & File Tree

The skill will be packaged as a `.tar.gz` archive for SkillPatch, containing the following structure:

```text
visual-orchestrator/
├── SKILL.md                # Core AI instructions and SkillPatch YAML frontmatter
├── package.json            # Minimal dependencies (express, cors)
├── server.js               # The local bridge API (localhost:3000)
├── public/
│   └── index.html          # The React Flow GUI canvas (via CDN)
└── parsers/
    ├── to-drawio.js        # Converter: latent-graph.json -> draw.io XML
    └── to-n8n.js           # Converter: latent-graph.json -> n8n workflow.json
```

---

## 2. Development Roadmap (Hackathon Timeline)

### Phase 1: Core Bridge (Hours 1-2)
- [ ] Scaffold the directory structure.
- [ ] Write `SKILL.md` with standard SkillPatch YAML frontmatter.
- [ ] Implement `server.js` (Express GET/POST endpoints for `/load` and `/save`).
- [ ] Implement `public/index.html` (React Flow canvas for drawing basic blocks and edges).

### Phase 2: Dual-Layer Data Model (Hours 2-4)
- [ ] Define `latent-graph.json` schema to support both visual metadata (coordinates, color) and functional metadata (endpoints, rules).
- [ ] Ensure the UI can input both types of data into a block.
- [ ] Test the two-way sync: Canvas saves to JSON -> Terminal reads JSON -> Terminal updates JSON -> Canvas reflects change.

### Phase 3: AI Rules & Parsers (Hours 4-12)
- [ ] Write `parsers/to-drawio.js` to convert `latent-graph.json` to mxGraph XML.
- [ ] Write `parsers/to-n8n.js` to convert `latent-graph.json` to n8n `workflow.json`.
- [ ] Define Graph-to-Code mapping rules in `SKILL.md` (e.g., "If edge connects 'Frontend' to 'Database', prompt to scaffold a server").

### Phase 4: Packaging & Testing (Hours 12-24)
- [ ] Execute `npm install` and test the full loop locally within a LatentCode session.
- [ ] Create the tarball: `tar -czvf visual-orchestrator.tar.gz -C visual-orchestrator .`
- [ ] Validate the tarball extraction behaves as expected.

---

## 3. SkillPatch.dev Publishing Requirements

To host on SkillPatch.dev, the `SKILL.md` must include exactly this frontmatter:

```yaml
---
name: visual-orchestrator
description: >
  Spins up a local drag-and-drop GUI canvas (localhost:3000) that unifies draw.io architecture diagramming 
  and n8n workflow execution. Translates visual blocks into latent-graph.json, draw.io XML, and n8n configurations.
languages:
  - JavaScript
  - HTML
  - Node.js
category: code-generation
license: MIT
metadata:
  author: [Your Team Name]
  version: "1.0"
---
```

## 4. End-User Installation command
Once published, users will install the skill using standard SkillPatch syntax:
```bash
mkdir -p .latentcode/plugins/skills/visual-orchestrator
curl -sSL https://skillpatch.dev/install_skill/visual-orchestrator | tar -xz -C .latentcode/plugins/skills/visual-orchestrator/
```
