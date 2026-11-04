# Hermes persistent goals

Load only for explicit persistent-goal work. Checked against local v0.22.5 CLI help and `hermes_cli/goal_command.py` on 2026-10-28; goal creation, file execution and pause were tested; automatic completion failed due to judge API errors. See runtime evidence below.

## Preconditions

- Resolve `hermes` on PATH and inspect `hermes --version`; use the reported install directory to locate source if necessary. Do not require git installation or a fixed path: a packaged install is not automatically invalid.
- Resolve the actual authorized project directory. Do not restrict all projects to a fixed parent directory or reuse historical container paths.
- Read project rules. If execution must occur in its Compose services, identify actual service names and commands, inspect `docker compose ps`, and instruct Hermes to use those entrypoints. Start services only when covered by user authorization.
- CLI goal use does not require gateway/dashboard. For an explicitly requested gateway workflow, inspect only relevant service status without environment output; start or reconfigure services only when authorized. Do not assume historic model/server/dashboard ports or authentication settings.
- Goal creation is persistent execution: state objective, directory and acceptance/stop conditions first. A clear task request can authorize ordinary execution; do not ask redundantly. Clarify missing scope or significant compute/cost changes.

## Interactive command handling

Run `hermes chat --cli --source cli --in PROJECT` and, for an existing owned session, add `--resume SESSION_ID`. Use an owned PTY and submit with carriage return. Do not pass slash commands via one-shot query: that path may submit literal model input.

1. `/goal status` inspects the existing goal.
2. Do not replace, clear or resume a different existing goal without authorization.
3. `/goal OBJECTIVE` creates/sets a goal and triggers execution.
4. `/goal draft OBJECTIVE` ALSO sets the goal and triggers execution after generating a completion contract. It is not a read-only draft or preview. Do not use it merely to refine a plan.
5. `/goal pause` pauses; `/goal resume` resumes an authorized goal. `/goal clear`, `/goal stop`, `/goal done` clear state and require appropriate authorization.
6. Goals whose literal text starts with a control word can use `/goal -- TEXT`, as supported by the installed parser.
7. Monitor status, tool activity, permission requests and actual artifacts. A quiet terminal does not prove success. Distinguish terminal input failures, permission waits and inference failures; do not restart/change models blindly.

Goal gates can execute shell commands without later approval. Do not add gates without explicit approval of their commands. Do not use `--yolo` or `--accept-hooks` without authorization.

On shutdown, exit an idle owned CLI gracefully; do not send Ctrl-D into an active prompt/task blindly. Report whether the CLI remains running and the current goal state. No session deletion, goal clearing, config edits, upgrades, rollback or unrelated service changes are implicit in this workflow.

## Evidence required

Confirm intended directory, actual goal-handler acknowledgment and state transitions, selected model/provider, and task results independently. Container work must be verified through the project's own declared service. Report failures and unresolved decisions rather than treating a goal acknowledgment as completion.


## Runtime test 2026-10-28

Use `hermes chat --cli --source cli --in PROJECT --provider deepseek --model deepseek-flash` when passing chat-only options; passing --source at the root invocation failed. In the automated tmux test, sending literal command text and Enter in separate calls worked; bundling paste and Enter initially only inserted text. Always verify actual handler acknowledgment.

A bounded goal wrote and read back a two-line file successfully. Automatic completion DID NOT work: the CLI reported judge API errors after five turns, while the worker repeatedly said the task was complete. The test was explicitly paused and the CLI exited. No judge configuration was changed. Treat goal execution as only partially verified; diagnose auxiliary goal_judge separately from the main worker, and stop bounded tests on repeated judge failure. A worker's completion claim cannot terminate a persistent goal by itself.
