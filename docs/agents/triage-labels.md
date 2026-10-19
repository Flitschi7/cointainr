# Triage Labels

Use these exact strings as the `Status:` value when triaging local issues.

| Skill role        | Local status      | Meaning                                  |
| ----------------- | ----------------- | ---------------------------------------- |
| `needs-triage`    | `needs-triage`    | Awaiting maintainer evaluation           |
| `needs-info`      | `needs-info`      | Awaiting more information                |
| `ready-for-agent` | `ready-for-agent` | Fully specified for agent implementation |
| `ready-for-human` | `ready-for-human` | Requires human implementation            |
| `wontfix`         | `wontfix`         | Will not be actioned                     |

When a skill requests a triage label, update the local ticket's `Status:` line.
Wayfinder uses the separate claimed/resolved lifecycle described in
[issue tracker conventions](issue-tracker.md).
