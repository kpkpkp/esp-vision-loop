# Session Chronicle: Prime & Self-Awareness

**Date:** 2026-03-28
**Platform:** Termux on Android (aarch64, 16GB RAM)
**Duration:** ~30 minutes
**Outcome:** Project cloned to device, `/prime` skill created, CLAUDE.md established

---

## What Got Done

### Environment surveyed
- Full sandbox audit: Android 15, Termux, unprivileged SELinux context, 8 cores, 16GB RAM
- RAM improved from 1.6GB to 2.8GB available after user closed apps — confirmed the OOM budget matters
- GitHub repos enumerated: 29 repos under kpkpkp, WitnessMark ecosystem identified as main active project family

### Repo cloned
- SSH clone failed (host key verification) — fell back to HTTPS, worked immediately
- All project files present: orchestrator, build pipeline, codegen, config, chronicles, logs
- One iteration log exists from prior session (iteration_001.json)

### `/prime` slash command created
- Built as a proper Claude Code skill at `.claude/skills/prime/SKILL.md`
- Reads project state, checks all prerequisites, reports milestones, proposes next action
- Replaces the need to manually paste NEXT_SESSION.md into each conversation

### `CLAUDE.md` established
- Project-root instructions that Claude Code auto-loads on `cd`
- Encodes the critical rules: don't re-run set-target, don't run ollama + builds together, build with ninja -j1
- Documents architecture and platform constraints

---

## Obstacles Overcome

### 1. The shell script trap

First instinct was to write a `prime.sh` bash script — clone repo, check prereqs, dump status, print context block for pasting. The user stopped this mid-write.

**What was wrong:** The problem wasn't "how do I check prereqs." The problem was "how do I give Claude Code the context it needs to be effective on this project." A shell script solves the human's problem. A `/prime` skill solves the AI's problem.

**The fix:** A Claude Code skill that runs *inside* the conversation, reading files and checking state with the tools it already has — not a script that prints text for a human to copy-paste into a different tool.

### 2. SSH host key not in known_hosts

`git clone git@github.com:...` failed because GitHub's SSH host key wasn't in Termux's `known_hosts`. Rather than debugging SSH config, fell back to HTTPS. The `gh` CLI was already authenticated, so HTTPS just worked.

**Lesson:** When one transport fails, try the other. Don't debug SSH when HTTPS is sitting right there and the goal is "get the code."

### 3. Understanding the plugin system

Claude Code's skill/plugin system wasn't immediately obvious. Required reading the example plugin structure to understand: skills live in `.claude/skills/<name>/SKILL.md` with YAML frontmatter for description, allowed tools, and argument hints. The skill markdown is injected as a prompt when the user types the slash command.

---

## Lessons Learned

### 1. Don't script what the AI should think

A shell script that checks prereqs and prints status is a 2024 solution. In 2026, the AI *is* the session. It should read the files, check the state, and reason about what to do next — not parse the stdout of a bash script somebody else wrote.

The `/prime` skill doesn't print a dashboard. It *becomes* the dashboard by reading the project and thinking about it. That's a fundamentally different thing.

**Lesson:** If you're writing a script to feed context to an AI, you're adding an unnecessary translation layer. Let the AI read the source material directly.

### 2. Claude Code skills are project-scoped prompts, not code

A skill is just a markdown file with instructions. No runtime, no dependencies, no API. It's a way to say "when the user types `/prime`, here's what you should do." The power is in the specificity of the instructions, not in any executable logic.

**Lesson:** Skills are leverage — they encode institutional knowledge into a repeatable prompt. The chronicles, the constraints, the hard-won lessons about OOM and set-target — all of that lives in the skill now, not in someone's memory.

### 3. CLAUDE.md is the project's constitution

Any Claude Code session that `cd`s into the project automatically loads `CLAUDE.md`. This is where the non-negotiable rules go — the things that, if violated, cost 40 minutes (re-running set-target) or crash the phone (running ollama + builds). It's not documentation for humans. It's guardrails for the AI.

**Lesson:** Treat CLAUDE.md like a `.editorconfig` for AI behavior. Keep it short, keep it firm, keep it current.

### 4. The repo tour is the real prime

Reading NEXT_SESSION.md, the chronicles, the logs, the current main.c — that's what priming actually is. It's not running `free -m` and checking if Python is installed. Those are hygiene checks. The real value is the AI absorbing the project's history and current state so it can make informed decisions.

**Lesson:** Prereq checks are table stakes. Context loading is the actual prime.

---

## Wisdom

- **The best tool is the one that removes a copy-paste step.** Every time a human has to copy output from one tool and paste it into another, information is lost, context is broken, and errors creep in. The `/prime` skill eliminates the "read NEXT_SESSION.md and paste it into Claude" step that was the project's handoff mechanism.

- **Self-awareness is a feature.** This session was about making the project aware of itself — giving the AI a way to orient on first contact. That's not setup busywork. That's infrastructure. A project that can explain itself to its tools is a project that can be picked up by anyone (or any AI) at any time.

- **The chronicles are compounding.** Four sessions in, the chronicles directory contains more hard-won knowledge than most project wikis. The pattern of writing a chronicle at session end is paying dividends: each new session starts with the full institutional memory of every previous one. The AI reads the chronicles during `/prime` and inherits the wisdom of its predecessors.

- **Android as a dev platform is a solved problem — if you know the adapters.** proot for glibc, HTTPS for git, CLAUDE_CODE_TMPDIR for sandbox, `/prime` for session setup. Each obstacle had an adapter. The phone isn't hostile to development; it just speaks a different dialect.

---

## What's Next

The project is now self-priming. Next session:

1. Run `/prime` to load context
2. Check `logs/codegen_build_test.log` for the test results from the last hardware session
3. Get a compilable `main.c` through the build-error feedback loop
4. Flash to the real ESP32 and photograph the result
5. Close the loop for real

---

*"The AI that knows how to start is halfway to knowing how to finish."*
