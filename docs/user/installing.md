# Installing CADD Calculator

From the first release, `v0.1.0a1`, downloads are on the project's
[GitHub releases page](https://github.com/inmymoonsuit/CADD-Calculator/releases). They come
from this repository's own build ([code signing policy](code-signing.md)). The first
release is an early pre-release for testing, with files for Windows and Linux; a macOS
download comes later.

**The downloads aren't signed yet.** The project is starting without signing and adding it
in steps ([ADR-0022](../dev/decisions/0022-distribution-and-signing.md)): Apple's
notarization needs a yearly paid membership, and for Windows the free route, SignPath
Foundation's program for open-source projects, asks for a project that's already released.
Until then, Windows and macOS warn you the first time you open the app, because they
can't tell who made it. The steps below get you past that warning safely. Check the
download first ([below](#checking-a-download)).

## Windows

1. Download `CADDCalculator-<version>-generic-windows-x64-setup.exe` and open it. It
   installs for your user account only, so it needs no administrator rights.
2. Windows shows **Windows protected your PC**. Choose **More info**, then **Run anyway**.
   Microsoft describes this prompt in
   [SmartScreen reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)
   (checked 2026-10-25).
3. Follow the installer. CADD Calculator is then in the Start menu.

If **Smart App Control** is on (Windows 11), it may block the app with no way to continue,
since it blocks unsigned programs and has no per-app exception. Signed releases will fix
that.

A zip of the same app (`…-windows-x64.zip`) is there too: unzip it anywhere and run
`CADDCalculator.exe`. Windows warns about it the same way.

## macOS

There's no macOS download yet; the first release is Windows and Linux only. When it comes,
it will be for Apple silicon (M1 and later), and these steps apply.

1. Download `CADDCalculator-<version>-generic-macos-arm64.dmg` and open it.
2. Drag **CADD Calculator** onto the **Applications** folder in the same window.
3. Open the app from Applications. macOS says it can't check the app for malicious
   software, and doesn't open it. That's expected for an app that isn't notarized yet.
4. Open **System Settings**, click **Privacy & Security**, scroll down, and click
   **Open Anyway**. When the warning appears again, click **Open**. Apple describes these
   steps in [Safely open apps on your Mac](https://support.apple.com/en-us/102445)
   (published 2026-05-27, checked 2026-10-25). Since macOS Sequoia, Control-clicking the
   app no longer gets past this.

You do this once; after that the app opens normally.

## Linux

* **AppImage:** download `…-linux-x64.AppImage`, make it executable
  (`chmod +x CADDCalculator-*.AppImage`), and run it. It needs no installation and no extra
  packages on Ubuntu 22.04's standard desktop: every release is started on X11 with only
  the libraries that desktop installs. It's built for 64-bit PCs with that release's
  system libraries or newer, so it should run on later Ubuntu releases and similar
  distributions too, though only Ubuntu 22.04 is tested. In a Wayland session it uses
  Qt's Wayland support, whose libraries are checked but which isn't started in testing
  yet.
* **Flathub:** a Flathub listing is planned. It will be built from source by Flathub.

## As a Python package

The calculators and the command line will also be on PyPI as `cadd-calculator`, once
publishing there is switched on: then `pipx install cadd-calculator`, or
`pipx install "cadd-calculator[gui]"` for the window too. This needs Python 3.12 or later.

## Checking a download

* **The checksum:** each release has a `SHA256SUMS` file. Compare your download's hash with
  it: `certutil -hashfile <file> SHA256` on Windows, or `shasum -a 256 <file>` on macOS and
  Linux.
* **Where it was built:** with the [GitHub CLI](https://cli.github.com/), run
  `gh attestation verify <file> --repo inmymoonsuit/CADD-Calculator`. It confirms this
  repository's release workflow built the file.

## Removing the app

* **Windows:** Settings > Apps > Installed apps, then CADD Calculator > Uninstall.
* **macOS:** move the app to the Trash.
* **Linux:** delete the AppImage.
