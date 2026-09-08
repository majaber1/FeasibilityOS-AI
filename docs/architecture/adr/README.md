# Architecture Decision Records

An ADR is required whenever a feature does not fit
`docs/architecture/SAUDI_BUSINESS_MASTER_ARCHITECTURE.md` (a new Wave, a
new layer, a structural change to the persistent workspace, etc.). Do not
silently redesign the master architecture to fit a feature -- write the
ADR, get it explicitly approved, then implement.

## Process

1. Copy the template below into `docs/architecture/adr/NNNN-short-title.md`
   (four-digit sequence number, e.g. `0001-franchise-fit-scoring.md`).
2. Fill in every section honestly, including the alternatives you didn't
   pick and why.
3. Present it for explicit approval before writing any implementation code
   for the change it describes.
4. Once approved, implement it and update
   `SAUDI_BUSINESS_MASTER_ARCHITECTURE.md` to reflect the now-approved
   change in the same commit/PR as the implementation.
5. If rejected or superseded later, leave the ADR in place and add a note
   at the top ("Superseded by 0007") rather than deleting it -- it's a
   historical record of why a decision was made.

## Template

```markdown
# NNNN — Short Title

Status: PROPOSED | APPROVED | REJECTED | SUPERSEDED
Date: YYYY-MM-DD

## Problem

What user/business need isn't served by the current architecture?

## Current Architecture

What does SAUDI_BUSINESS_MASTER_ARCHITECTURE.md say today, and why doesn't
it cover this?

## Reason Change Is Needed

Why is extending/changing the architecture the right call, rather than
fitting the feature into an existing Wave/layer?

## Proposed Change

Exactly what changes: new Wave, new layer, new persistent resource, new
engine, etc.

## Alternatives

What else was considered, and why was it not chosen?

## Data Impact

New tables/columns, migrations required, existing-data implications.

## API Impact

New/changed endpoints, breaking changes to existing contracts.

## Security Impact

Ownership, auth, data exposure implications.

## Migration Impact

Additive only? Any backfill required? Rollback plan.

## Backward Compatibility

What existing behavior, if any, changes for existing users/data.

## Risks

What could go wrong, and how would we know.
```
