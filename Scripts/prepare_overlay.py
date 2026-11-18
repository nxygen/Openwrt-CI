#!/usr/bin/env python3
"""Safely quote values embedded in the first-boot shell scripts."""
import os
import pathlib
import shlex
import sys

root = pathlib.Path(sys.argv[1]) / "etc" / "uci-defaults"
for filename, replacements in {
    "99-custom": {"__ROOT_PASSWORD_SHELL__": "WRT_PW"},
    "98-tr3000-wifi": {
        "__SSID_SHELL__": "WRT_SSID",
        "__PASSWORD_SHELL__": "WRT_WORD",
    },
}.items():
    path = root / filename
    if not path.exists():
        continue
    content = path.read_text(encoding="utf-8")
    for placeholder, variable in replacements.items():
        if content.count(placeholder) != 1:
            raise ValueError(f"Missing or duplicate placeholder {placeholder} in {path}")
        content = content.replace(placeholder, shlex.quote(os.environ.get(variable, "")))
    path.write_text(content, encoding="utf-8")
