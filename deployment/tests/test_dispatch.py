import contextlib
import importlib.util
import io
import json
import os
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch


def load(name):
    path = Path(__file__).resolve().parents[2] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dispatch = load("dispatch_ec2")
package = load("check_private_package")
ENV = {
    "PRISM_IMAGE": "ghcr.io/oso7865-ship-it/prism-backend@sha256:" + "a" * 64,
    "GITHUB_SHA": "b" * 40,
    "GITHUB_RUN_NUMBER": "23",
    "PRISM_EC2_INSTANCE_ID": "i-02d892cf8019b2d7a",
    "PRISM_SSM_DOCUMENT": "PrismDeployBackend",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "push",
}


class DispatchTests(unittest.TestCase):
    def test_dispatch_is_not_success_until_ssm_finishes(self):
        with (
            patch.dict(os.environ, ENV, clear=True),
            patch.object(
                dispatch,
                "aws",
                side_effect=[
                    {"Command": {"CommandId": "example"}},
                    None,
                    {"Status": "InProgress"},
                    {"Status": "Success"},
                ],
            ) as aws,
            patch.object(dispatch.time, "sleep"),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(dispatch.main(), 0)
            self.assertEqual(aws.call_count, 4)
            command = aws.call_args_list[0].args[0]
            self.assertEqual(command[command.index("--document-version") + 1], "1")
            payload = json.loads(command[command.index("--parameters") + 1])
            self.assertEqual(set(payload), {"Image", "Revision", "Sequence"})

    def test_failed_remote_command_never_reports_success_or_raw_output(self):
        for status in ["Failed", "Cancelled", "TimedOut", "Unexpected"]:
            output = io.StringIO()
            with (
                patch.dict(os.environ, ENV, clear=True),
                patch.object(
                    dispatch,
                    "aws",
                    side_effect=[
                        {"Command": {"CommandId": "example"}},
                        {"Status": status, "StandardOutputContent": "PRIVATE_RUNTIME_VALUE"},
                    ],
                ),
                contextlib.redirect_stdout(output),
            ):
                self.assertEqual(dispatch.main(), 1)
            self.assertNotIn("PRIVATE_RUNTIME_VALUE", output.getvalue())

    def test_untrusted_branch_event_or_image_never_reaches_aws(self):
        for key, value in [
            ("GITHUB_REF", "refs/heads/dev"),
            ("GITHUB_EVENT_NAME", "pull_request"),
            ("PRISM_IMAGE", ENV["PRISM_IMAGE"] + ";id"),
            ("PRISM_SSM_DOCUMENT", "AWS-RunShellScript"),
        ]:
            with (
                patch.dict(os.environ, {**ENV, key: value}, clear=True),
                patch.object(dispatch, "aws") as aws,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(dispatch.main(), 1)
                aws.assert_not_called()

    def test_poll_deadline_is_a_failure(self):
        with (
            patch.dict(os.environ, ENV, clear=True),
            patch.object(dispatch, "aws", return_value={"Command": {"CommandId": "example"}}),
            patch.object(dispatch.time, "monotonic", side_effect=[0, 1321]),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(dispatch.main(), 1)


class PrivatePackageTests(unittest.TestCase):
    def test_only_private_package_is_accepted(self):
        for payload, expected in [
            ({"visibility": "private"}, 0),
            ({"visibility": "public"}, 1),
            ({}, 1),
            ([], 1),
        ]:
            with (
                patch.dict(os.environ, {"GH_TOKEN": "test-only"}),
                patch.object(
                    package.urllib.request, "urlopen", return_value=io.StringIO(json.dumps(payload))
                ),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(package.main([]), expected)

    def test_missing_allowed_only_before_first_publish_and_403_never_allowed(self):
        for code, argv, expected in [
            (404, ["--allow-missing"], 0),
            (404, [], 1),
            (403, ["--allow-missing"], 1),
        ]:
            with (
                patch.dict(os.environ, {"GH_TOKEN": "test-only"}),
                patch.object(
                    package.urllib.request,
                    "urlopen",
                    side_effect=urllib.error.HTTPError(
                        "https://api.github.com", code, "", {}, None
                    ),
                ),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(package.main(argv), expected)

    def test_missing_token_fails_without_network(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(package.urllib.request, "urlopen") as request,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(package.main([]), 1)
            request.assert_not_called()
