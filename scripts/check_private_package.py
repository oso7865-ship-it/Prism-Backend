"""Refuse to publish application images into a public or inaccessible package."""

import argparse
import json
import os
import urllib.error
import urllib.request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args(argv)
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        print("GHCR_VISIBILITY_CHECK_FAILED")
        return 1
    request = urllib.request.Request(
        "https://api.github.com/users/oso7865-ship-it/packages/container/prism-backend",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            package = json.load(response)
        if not isinstance(package, dict) or package.get("visibility") != "private":
            raise ValueError("PRIVATE_PACKAGE_REQUIRED")
        print("GHCR_VISIBILITY_PRIVATE")
        return 0
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and args.allow_missing:
            print("GHCR_NEW_PACKAGE_DEFAULT_PRIVATE")
            return 0
        print("GHCR_VISIBILITY_CHECK_FAILED")
    except (OSError, ValueError, KeyError):
        print("GHCR_VISIBILITY_CHECK_FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
