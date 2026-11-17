# Sibelius 8.5 Font Fix for Modern macOS

**An unofficial compatibility patch that fixes missing music fonts and broken music notation in Avid Sibelius 8.5 on modern macOS.**

Successfully tested on Apple Silicon Macs running macOS Golden Gate 27.

## The problem

When running Sibelius 8.5 on newer versions of macOS, users may experience:

- **Missing Fonts** warnings even though the required fonts are installed.
- An empty font selection menu in **Preferences → Music Fonts → Choose Font**.
- Missing or incorrectly rendered musical notation.
- Problems with music fonts such as Opus, Inkpen2, Helsinki and Reprise.

Reinstalling Sibelius, reinstalling fonts, resetting font caches or changing Sibelius preferences may not resolve the issue.

## Root cause

Sibelius 8.5 includes an older version of the Qt 4 framework.

During investigation, we discovered that Qt incorrectly reported the macOS version through:

`QSysInfo::MacintoshVersion = 4`

However, the bundled QtGui framework contains a version check inside `initializeDb()`:

```asm
cmpl $0x7, (%rax)
jl   skip_initialization
```

Because the detected version is less than 7, Qt skips the CoreText font database initialization.

As a result, `QFontDatabase::families()` returns an empty list, despite macOS CoreText correctly recognizing the installed fonts.

## The fix

This patch replaces a single conditional jump with six NOP instructions in the **x86_64 architecture** of the bundled QtGui framework.

| Property | Value |
|---|---|
| Framework | QtGui.framework |
| Architecture | x86_64 |
| Function | `initializeDb()` |
| Offset in extracted x86_64 slice | `0x27DFEC` |
| Original bytes | `0F 8C F8 06 00 00` |
| Patched bytes | `90 90 90 90 90 90` |

The patch removes the problematic version check, allowing Qt to initialize its CoreText font database.

**Important:** The script checks the original bytes before modifying anything. If the installed QtGui does not match the expected binary, the patch is refused.

It does not modify macOS system frameworks or require disabling System Integrity Protection (SIP).

## Requirements

- macOS with Python 3 available.
- An existing installation of Sibelius 8.5.
- The original bundled QtGui framework matching the expected bytes.
- Administrator privileges to create a test application in `/Applications`.

No additional Python packages, Homebrew or LLDB are required.

## Installation

### 1. Download the patcher

Download [`sibelius-font-fix.py`](sibelius-font-fix.py) from this repository.

Open Terminal and navigate to the directory containing the file.

### 2. Check compatibility

```bash
python3 sibelius-font-fix.py check
```

Expected result:

```text
Status: original
Offset: 0x27DFEC
```

If the script reports unknown bytes, **do not attempt to force the patch**. Your QtGui version may be different.

### 3. Apply the patch

Quit Sibelius completely, then run:

```bash
sudo python3 sibelius-font-fix.py apply
```

The script:

1. Verifies the original QtGui binary.
2. Creates a separate application at `/Applications/Sibelius-FontFix-Test.app`.
3. Backs up the original QtGui inside the test application.
4. Extracts the i386 and x86_64 slices.
5. Patches only the x86_64 slice.
6. Reassembles the universal binary.
7. Verifies the result.

**The original `/Applications/Sibelius.app` is not modified.**

### 4. Launch the patched Sibelius

```bash
open /Applications/Sibelius-FontFix-Test.app
```

Check **Preferences → Music Fonts → Choose Font**.

The previously empty font selection menu should now contain the available system fonts.

Open a score and verify that musical notation displays correctly.

## Restoring the original library

To restore the original QtGui within the test application:

```bash
sudo python3 sibelius-font-fix.py restore
```

Alternatively, remove the test application and recreate it using the original Sibelius installation.

The original application remains untouched by the patcher.

## Tested configurations

| Hardware | macOS | Result |
|---|---|---|
| Apple M5 | Golden Gate 27 | Font list and music notation restored |
| Apple M6 (Mac mini) | Golden Gate 27.0 | Font list and music notation restored |

Both computers successfully ran the automated patcher and launched Sibelius with working font selection and visually correct musical notation.

Testing on additional macOS versions and Sibelius builds is welcome.

## Investigation

The issue was traced using LLDB, CoreText diagnostics, Qt 4 symbol inspection and x86_64 disassembly.

Key findings:

- Original Sibelius music fonts were installed correctly.
- CoreText could enumerate the fonts, including under Rosetta 2.
- Qt 4 returned an empty list of font families.
- An outdated macOS version check prevented Qt from initializing the CoreText font database.
- Replacing the conditional branch restored the font list and notation rendering.

Only six bytes needed to change.

## Limitations and disclaimer

This is an **unofficial, experimental compatibility patch**.

It is not affiliated with, supported by, or endorsed by Avid Technology, Apple or the Qt Project.

The patch has been verified only on the configurations listed above. Other Sibelius builds may have different binary layouts. Modified application binaries may also interact differently with macOS security and code-signing checks.

Always keep a backup of your original application and important music projects.

The repository distributes only the patching script, **not copyrighted Sibelius or Qt binaries**.

## License

The patching script is distributed under the [MIT License](LICENSE). This does not grant rights to redistribute Sibelius or its bundled proprietary components.

---

**Six bytes. One old Qt compatibility check. Music notation restored.** 🎼
