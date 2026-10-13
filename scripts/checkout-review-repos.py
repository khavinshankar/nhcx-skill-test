#!/usr/bin/env python3
"""Restore published child repositories at the recorded commits; never overwrite."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remote', help='Override Git URL (also useful for offline verification)')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    manifest = json.loads((root / 'review/repositories.json').read_text())
    remote = args.remote or manifest['remote']
    # Preflight all paths before making any changes.
    for repo in manifest['repositories']:
        if (root / repo['path']).exists():
            parser.error(f"{repo['path']} already exists; use a fresh parent clone")
    for repo in manifest['repositories']:
        target = root / repo['path']
        subprocess.run(['git', 'clone', '--single-branch', '--branch', repo['branch'],
                        remote, str(target)], check=True)
        subprocess.run(['git', '-C', str(target), 'checkout', '--detach', repo['commit']], check=True)
        print(f"Restored {repo['path']} at {repo['commit']}", flush=True)
    print('Uncommitted review patches are available in review/wip/; not applied automatically.')


if __name__ == '__main__':
    main()
