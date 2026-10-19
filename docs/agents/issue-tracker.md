# Issue tracker: Local Markdown

Issues and specs live as Markdown files in `.scratch/`, not GitHub Issues.

## Conventions

- Use one feature directory: `.scratch/<feature-slug>/`.
- Store the spec at `.scratch/<feature-slug>/spec.md`.
- Store one implementation ticket per file at
  `.scratch/<feature-slug>/issues/NN-<slug>.md`, numbered from `01`.
- Record triage state in a `Status:` line near the top of each ticket, using
  [triage labels](triage-labels.md).
- Append conversation under a `## Comments` heading at the bottom of the file.

## Skill operations

- "Publish to the issue tracker" means create the appropriate local file and
  its parent directories.
- "Fetch the relevant ticket" means read the referenced local ticket file.
  Resolve a ticket number within the specified feature; ask when ambiguous.

## Wayfinding operations

- Map: `.scratch/<effort>/map.md`, with Notes, Decisions-so-far, and Fog sections.
- Child ticket: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`,
  with its question in the body.
- Record ticket type in `Type:` as `research`, `prototype`, `grilling`, or `task`.
- Wayfinder uses its own lifecycle: open tickets become `Status: claimed`, then
  `Status: resolved`, rather than the triage role values.
- Record dependencies in `Blocked by: NN, NN`. All listed tickets must be
  resolved before the dependent ticket is unblocked.
- Select the lowest-numbered open, unblocked, unclaimed ticket.
- Save `Status: claimed` before beginning work.
- To resolve, append an `## Answer` section, save `Status: resolved`, and append
  a linked summary to Decisions-so-far in the map.
