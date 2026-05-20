# Agent Mandatory Rules

All agents **MUST** strictly follow all the rules listing below without exception!

## 1. Before Every Response: **ALWAYS** Check for available Skills

- After receiving a user message, check `available_skills` before responding.
- If any skill has >1% match, invoke it via Skill tool.
- Announce: "Using [skill name] to [purpose]"

## 2. Mode Distinction

### Plan Mode

**Skills**:
| Skill | Trigger |
|-------|---------|
| brainstorming | User proposes creative work (features, designs, architectures) |
| writing-plans | Design approved, generate implementation plan |
| systematic-debugging | Bugs, test failures, unexpected behavior |

### Build Mode

**Skills**:
| Skill | Trigger |
|-------|---------|
| test-driven-development | Before implementing any feature or fix |
| executing-plans | Plan exists, no subagent |
| subagent-driven-development | Plan exists, has subagent |
| using-git-worktrees | Before code changes, create isolated branch |
| verification-before-completion | Before claiming completion |
| requesting-code-review | After each task, before merge |
| finishing-a-development-branch | After all tasks complete |
| dispatching-parallel-agents | 2+ independent tasks |
| receiving-code-review | Receiving code review feedback |

## 3. Decision Tree

### Creative Work
→ `brainstorming` → `writing-plans` → User switches to Build Mode → Write plan → `subagent-driven-development` or `executing-plans`

### Bug Fix
→ `systematic-debugging` → `test-driven-development`

### Plan Exists
→ `subagent-driven-development` or `executing-plans`

### Code Change Without Branch
→ `using-git-worktrees`

### 2+ Independent Tasks
→ `dispatching-parallel-agents`

### All Tasks Complete
→ `finishing-a-development-branch`

## 4. **MUST FOLLOW**

| Rule |
|------|
| Check skills before every response |
| No brainstorming = no plan mode |
| No writing-plans = no code |
| No failing test = no production code |
| No branch = no code changes |
| No verification = no completion claim |
| Two reviews per task (spec + quality) |
| finishing-a-development-branch after all tasks |

## 5. Red Warnings — Stop Immediately

**Stop immediately upon violation detection**:
- Do not continue
- Do not fix
- Do not explain
- Wait for user instruction

Stop immediately if thinking:
- "Do first, check skill later"
- "Too simple for brainstorming"
- "I remember how"
- "Tests after"
- "Tests passed" (no verification)
- "Manually tested"
- "Feels done"
- "Small change, no review"
- "Self-review enough"
