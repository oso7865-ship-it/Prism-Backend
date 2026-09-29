import hashlib
import importlib.util
import io
import json
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "public_image", Path(__file__).parents[2] / "scripts/check_public_image.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
MANIFEST = b'{"schemaVersion":2}'
IMAGE = "ghcr.io/" + checker.REPOSITORY + "@sha256:" + hashlib.sha256(MANIFEST).hexdigest()


class PublicImageTests(unittest.TestCase):
    def test_uses_anonymous_registry_token_and_exact_digest(self):
        with patch.object(
            checker.urllib.request,
            "urlopen",
            side_effect=[
                io.StringIO(json.dumps({"token": "anonymous-registry-token"})),
                io.BytesIO(MANIFEST),
            ],
        ) as network:
            checker.verify(IMAGE)
            self.assertIsInstance(network.call_args_list[0].args[0], str)
            request = network.call_args_list[1].args[0]
            self.assertEqual(request.get_header("Authorization"), "Bearer anonymous-registry-token")
            self.assertTrue(request.full_url.endswith(IMAGE.split("@")[1]))

    def test_mismatched_digest_fails(self):
        with patch.object(
            checker.urllib.request,
            "urlopen",
            side_effect=[
                io.StringIO(json.dumps({"token": "anonymous"})),
                io.BytesIO(b"wrong image"),
            ],
        ):
            with self.assertRaisesRegex(ValueError, "DIGEST_MISMATCH"):
                checker.verify(IMAGE)

    def test_other_registry_or_mutable_tag_never_reaches_network(self):
        for image in [
            IMAGE.replace("ghcr.io", "example.com"),
            "ghcr.io/" + checker.REPOSITORY + ":latest",
            IMAGE + ";id",
        ]:
            with patch.object(checker.urllib.request, "urlopen") as network:
                with self.assertRaises(ValueError):
                    checker.verify(image)
                network.assert_not_called()

    def test_private_or_unavailable_registry_does_not_pass(self):
        with patch.object(
            checker.urllib.request,
            "urlopen",
            side_effect=urllib.error.HTTPError("https://ghcr.io", 403, "", {}, None),
        ):
            with self.assertRaises(urllib.error.HTTPError):
                checker.verify(IMAGE)
