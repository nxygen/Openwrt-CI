import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "Scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sources = load("resolve_sources")
feeds = load("verify_feeds")


class VersionTests(unittest.TestCase):
    def test_stable_sort_and_exclusions(self):
        page = '<a href="25.12.9/">x</a><a href="26.1.0-rc1/">x</a><a href="26.1.0/">x</a><a href="25.12.10/">x</a><a href="99.0-SNAPSHOT/">x</a>'
        self.assertEqual(sources.latest_version(page), "26.1.0")
        self.assertEqual(sources.latest_version('<a href="25.12.9/"></a><a href="25.12.10/"></a>'), "25.12.10")

    def test_empty_fails(self):
        with self.assertRaises(ValueError):
            sources.latest_version('<a href="25.12.0-rc1/">x</a>')

    @mock.patch.object(sources.subprocess, "run")
    def test_tag_peeling_and_missing(self, run):
        tag = "refs/tags/v25.12.2"
        run.return_value.stdout = f'{"a"*40}\t{tag}\n{"b"*40}\t{tag}^{{}}\n'
        self.assertEqual(sources.resolve_ref("repo", tag), "b" * 40)
        run.return_value.stdout = ""
        with self.assertRaises(ValueError):
            sources.resolve_ref("repo", tag)
        run.side_effect = subprocess.CalledProcessError(1, "git")
        with self.assertRaises(subprocess.CalledProcessError):
            sources.resolve_ref("repo", tag)

    @mock.patch.object(sources.urllib.request, "urlopen", side_effect=OSError("network unavailable"))
    def test_network_failure_does_not_fall_back(self, _urlopen):
        with self.assertRaises(OSError):
            sources.main()


class FeedTests(unittest.TestCase):
    def test_pinned_only(self):
        sha = "a" * 40
        self.assertEqual(feeds.parse_feeds(f"src-git luci https://example.org/luci.git^{sha}\n"), {"luci": sha})
        for line in ("src-git luci https://example.org/luci.git;main",
                     "src-git luci https://example.org/luci.git",
                     "src-link local /tmp/feed", ""):
            with self.subTest(line=line), self.assertRaises(ValueError):
                feeds.parse_feeds(line)

    def test_checkout_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "feeds.conf.default").write_text("src-git luci https://example.org/luci.git^" + "a" * 40)
            with mock.patch.object(feeds.sys, "argv", ["verify_feeds.py", tmp]), \
                 mock.patch.object(feeds.subprocess, "check_output", return_value="b" * 40):
                with self.assertRaises(ValueError):
                    feeds.main()


class ShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bash = os.environ.get("TEST_BASH", "bash")

    def run_shell(self, script, cwd=None, env=None):
        return subprocess.run([self.bash, "-c", script], cwd=cwd, env=env,
                              text=True, capture_output=True)

    def test_proxy_choices(self):
        text = (ROOT / "Scripts/Settings.sh").read_text(encoding="utf-8")
        block = text[text.index('case "${WRT_PROXY:-nikki}"'):text.index("# #编译器优化")]
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / ".config"
            for proxy in ("nikki", "openclash", "momo", "bad"):
                config.write_text("CONFIG_PACKAGE_luci-app-openclash=y\nCONFIG_PACKAGE_luci-app-nikki=y\n")
                result = self.run_shell(block, tmp, dict(os.environ, WRT_PROXY=proxy))
                if proxy == "bad":
                    self.assertNotEqual(result.returncode, 0)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual([line for line in config.read_text().splitlines() if line.endswith("=y")],
                                     [f"CONFIG_PACKAGE_luci-app-{proxy}=y"])

    def test_overlay_values_are_shell_quoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "etc/uci-defaults"
            directory.mkdir(parents=True)
            (directory / "99-custom").write_text("value=__ROOT_PASSWORD_SHELL__\nprintf '%s' \"$value\"\n")
            env = dict(os.environ, WRT_PW="a'$(echo unsafe)\\b")
            subprocess.run(["python", str(ROOT / "Scripts/prepare_overlay.py"), tmp], env=env, check=True)
            result = self.run_shell((directory / "99-custom").read_text())
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, env["WRT_PW"])

    def test_patch_applies_once_and_rejects_changes(self):
        patch = ROOT / "patches/100-tr3000-large-ubi.patch"
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            path = Path(tmp) / "target/linux/mediatek/dts/mt7981b-cudy-tr3000-v1.dts"
            path.parent.mkdir(parents=True)
            subprocess.run(["git", "init", "-q", tmp], check=True)
            # Keep this context faithful to the official v25.12.2 DTS.
            path.write_text("\n" * 18 + "\tmediatek,bmt-max-ratio = <1>;\n\tmediatek,bmt-max-reserved-blocks = <64>;\n};\n\n&ubi {\n\treg = <0x5c0000 0x4000000>;\n};\n")
            def apply(*args):
                return subprocess.run(["git", "apply", *args, str(patch)], cwd=tmp, capture_output=True)
            self.assertEqual(apply("--check").returncode, 0)
            self.assertEqual(apply().returncode, 0)
            self.assertIn("0x7240000", path.read_text())
            self.assertNotEqual(apply("--check").returncode, 0)
            path.write_text(path.read_text().replace("0x7240000", "0x3000000"))
            self.assertNotEqual(apply("--check").returncode, 0)

    def test_wifi_bands_and_missing_interfaces(self):
        script = (ROOT / "files/etc/uci-defaults/98-tr3000-wifi").read_text(encoding="utf-8")
        script = script.replace(". /lib/functions.sh", "").replace(". /lib/functions/system.sh", "")
        script = script.replace("__SSID_SHELL__", "'Openwrt'").replace("__PASSWORD_SHELL__", "'12345678'")
        mock_functions = r"""
board_name() { echo cudy,tr3000-v1; }
logger() { :; }
uci() { printf '%s\n' "$*" >> "$CALLS"; }
config_load() { :; }
config_foreach() {
    if [ "$2" = wifi-device ]; then
        [ "$SCENARIO" != none ] && "$1" radio0
        [ "$SCENARIO" = dual ] && "$1" radio1
        [ "$SCENARIO" = unknown ] && "$1" radio1
    else
        "$1" default0
        "$1" default1
    fi
    return 0
}
config_get() {
    local value=''
    case "$2:$3" in
        radio0:band) value=2g ;;
        radio1:band) [ "$SCENARIO" = dual ] && value=5g ;;
        default0:device) value=radio0 ;;
        default1:device) value=radio1 ;;
        default0:mode|default1:mode) value=ap ;;
    esac
    printf -v "$1" '%s' "$value"
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            calls = Path(tmp) / "calls"
            for scenario in ("none", "single", "unknown", "dual"):
                calls.write_text("")
                env = dict(os.environ, SCENARIO=scenario, CALLS=str(calls).replace("\\", "/"))
                result = self.run_shell(mock_functions + script, tmp, env)
                self.assertEqual(result.returncode, 0, result.stderr)
                changes = calls.read_text()
                if scenario == "dual":
                    self.assertIn("wireless.default1.ssid=Openwrt_5GHz", changes)
                    self.assertIn("commit wireless", changes)
                else:
                    self.assertEqual(changes, "")


if __name__ == "__main__":
    unittest.main()
