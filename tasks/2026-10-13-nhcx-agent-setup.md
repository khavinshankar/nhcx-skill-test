# NHCX agent setup

Date: 2026-10-13 (Asia/Kolkata)
Session: not recorded

## Request

Follow https://docs.abdm.gov.in/agent-setup/nhcx.md to set up the AI dev environment for NHCX integration.

## Decisions and rationale

- Scope: user chose `nhcx-full` (whole integration, both sides).
- GitHub Copilot has no NHCX marketplace plugin, so the skill was installed via the documented git sparse-checkout fallback into `.github/skills/nhcx-full` (311 files) at the workspace root, so it applies across all child repos.
- Docs MCP server `nhcx-docs` (https://docs.abdm.gov.in/mcp) was already registered in the VS Code user `mcp.json`; no change made.

## Repository changes

| Repository | Final commit | Changes |
| --- | --- | --- |
| . (parent) | this commit | Added `.github/skills/nhcx-full` and this record |

## Validation

- Skill folder present with `SKILL.md`, `references/`, `steps/`, `apis/`, etc.; 311 files, matching the documented upper bound.
- No code repositories changed.

## Open items

- Skills are snapshots of catalogue 2026.09.16; prefer https://docs.abdm.gov.in/docs/nhcx/v1 and the MCP server for current docs.
- Verify response shapes against real NHCX sandbox calls before relying on skill samples.
