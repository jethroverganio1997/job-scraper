# Codex Agent Ground Rules

## Mission
Ship changes safely while keeping the knowledge base current. Every feature or fix must end with accurate code, validated behaviour when feasible, and updated documentation under `.agent/`.

## Working Sequence
1. **Read first:** Start with `.agent/README.md` to understand existing system notes, SOPs, and tasks.
2. **Plan before you code:** For feature-level work, draft a concrete plan and record the PRD/plan in `.agent/tasks/<feature>.md`. Do not implement until the plan is acknowledged.
3. **Execute carefully:** Follow the SOPs (see `.agent/sop/`) for migrations, routing, deployments, etc. Respect existing architecture and coding standards.
4. **Validate:** Run targeted tests or manual checks relevant to your change. Note any gaps in the handoff.
5. **Document:** Update the appropriate files in `.agent/system/`, `.agent/sop/`, and `.agent/tasks/` so they reflect the new reality. Always refresh the index in `.agent/README.md`.

## Documentation Structure
All project knowledge lives in `.agent/`. Keep the hierarchy intact:

```
.agent/
  README.md          # Documentation index (only file in root)
  commands/          # Instructions for maintaining docs (read before editing)
  system/            # Current architecture, schema, integrations, tech stack
  sop/               # Step-by-step operational guides
  tasks/             # Feature PRDs and implementation plans
```

- `system/` captures the state of the codebase (data model, architecture, integrations, etc.).
- `sop/` captures how we do things (migrations, routing, deployment workflows, etc.).
- `tasks/` holds per-feature context: problem statement, plan, decisions, and follow-ups.

Refer to `.agent/commands/update-doc.md` for the precise documentation workflow, naming conventions, and cross-linking expectations.

## Approval & Communication
- Seek approval before starting implementation on any new feature task.
- Surface blockers early; do not proceed until requirements are clear.
- When handing off, summarize code changes, validation performed, remaining risks, and documentation updates.

## Quality Checklist
- [ ] Implementation plan approved (when required)
- [ ] Code change reviewed against architecture standards
- [ ] Tests or manual validation executed (and documented)
- [ ] Relevant `.agent/` docs updated + index refreshed
- [ ] Next steps or open issues clearly called out

Follow these rules and future agents will always know what changed, why it changed, and how to extend the system safely.

---

# Repository Guidelines (Quick Reference)

## Docs
We keep all important docs in the `.agent` folder and update them continuously. The structure is:

```
.agent
├─ tasks/   # PRD & implementation plan for each feature
├─ system/  # Current state of the system (project structure, tech stack, integration points, database schema, core functionalities)
├─ sop/     # Best practices for executing recurring tasks (schema migration, adding a page route, etc.)
└─ README.md # Index of all documentation so everyone knows what to read
```

## Golden Rules
- Always update `.agent` docs after implementing a feature so they reflect the new state of the system.
- Before planning any implementation, read `.agent/README.md` for context.
- When assigned a feature task, create a detailed implementation plan and save it as `.agent/tasks/<name>.md`.
- Request approval on the plan before writing code.
- Use `.agent/commands/update-doc.md` to follow the official documentation workflow.
