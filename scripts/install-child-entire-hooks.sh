#!/bin/sh
# Install a prepare-commit-msg hook in each child repository that adds an
# "Entire-Session: <id>" trailer to commits made by an agent session (plus
# "Entire-Subagent: <id>" when a Copilot subagent made the commit). Entire
# stores the session's checkpoints in this parent repository, so the trailer
# links child commits to `entire checkpoint list --session <id>` here.
# Re-run after cloning a child repository. Existing non-Entire hooks are kept.
set -eu

parent=$(dirname "$(git -C "$(dirname "$0")" rev-parse --path-format=absolute --git-common-dir)")
marker="# nhcx-entire-session-trailer"

for repo in care care/care_abdm care_fe care_abdm_fe; do
  dir="$parent/$repo"
  if ! git -C "$dir" rev-parse --git-dir >/dev/null 2>&1; then
    echo "skip $repo: not a git repository"
    continue
  fi
  hooks=$(git -C "$dir" rev-parse --path-format=absolute --git-path hooks)
  hook="$hooks/prepare-commit-msg"
  if [ -e "$hook" ] && ! grep -q "$marker" "$hook"; then
    echo "skip $repo: $hook exists and is not managed by this script"
    continue
  fi
  mkdir -p "$hooks"
  cat >"$hook" <<EOF
#!/bin/sh
$marker
# Installed by $parent/scripts/install-child-entire-hooks.sh
case "\${2:-}" in merge|squash) exit 0 ;; esac
command -v entire >/dev/null 2>&1 || exit 0
# Copilot holds ~/.copilot/session-state/<top-level session>/inuse.<pid>.lock;
# subagents run in the same process but export their own
# COPILOT_AGENT_SESSION_ID. Entire's ancestry fallback can pick a subagent or
# title-generator session, so it is used only when neither is available.
sid= sub=\${COPILOT_AGENT_SESSION_ID:-} pid=\$PPID
while [ -z "\$sid" ] && [ "\${pid:-1}" -gt 1 ]; do
  for lock in "\$HOME"/.copilot/session-state/*/inuse."\$pid".lock; do
    [ -e "\$lock" ] && sid=\$(basename "\$(dirname "\$lock")") && break
  done
  pid=\$(ps -o ppid= -p "\$pid" 2>/dev/null | tr -d ' ')
done
[ -n "\$sid" ] || sid=\$sub
[ "\$sub" != "\$sid" ] || sub=
[ -n "\$sid" ] || sid=\$(cd '$parent' && entire session current --json 2>/dev/null | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except ValueError:
    sys.exit()
if d.get("resolution") in ("caller-env", "ancestry"):
    print(d.get("session_id", ""))
') || exit 0
[ -n "\$sid" ] || exit 0
git interpret-trailers --in-place --if-exists addIfDifferent --trailer "Entire-Session: \$sid" "\$1"
[ -z "\$sub" ] || git interpret-trailers --in-place --if-exists addIfDifferent --trailer "Entire-Subagent: \$sub" "\$1"
EOF
  chmod +x "$hook"
  echo "installed $repo"
done
