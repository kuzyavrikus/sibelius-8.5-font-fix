
#!/usr/bin/env python3
"""
Sibelius 8.5 Font Fix for Modern macOS
Unofficial, experimental compatibility patch.

Tested: Apple M5, macOS Golden Gate 27, Sibelius 8.5
M6: not yet tested.
"""

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

FONT_PATH = Path(
    "Contents/Frameworks/QtGui.framework/Versions/4/QtGui"
)

OFFSET = 0x27DFEC
ORIGINAL = bytes.fromhex("0F 8C F8 06 00 00")
PATCHED = b"\x90" * 6

DEFAULT_SOURCE = Path("/Applications/Sibelius.app")
DEFAULT_TARGET = Path("/Applications/Sibelius-FontFix-Test.app")


def run(*args):
    subprocess.run(
        [str(arg) for arg in args],
        check=True
    )


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(binary, arch, output):
    run("lipo", "-thin", arch, binary, "-output", output)


def patch_status(data):
    actual = data[OFFSET:OFFSET + len(ORIGINAL)]

    if actual == ORIGINAL:
        return "original"
    if actual == PATCHED:
        return "patched"
    return f"unknown ({actual.hex(' ')})"


def check(app):
    library = app / FONT_PATH

    if not library.is_file():
        raise RuntimeError(f"QtGui not found: {library}")

    with tempfile.TemporaryDirectory() as td:
        thin = Path(td) / "QtGui-x86_64"
        extract(library, "x86_64", thin)

        status = patch_status(thin.read_bytes())

    print(f"Application: {app}")
    print(f"QtGui:       {library}")
    print(f"Status:      {status}")
    print(f"Offset:      0x{OFFSET:X}")

    return status


def apply(source, target):
    source = source.resolve()
    target = target.absolute()

    if not (source / FONT_PATH).is_file():
        raise RuntimeError("Source Sibelius QtGui not found")

    if target.exists():
        raise RuntimeError(
            f"Target already exists: {target}\n"
            "Refusing to overwrite an existing application."
        )

    if check(source) != "original":
        raise RuntimeError(
            "Source QtGui does not match the expected "
            "original bytes. No changes made."
        )

    print("\nCreating separate test application...")
    run("ditto", source, target)

    library = target / FONT_PATH
    backup = library.with_name("QtGui.fontfix-original")

    try:
        shutil.copy2(library, backup)

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            x86 = td / "QtGui-x86_64"
            i386 = td / "QtGui-i386"
            universal = td / "QtGui-patched"

            extract(library, "x86_64", x86)
            extract(library, "i386", i386)

            data = bytearray(x86.read_bytes())

            if patch_status(data) != "original":
                raise RuntimeError(
                    "Unexpected x86_64 instruction bytes"
                )

            data[OFFSET:OFFSET + 6] = PATCHED
            x86.write_bytes(data)

            run(
                "lipo", "-create",
                i386, x86,
                "-output", universal
            )

            # Verify both slices before installation.
            verify_x86 = td / "verify-x86"
            verify_i386 = td / "verify-i386"

            extract(universal, "x86_64", verify_x86)
            extract(universal, "i386", verify_i386)

            if patch_status(verify_x86.read_bytes()) != "patched":
                raise RuntimeError("Patch verification failed")

            if sha256(i386) != sha256(verify_i386):
                raise RuntimeError("i386 slice changed unexpectedly")

            # Stage replacement on the destination filesystem.
            staged = library.with_name("QtGui.fontfix-staged")
            shutil.copy2(universal, staged)
            shutil.copymode(backup, staged)
            os.replace(staged, library)

        if check(target) != "patched":
            raise RuntimeError("Installed patch verification failed")

    except Exception:
        if backup.exists():
            shutil.copy2(backup, library)
        raise

    print("\nSUCCESS! Font fix installed.")
    print(f"Test application: {target}")
    print(f"Original application untouched: {source}")
    print(f"Backup: {backup}")
    print("\nLaunch normally, without LLDB:")
    print(f"open {target}")


def restore(target):
    target = target.absolute()
    library = target / FONT_PATH
    backup = library.with_name("QtGui.fontfix-original")

    if not backup.is_file() or not library.is_file():
        raise RuntimeError(
            "Test QtGui or its original backup is missing"
        )

    shutil.copy2(backup, library)
    print("Original QtGui restored.")
    check(target)


def main():
    parser = argparse.ArgumentParser(
        description="Sibelius 8.5 Qt4 macOS font fix"
    )

    parser.add_argument(
        "action",
        choices=["check", "apply", "restore"]
    )
    parser.add_argument(
        "--source", type=Path,
        default=DEFAULT_SOURCE
    )
    parser.add_argument(
        "--target", type=Path,
        default=DEFAULT_TARGET
    )

    args = parser.parse_args()

    try:
        if args.action == "check":
            check(args.source)
        elif args.action == "apply":
            apply(args.source, args.target)
        elif args.action == "restore":
            restore(args.target)
    except (RuntimeError, OSError, subprocess.CalledProcessError) as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

