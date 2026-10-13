#!/bin/sh
# Add the ff-main step to the parent repository's post-commit hook, after
# Entire's own step. Hooks live in the common git directory, so every worktree
# uses them. Rerun after `entire enable` or an Entire upgrade rewrites hooks.
set -eu

hooks=$(git rev-parse --path-format=absolute --git-common-dir)/hooks
hook=$hooks/post-commit
marker='# NHCX: fast-forward main'
line='top=$(git rev-parse --show-toplevel) && [ -f "$top/scripts/ff-main.sh" ] && sh "$top/scripts/ff-main.sh" || true'

if [ ! -f "$hook" ]; then
	printf '#!/bin/sh\n' >"$hook"
	chmod +x "$hook"
fi

if grep -qF "$marker" "$hook"; then
	echo "Already installed in $hook"
else
	printf '%s\n%s\n' "$marker" "$line" >>"$hook"
	echo "Installed in $hook"
fi
