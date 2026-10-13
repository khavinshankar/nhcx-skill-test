# Uncommitted work at publication

The patches preserve the active backend and frontend worktrees' tracked changes and untracked source files at publication time. They concern beneficiary selection and were already in progress in another task. They have **not** been committed into the published code branches or validated as completed fixes by this publication task.

Base commits and SHA-256 checksums are in `../repositories.json`. After restoring the code repositories, review a patch before applying it, for example:

```sh
git -C care apply --check ../review/wip/care.patch
git -C care apply ../review/wip/care.patch
git -C care_fe apply --check ../review/wip/care_fe.patch
git -C care_fe apply ../review/wip/care_fe.patch
```

The unrelated local deletion of the parent's `PROGRESS.md` was left untouched and is not included. Ignored environment files, credentials, local databases and dependency directories are not review artifacts and are not included.
