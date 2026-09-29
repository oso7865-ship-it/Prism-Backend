"""Verify that the exact deployment digest can be downloaded without credentials."""

import argparse
import hashlib
import json
import re
import urllib.request

REPOSITORY = "oso7865-ship-it/prism-backend"


def verify(image):
    if not re.fullmatch(re.escape("ghcr.io/" + REPOSITORY) + r"@sha256:[0-9a-f]{64}", image):
        raise ValueError("INVALID_PUBLIC_IMAGE")
    digest = image.split("@", 1)[1]
    with urllib.request.urlopen(
        "https://ghcr.io/token?service=ghcr.io&scope=repository:" + REPOSITORY + ":pull", timeout=20
    ) as response:
        token = json.load(response)["token"]
    request = urllib.request.Request(
        "https://ghcr.io/v2/" + REPOSITORY + "/manifests/" + digest,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": (
                "application/vnd.oci.image.manifest.v1+json, "
                "application/vnd.docker.distribution.manifest.v2+json, "
                "application/vnd.oci.image.index.v1+json"
            ),
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if "sha256:" + hashlib.sha256(response.read(4 * 1024 * 1024)).hexdigest() != digest:
            raise ValueError("PUBLIC_IMAGE_DIGEST_MISMATCH")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    try:
        verify(args.image)
    except (OSError, ValueError, KeyError):
        print("PUBLIC_IMAGE_VERIFICATION_FAILED")
        return 1
    print("PUBLIC_IMAGE_VERIFIED_WITHOUT_CREDENTIALS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
