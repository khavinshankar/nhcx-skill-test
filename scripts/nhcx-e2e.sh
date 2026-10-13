#!/usr/bin/env bash
# NHCX end-to-end tests against the live NHCX sandbox, run from the host.
#
#   care/scripts/nhcx-e2e.sh list | check | payer ...      (passed to the backend)
#   care/scripts/nhcx-e2e.sh run [ids|irdai|pmjay] [--mode cli|gui|both] [--headed] [--report path]
#
# The CLI runner runs inside the backend container (manage.py nhcx_e2e). The
# GUI runner (Playwright, care_fe/tests/nhcx) runs on the host, where the
# screens and the browser are, and takes payer decisions through the backend.
# Exit code (T2L): 0 no test failed, 1 a test failed, 2 a setup check failed or
# the screens are unreachable. Results are in the report (nhcx-plan/e2e.json).
#
# Environment: NHCX_TEST_BACKEND_CONTAINER (default care-nhcx-backend),
# NHCX_TEST_FE_DIR (default ../care_fe beside this repository),
# NHCX_TEST_APP_URL (default http://localhost:4000).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CARE="$(dirname "$HERE")"
CONTAINER="${NHCX_TEST_BACKEND_CONTAINER:-care-nhcx-backend}"
FE="${NHCX_TEST_FE_DIR:-$(dirname "$CARE")/care_fe}"
APP_URL="${NHCX_TEST_APP_URL:-http://localhost:4000}"

backend() {
  docker exec "$CONTAINER" python manage.py nhcx_e2e "$@"
}

if [ "${1:-}" != "run" ]; then
  backend "$@"
  exit $?
fi
shift

mode="" headed="" report="" tests=()
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) mode="$2"; shift 2 ;;
    --mode=*) mode="${1#*=}"; shift ;;
    --headed) headed="--headed"; shift ;;
    --report) report="$2"; shift 2 ;;
    --report=*) report="${1#*=}"; shift ;;
    *) tests+=("$1"); shift ;;
  esac
done
mode="${mode:-both}"
report_args=()
[ -n "$report" ] && report_args=(--report "$report")

# irdai/pmjay/T-ids resolve to the scenario ids the GUI runner filters on.
ids="$(backend list --ids ${tests[@]+"${tests[@]}"} 2>/dev/null | tail -1)"

cli_code=0
if [ "$mode" = "cli" ] || [ "$mode" = "both" ]; then
  backend run ${tests[@]+"${tests[@]}"} --mode cli ${report_args[@]+"${report_args[@]}"} || cli_code=$?
  if [ "$cli_code" = 2 ]; then
    exit 2
  fi
fi
if [ "$mode" = "cli" ]; then
  exit "$cli_code"
fi

if ! curl -fsS -o /dev/null --max-time 10 "$APP_URL"; then
  echo "the screens are not served at $APP_URL; start care_fe (npm run dev) first" >&2
  exit 2
fi
(
  cd "$FE"
  NHCX_TEST_ONLY="$ids" npx playwright test --config tests/nhcx/playwright.config.ts \
    --reporter=line $headed
) || true

# Each GUI test merges its own entry; this prints both runners' results.
backend report $ids ${report_args[@]+"${report_args[@]}"}
