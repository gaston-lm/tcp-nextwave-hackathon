# Codex repository instructions

Always follow the active system and developer instructions. These repository instructions add
project-specific requirements; they do not override higher-priority instructions.

## After coding

Before reporting an implementation task as complete:

1. Re-read the active developer instructions and confirm the completed work complies with them.
2. Run `make lint` after all code edits.
3. Run focused tests relevant to the change when the required dependencies and services are
   available. Do not claim tests passed when they could not run.
4. Run `git diff --check` to catch whitespace errors.
5. Update the relevant README files whenever the work changes repository design, architecture,
   setup, public interfaces, data flow, or implementation behavior. Keep the root README and any
   affected service or data README consistent with the code.
6. Fix every failure from these checks and rerun the failed command until it passes, or report
   the precise external blocker.
7. In the final response, state which verification commands passed and clearly disclose any that
   could not run.

Do not make unrelated cleanup changes while satisfying this checklist.
