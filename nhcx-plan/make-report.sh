#!/bin/sh
# nhcx-plan/make-report.sh: rebuild report.html every 10 seconds until stopped.
# "make-report.sh once" rebuilds it one time and exits with the builder's status.
cd "$(dirname "$0")" || exit 1
build() { python3 report.py; }
if [ "$1" = once ]; then build; exit $?; fi
while :; do
  build && echo "$(date '+%H:%M:%S') report.html rebuilt" || echo "$(date '+%H:%M:%S') report build failed"
  sleep 10
done
