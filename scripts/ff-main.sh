#!/bin/sh
# Fast-forward main to the commit just made on a task branch, so that
# `entire checkpoint list` on main shows its checkpoint. Called from the parent
# repository's post-commit hook after Entire's own post-commit step. It never
# creates merge commits, never pushes and never fails the commit.
#
# Disable with: git config nhcx.autoFastForwardMain false

target=main

unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_PREFIX

[ "$(git config --bool nhcx.autoFastForwardMain)" = false ] && exit 0

branch=$(git symbolic-ref --short -q HEAD) || exit 0
[ "$branch" = "$target" ] && exit 0
git show-ref --verify -q "refs/heads/$target" || exit 0

warn() { echo "ff-main: $* main was not updated." >&2; exit 0; }

git merge-base --is-ancestor "$target" HEAD ||
	warn "$target has commits that $branch lacks; merge or rebase manually."

main_wt=$(git worktree list --porcelain | awk -v ref="refs/heads/$target" '
	/^worktree / { wt = substr($0, 10) }
	$0 == "branch " ref { print wt; exit }')

if [ -z "$main_wt" ]; then
	git update-ref -m "ff-main: fast-forward to $branch" \
		"refs/heads/$target" HEAD "$(git rev-parse "$target")" ||
		warn "update-ref failed."
elif [ -n "$(git -C "$main_wt" status --porcelain --untracked-files=no)" ]; then
	warn "$main_wt has uncommitted changes."
else
	git -C "$main_wt" merge --ff-only -q "$branch" ||
		warn "fast-forward in $main_wt failed."
fi

echo "ff-main: $target -> $(git rev-parse --short HEAD) ($branch)" >&2
