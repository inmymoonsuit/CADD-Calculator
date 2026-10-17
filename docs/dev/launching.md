# Launching the work-in-progress app

To try the app as it is in your checkout, uncommitted changes included, use the launcher:

```bat
scripts\launch_app.cmd
```

```bash
scripts/launch_app.sh        # macOS, Linux
```

On Windows you can also double-click `scripts\launch_app.cmd`. A console window opens
next to the app and shows any errors and warnings. If the app exits with an error, the
window stays open until you press a key.

## Options

| Option | Effect |
|---|---|
| `--branding FOLDER` | Run with the branding pack in `FOLDER` (any path). The pack is checked first, and an invalid pack stops the launch with the reason. |
| anything else | Passed to the app, e.g. `--smoke-test` to open, report, and quit, or Qt options such as `-style fusion` |

Examples:

```bat
scripts\launch_app.cmd --branding "D:\packs\my-edition"
scripts\launch_app.cmd --smoke-test=builds\launch-check
```

## What it does

1. Checks that `uv` is installed.
2. Runs `uv run --extra gui`, which brings the project's `.venv` up to date with
   `uv.lock` (installing PySide6 the first time) before anything starts. The package is
   installed in editable mode, so the app runs your current source.
3. Runs `scripts/launch_app.py`, which:
   * applies `--branding`, or clears any inherited `CADDCALC_BRANDING`, so the app is
     unbranded unless you ask
   * prints the version and the source folder
   * turns on `faulthandler`, so a hard crash inside Qt still prints a traceback
   * shows the project's own warnings
   * starts `caddcalc.gui.app.main` with the remaining arguments

## Isolation

No container or VM is needed to run the app from source. uv's `.venv` is the sandbox:
* It is a private Python environment, pinned by `uv.lock`.
* Nothing is installed into the system Python.
* Deleting `.venv` resets it, and the next launch rebuilds it.

Docker suits server software. A desktop Qt app in a Linux container needs display
forwarding to show its window, and it wouldn't test the Windows or macOS app anyway.

## Testing what users install

The launcher runs the source. To check the compiled app instead, build it and let the
build script start it (see [packaging.md](packaging.md)):

```bash
uv run python packaging/build.py --smoke-test
```

Testing an installer on a clean machine, with no Python or uv, needs a virtual machine.
Windows Home has neither Windows Sandbox nor Hyper-V, so use VirtualBox or VMware
Workstation. That belongs to the installer work on the roadmap.
