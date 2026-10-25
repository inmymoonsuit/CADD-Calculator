# Packaging the desktop app

How to build the standalone app, and how branded editions work. The decisions behind it
are [ADR-0009](decisions/0009-packaging-and-distribution.md) (build tool, spike results),
[ADR-0011](decisions/0011-branding-packs.md) (branding packs), and
[ADR-0008](decisions/0008-licensing-and-third-party-assets.md) item 4 (branding policy).

## Quick start

```bash
uv sync --extra gui --group build
uv run python packaging/build.py --smoke-test --archive
```

The output goes to `builds/generic/` (git-ignored):

| Path | What it is |
|---|---|
| `CADDCalculator-<version>-generic-windows-x64/` | the app folder. Run `CADDCalculator.exe`. |
| `…-windows-x64.zip` | the same folder zipped, for handing out (`--archive`) |
| `…-windows-x64.smoke-test/` | `smoke-test.json` and a `window.png` screenshot (`--smoke-test`) |
| `…-windows-x64.build.json` | size, build time, tool versions, startup times |
| `work/` | pyside6-deploy's spec, the log, and Nuitka's compilation report |

The first build downloads Nuitka's C compiler (MinGW-w64 gcc, about 270 MB) and Dependency
Walker into Nuitka's cache. Later builds take 20 to 45 seconds because ccache keeps the
compiled C.

## The wheel and the sdist

`uv build` makes both. The sdist carries the catalogs' sources, each language's `.po`
and the `.pot`, for translators. The wheel carries only the compiled `.mo`, which its
build hook (`hatch_build.py`) compiles from them. Babel (BSD-3-Clause) is a build
requirement for that, and nothing from it ships. pip and uv fetch it into the build's
isolated environment automatically, except offline, or for a distribution packager
building without isolation: there it must be installed first (often as
`python3-babel`). CI builds both and checks the wheel's catalogs: each language's `.mo`,
and nothing else (`uv run python scripts/i18n.py check-wheel dist/*.whl`). A `v*` tag
publishes both to PyPI ([PyPI](#pypi)).

## Editions

| Command | Edition | Branding |
|---|---|---|
| `build.py` | `generic`, the public build | none: the built-in name and icon |
| `build.py --branding NAME` | the pack's `edition` | the pack in `branding/NAME/` |
| `build.py --branding DIR` | the pack's `edition` | the pack in `DIR`, e.g. a private repository |

Branded editions are built outside this repository's CI and never attached to public
releases (ADR-0008 item 4). `branding/` is git-ignored, so local packs aren't committed by accident.
Whoever builds a branded edition is responsible for permission to use the marks and art
in its pack.

The script refuses every branded build when the `CI` or `GITHUB_ACTIONS` environment
variable is set, so the public CI can't make one even by mistake.

### Testing the branded path without a real pack

```bash
uv run python packaging/make_placeholder_pack.py builds/placeholder-pack
uv run python packaging/build.py --branding builds/placeholder-pack --smoke-test
```

The placeholder pack is a magenta test pattern that says "not for distribution", with
the edition `placeholder`, and generated welcome art and a vertical logo. To try any pack from a source checkout without building, set
`CADDCALC_BRANDING`:

```bash
CADDCALC_BRANDING=builds/placeholder-pack uv run caddcalc-gui
```

## Branding packs

A pack is a folder with a `branding.toml`:

```toml
schema = 1                                    # pack format version (optional)
edition = "example"                           # slug for folder names: a-z, 0-9, -
icon = "icon.png"                             # optional; .png (256 px or more) or .ico
about = "about.html"                          # optional; .html fragment or .txt

[welcome]                                     # optional welcome screen parts (ADR-0015)
art = "welcome-art.png"                       # 16:9, supplied at 1920 x 1080; .png or .jpg
art_focus = [0.35, 0.5]                       # the point kept in view when cropping
logo = "logo-vertical.svg"                    # the logo, in its box; .svg or .png

[welcome.style.logo]                          # optional overrides (ADR-0016, S5)
fill_role = "welcome_paper"                   # also margin_left, margin_top,
                                              #   margin_bottom, padding
[welcome.style.panes]
fill_opacity_min = 0.25                       # also fill_roles
```

* Every edition is called "CADD Calculator": in its window title, on its welcome
  screen, and in About. An edition is told apart by its icon, art, logo, and About text
  (ADR-0016, S4). A pack that still names the old `name` key is refused, with a message
  saying to delete it.
* Paths are relative to the pack folder and must stay inside it.
* `icon` sets the window icon, and also the `.exe` icon. A PNG is converted to a
  multi-size `.ico` (Windows) or `.icns` (macOS) at build time.
* `about` replaces the one-line description in Help > About. The version, the
  disclaimer, and the link to the source code are always shown.
* `[welcome]` supplies the welcome screen's parts: 16:9 art, supplied at 1920 × 1080,
  its focal point, and a vertical logo. The sizes, safe areas, budgets, and the art's
  notice are in the [art specification](design/welcome-screen.md), and
  `packaging/make_welcome_template.py` writes a guide for the art. A pack that still
  names the old `splash` key is refused, with a message naming `[welcome]`.
* `[welcome.style.logo]` and `[welcome.style.panes]` may override a short whitelist of
  the welcome screen's design tokens: the logo box's fill role, margins, and padding,
  and the panes' fill roles and least opacity. Anything else is refused. The art
  specification lists them and the checks.
* The build copies only `branding.toml`, the files it names, and any file at the top of
  the pack whose name contains `NOTICE`, `LICENSE`, `LICENCE`, or `COPYING` (such as
  `ART-NOTICE.md` for the pack's art). Source art, drafts, and planning notes in the pack
  folder stay behind.
* The packaged app finds the pack in a `branding/` folder next to its executable.
  Every edition shares one application name, so it shares its settings too.
* A broken pack at run time gives a warning and the generic branding. The build script
  checks the pack first and stops with the reason, so a broken pack can't ship.

The loader is `caddcalc.gui.branding`. It doesn't import Qt.

## Notices

The build copies `LICENSE.md` and `THIRD_PARTY_NOTICES.md` into the app folder, and the
runtime's license texts into its `licenses/` folder. Third-party assets inside the
package ride along with the package data: the Tabler icons and their `LICENSE.txt`, and
the welcome screen's display face, VT323, with its `OFL.txt` (`gui/assets/fonts/vt323/`,
vendored by `packaging/fetch_fonts.py`; ADR-0016 §2).

The runtime's texts (Qt's LGPL-3.0 and GPL-3.0, CPython's license and the software it
includes, OpenSSL, libffi, zlib, bzip2, xz, Nuitka, the Microsoft C++ runtime, and Qt's
own third-party notices) are vendored in `packaging/notices/` by
`packaging/fetch_notices.py`, from each project's repository at a pinned tag, with each
file's SHA-256 in its `manifest.toml`:

```bash
uv run python packaging/fetch_notices.py --check    # offline: the files match
uv run python packaging/fetch_notices.py            # re-download; refuse any change
uv run python packaging/fetch_notices.py --update   # after moving a pin: re-hash
```

Qt's third-party notices (`Qt-third-party.txt`) are collected from every
`qt_attribution.json` in qtbase at its tag, for the modules a build ships: Core, Gui
with its platform plugins, DBus, and Svg. When PySide6 is upgraded, move `QT_TAG` with
it, and `CPYTHON_TAG` with the build's Python, then run `--update` and review the diff.
The build stops before compiling if a vendored text differs from the manifest, and
after, if a notice is missing from the app folder (`missing_notices`).

## What the build leaves out

Beyond Nuitka's PySide6 defaults, the build leaves out code the app never uses. That
makes the folder smaller and leaves fewer notices to carry. On Windows the folder went
from 87.8 MB to 83.0 MB, and its zip from 32.3 MB to 30.3 MB, with 0.4 MB of license
texts added (2026-10-25; `.build.json`'s `size_mb` and `archive_mb`):

| Left out | Why | How |
|---|---|---|
| QtNetwork (`QtNetwork` module, `Qt6Network` library) | nothing imports it; the app makes no network calls (ADR-0009) | `--nofollow-import-to=PySide6.QtNetwork`, and `--noinclude-dlls=*Qt6Network*`, since Nuitka still follows a left-out plugin's dependencies |
| Qt's TLS backends (`tls/`: OpenSSL, Schannel, cert-only) | they serve QtNetwork, and pulled it in | `--noinclude-qt-plugins=tls` |
| The VNC platform plugin (`platforms/libqvnc.so`, Linux) | it serves the window over a network, and links QtNetwork; the app uses xcb or Wayland | `--noinclude-dlls=*platforms*qvnc*` |
| Image plugins for PDF, TIFF, WebP, TGA, WBMP, and ICNS | the app reads PNG and JPEG art, SVG and ICO icons; `.icns` is only written at build time | `--noinclude-dlls=*imageformats*<name>*` |

OpenSSL's libcrypto stays, because Python's `hashlib` uses it. The GIF, ICO, JPEG, and
SVG image plugins stay. The build fails if a left-out file turns up in the app folder
(`trimmed_files`), and the smoke test checks the app still starts and draws its icons
and art.

## What the build does

1. Copies `packaging/launcher.py` into `work/` as `CADDCalculator.py`. pyside6-deploy
   compiles a script, not an entry point. The launcher calls `caddcalc.gui.app:main`.
2. Compiles the catalogs, each language's `.po` to its `.mo`, into the source tree's
   `caddcalc/locale`, where they're package data (`scripts/i18n.py compile`).
3. Writes `work/pysidedeploy.spec`: the Qt modules (`Core,Gui,Widgets`), the icon, and
   the Nuitka options. Those include Windows version info, `--include-package-data=caddcalc`
   for the generic icon and the catalogs (the `.mo`, not their `.po` and `.pot`
   sources), Qt's `qtbase_*.qm` catalogs into the folder where the build's PySide6 keeps
   them, `PySide6/translations/` on Windows and `PySide6/Qt/translations/` on Linux and
   macOS (`qt_catalogs_dir()`; no other Qt translation), and, for a branded build,
   `--include-data-dir=<staged pack>=branding`.
4. Runs `pyside6-deploy -c pysidedeploy.spec --no-install`, which runs Nuitka in standalone
   mode. Nuitka must already be installed by uv (the `build` dependency group).
5. Renames the `.dist` folder, copies `LICENSE.md` into it, and checks that a generic build
   has no `branding/` folder and a branded build has one, and that every reference table
   in `caddcalc.calculators.REFERENCE_TABLES`, such as `sheet_metal/data/gauges.toml`, is
   bundled (`--include-package-data=caddcalc` carries them), as is every file the display
   face's `manifest.toml` lists: the font and its license, and every catalog: each
   language's `.mo`, and every `qtbase_*.qm` (ADR-0009's checklist). It fails if there's
   no `.po` to check against, or if a `.po` or `.pot` was bundled.
6. With `--smoke-test`, starts the app with `--smoke-test=DIR` a few times (`--runs`). Each
   run opens the welcome screen and the window, loads every reference table, writes the
   report, and exits. The script checks the reported name, edition, icon, that the
   welcome screen showed with the pack's art and logo (or the generic ones), that it
   loaded the display face (the report's `display_font` is `VT323`, or `fallback` if it
   couldn't), the number of reference tables loaded, the catalogs the app finds
   (`catalogs`), that Qt loads its own catalog from the build (`qt_catalog`), and that
   the app knew it was packaged.

`--mode onefile` builds a single self-extracting executable instead. It works, branded too,
but starts about 0.9 s slower and unpacks to a temp folder on every start, which
antivirus software tends to dislike (ADR-0009).

## Building against a modified PySide6

The LGPL-3.0 lets a user rebuild the app against a modified Qt or PySide6
(THIRD_PARTY_NOTICES.md, "Replacing or rebuilding Qt and PySide6"). Install the modified
wheels into the project's `.venv`, then build **without syncing**:

```bash
uv sync --extra gui --group build
uv pip install <your modified PySide6 wheels>
uv run --no-sync python packaging/build.py
```

A plain `uv run` syncs `.venv` back to `uv.lock` first, and so would build with the stock
PySide6: installing babel 2.14.0 over the locked 2.18.0, `uv run --no-sync` still sees
2.14.0, while `uv run` puts 2.18.0 back (checked 2026-10-25). `UV_NO_SYNC=1` does the
same as `--no-sync`.

The build report (`.build.json`) records which PySide6 the build compiled against, in
`pyside6_source`: its version, the version `uv.lock` pins, where it's installed, its
installer, and any `direct_url.json` (a wheel installed from a file or URL).
`matches_lock` is false for anything but the locked release from the index.

## Troubleshooting

* **Use the pinned Nuitka.** `pyproject.toml` pins the version that pyside6-deploy's
  `default.spec` names (4.1.1 for PySide6 6.12). Nuitka 4.3 builds an app that crashes
  when it opens (engineering log, 2026-10-17). When PySide6 is upgraded, read the new
  `default.spec` and move the pin with it.
* **`structuredquerycondition.h: No such file or directory`** (or another missing MinGW
  header) means the compiler's include paths are longer than Windows' 260-character limit.
  This happened when the build ran inside the Claude desktop app, whose sandbox moves
  `%LOCALAPPDATA%` to a much longer path. Point Nuitka's cache at a short folder:
  `NUITKA_CACHE_DIR=C:\Users\<you>\.cache\nuitka`.
* **"Unable to find dumpbin"** from pyside6-deploy is harmless. It needs Visual Studio's
  `dumpbin` to find Qt module dependencies, so the spec lists the modules itself.
* **Antivirus.** No detections happened during the spike, but Nuitka builds are sometimes
  flagged. The build output stays under `builds/` in the project folder. If a file is
  quarantined, note its exact name before changing any exclusions.
* **Slow start on machines with many fonts.** See KI-015.

## The Windows installer

`build.py --installer` wraps the standalone Windows folder in an Inno Setup 6 installer,
`…-windows-x64-setup.exe`, from `packaging/windows/CADDCalculator.iss` (ADR-0022, slice d3).
It needs Inno Setup 6's `ISCC.exe` ([jrsoftware.org](https://jrsoftware.org/isinfo.php));
GitHub's windows-latest runner has it.

* It installs for the current user by default, into `%LOCALAPPDATA%\Programs\CADD
  Calculator`, with no admin rights. The installer offers a per-machine install instead,
  which `/ALLUSERS` also chooses.
* It adds a Start-menu shortcut and an uninstaller, and shows the license.
* The version comes from the build (`caddcalc.__version__`). The `AppId` in the script
  never changes, since it's how Windows knows a new version upgrades the old one. A test
  pins it.

`packaging/windows/test_installer.py <setup.exe>` installs silently into a temporary
folder, starts the installed app with `--smoke-test`, uninstalls silently, and checks the
folder and the shortcut are gone, checking every step's exit code. The release workflow
runs it on every Windows dry run. It installs software, so run it on your own machine only
on purpose.

## Signing

The release workflow's `sign-windows` job signs the installer on a `v*` tag, through
SignPath Foundation or Microsoft Artifact Signing (ADR-0022). The maintainer hasn't chosen
yet, so it's **switched off**. It runs only on tags, and until its settings exist it leaves
a "Signing is switched off" notice and succeeds, so a missing setting never fails a release.
When it signs, the draft release gets the signed installer in place of the unsigned one.

### First, for either provider: the approval gate and the tags

Signing must never happen without the maintainer approving it by hand
([the code signing policy](../user/code-signing.md)). Set these up before switching
signing on:

1. **The `release-signing` environment.** Settings > Environments > New environment,
   named `release-signing`. Under "Deployment protection rules", add yourself as a
   **required reviewer**, and turn on "Prevent self-review" only if another maintainer can
   approve. Under "Deployment branches and tags", choose "Selected branches and tags" and
   add the tag rule `v*`. The `sign-windows` job runs in this environment, so each signing
   waits for your approval in the run's page, and the job can't run from anywhere else.
2. **A tag ruleset.** Settings > Rules > Rulesets > New tag ruleset, targeting tags that
   match `v*`, enforced, restricting creation, update, and deletion, with yourself (the
   repository admin role) as the only bypass. Then only you can create the release tags
   that trigger signing.

### Then choose a provider

Set the repository **variable** `SIGNING_PROVIDER` (Settings > Secrets and variables >
Actions > Variables) to one provider, and set that provider's settings:

**SignPath Foundation** (`SIGNING_PROVIDER` = `signpath`):

1. Apply at [signpath.org](https://signpath.org/apply). SignPath signs a project that's
   already released, in the form to be signed, and asks for some reputation
   ([research](research/distribution.md), S1).
2. Follow [the code signing policy](../user/code-signing.md), and turn on MFA for every
   team member, on GitHub and on SignPath.
3. In SignPath, add GitHub as a trusted build system for this repository, and make a
   project and a signing policy with manual approval.
4. Set the variables `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`, and
   `SIGNPATH_POLICY_SLUG`, and the **secret** `SIGNPATH_API_TOKEN` (a CI user's token).
5. Each tagged release then waits for you twice: to approve the `release-signing`
   environment in GitHub, and to approve its signing request in SignPath. SignPath's
   manual approval is its own gate, required by its conditions.

**Microsoft Artifact Signing** (`SIGNING_PROVIDER` = `artifact-signing`):

1. On a paid Azure subscription, create an Artifact Signing account, finish identity
   validation, and create a public-trust certificate profile. An individual must be in the
   US or Canada.
2. Register an app in Microsoft Entra ID, give it the "Artifact Signing Certificate Profile
   Signer" role on the profile, and add a federated credential for the `release-signing`
   environment: entity type "Environment", subject
   `repo:inmymoonsuit/CADD-Calculator:environment:release-signing`. Azure then accepts a
   login only from a job in that environment, which runs only after you approve it. No
   client secret is needed: the job signs in through OIDC.
3. Set the variables `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `ARTIFACT_SIGNING_ENDPOINT`
   (the account's regional endpoint, such as `https://eus.codesigning.azure.net/`),
   `ARTIFACT_SIGNING_ACCOUNT`, and `ARTIFACT_SIGNING_PROFILE`.

No key or certificate file is ever stored in the repository or its secrets: both services
keep the key in their own hardware (ADR-0022's amendment, W5).

## Checksums and attestations

The release workflow's `release-files` job gathers every file a release offers: the Windows
zip and installer (the signed one, when signing ran), the macOS `.dmg` and zip, the Linux
AppImage and archive, and the wheel and the sdist. It fails if any kind is missing. It
writes `SHA256SUMS` over them, and checks it. On a `v*` tag it then makes a GitHub
artifact attestation for each file with `actions/attest`, from that `SHA256SUMS`
(ADR-0022, slice d6). The draft release gets every file and `SHA256SUMS`.

The job runs on dry runs too, so `SHA256SUMS` is tested on every push; only a tag
attests. It alone has `id-token: write` and `attestations: write`. Users check a download
with either ([installing](../user/installing.md#checking-a-download)):

```bash
sha256sum --check --ignore-missing SHA256SUMS
```

```bash
gh attestation verify CADDCalculator-0.3.0-generic-windows-x64-setup.exe --repo inmymoonsuit/CADD-Calculator
```

The build reports (`*.build.json`) stay in the workflow's artifacts, not the release.

## PyPI

On a `v*` tag the workflow publishes the wheel and the sdist with PyPI's Trusted
Publishing: first to TestPyPI (the `testpypi` job), then, once that succeeds, to PyPI (the
`pypi` job). Both use `pypa/gh-action-pypi-publish`, which also makes PEP 740
attestations for both files. No API token is stored anywhere: PyPI trusts this workflow's
OIDC identity, and each job has `id-token: write` and nothing else. The `python-dist` job
builds both files and checks the wheel's catalogs on every run; only a tag publishes.

Nothing is published until the maintainer does this once, on each of
[PyPI](https://pypi.org/manage/account/publishing/) and
[TestPyPI](https://test.pypi.org/manage/account/publishing/) (an account on each, with
two-factor authentication on):

1. **A pending publisher.** Account > Publishing > "Add a new pending publisher", GitHub
   tab: PyPI project name `cadd-calculator`, owner `inmymoonsuit`, repository
   `CADD-Calculator`, workflow `release.yml`, environment `pypi` (on TestPyPI,
   `testpypi`). A pending publisher doesn't reserve the name: until the first upload,
   anyone can take it.
2. **The two environments**, in the repository's Settings > Environments: `testpypi` and
   `pypi`, each with yourself as a **required reviewer** and the deployment tag rule `v*`,
   as for `release-signing` ([Signing](#signing)). Each upload then waits for your approval
   in the run's page.

Without them, a tag's `testpypi` job fails at the upload and `pypi` never starts; the
draft release is made either way. A version can be uploaded once only, to each index, so
a tag that's published can't be reused.

## winget

`packaging/windows/winget/` holds the winget manifest templates (schema 1.10.0) for
`inmymoonsuit.CADDCalculator`. `packaging/windows/winget.py render` fills in a release's
version, installer URL, and SHA-256, and `validate` checks the result against winget's
schema, which is downloaded from winget-cli at a pinned tag and checked against its SHA-256.
Every Windows dry run renders and validates them, with the build's installer.

Submitting to [winget-pkgs](https://github.com/microsoft/winget-pkgs) is the maintainer's
job, after the first **signed** release, since an unsigned installer trips SmartScreen in
winget's validation:

1. Render the manifests for the published release, with the release asset's URL and the
   SHA-256 from its `SHA256SUMS`.
2. Validate them locally with `winget validate --manifest <folder>`, and test
   `winget install --manifest <folder>` in Windows Sandbox.
3. Fork winget-pkgs, add the folder as `manifests/i/inmymoonsuit/CADDCalculator/<version>/`,
   and open a pull request. Its bots check the manifest and the installer.

## The macOS .dmg

`packaging/macos/make_dmg.py <app> --smoke-test` puts the `.app` that `build.py` makes into
a compressed, read-only `.dmg` with `hdiutil`, with a link to `/Applications` beside it, so
users drag one onto the other (ADR-0022, slice d5). `--smoke-test` mounts the image
read-only, checks the link, starts the app from the mounted image with `--smoke-test`, and
detaches.

The CI build is for Apple silicon only: `macos-latest` is an arm64 runner. An Intel or
universal build would need its own runner or a universal Python.

The app isn't signed or notarized yet, so macOS blocks it the first time it's opened.
`docs/user/installing.md` explains why, and gives Apple's "Open Anyway" steps.

### macOS notarization (a stub)

The release workflow's `notarize-macos` job is a placeholder for Developer ID signing and
notarization, once the maintainer joins the Apple Developer Program (ADR-0022, "Later"). It
runs only on tags, in the `release-signing` environment. Until the variable
`MACOS_NOTARIZE` is `true` and its secrets are set, it leaves a "switched off" notice and
succeeds. Switched on, it fails on purpose, because its steps aren't written yet. Before
switching it on, write and test them:

1. Import the Developer ID Application certificate (the secrets
   `APPLE_DEVELOPER_ID_P12`, base64, and `APPLE_DEVELOPER_ID_P12_PASSWORD`) into a
   temporary keychain on a macOS runner.
2. Sign the `.app` with `codesign --deep --force --options runtime --timestamp`.
3. Submit it with `xcrun notarytool submit --wait`, using `APPLE_ID`, `APPLE_TEAM_ID`, and
   `APPLE_APP_SPECIFIC_PASSWORD`, then `xcrun stapler staple` the app.
4. Rebuild the `.dmg` with `make_dmg.py` from the stapled app, and sign and staple the
   `.dmg` too.

After that, Homebrew can take a cask, since it accepts only apps that pass Gatekeeper.

## The Linux AppImage

`packaging/linux/make_appimage.py <app folder> --smoke-test` wraps the standalone Linux
build in an AppImage, `…-linux-x64.AppImage` (ADR-0022, slice d4):

* The AppDir holds the app folder in `usr/lib/caddcalc`, a `caddcalc-gui` launcher, the
  `.desktop` file, the 256 px icon, and the AppStream metainfo
  (`packaging/linux/io.github.inmymoonsuit.CADDCalculator.{desktop,metainfo.xml}`).
* appimagetool 1.9.1 and the AppImage runtime (release 20251108) are pinned tagged
  releases, checked against their published SHA-256s. They're downloaded once into
  `builds/tools/`, and run extracted, so no FUSE is needed.
* `--smoke-test` starts the AppImage with `--appimage-extract-and-run` and checks the app's
  report.

Build it on the oldest Linux you support (CI uses ubuntu-22.04), since an AppImage runs
only on systems with at least its build's glibc. CI also checks the `.desktop` file with
`desktop-file-validate`, and the metainfo with `appstreamcli validate`.

## Flathub

`packaging/flatpak/io.github.inmymoonsuit.CADDCalculator.yml` builds the app **from
source** on the KDE runtime, with PySide6 from `io.qt.PySide.BaseApp` (runtime and base at
the same version, 6.11). It pip-installs the app offline. Its only build-time downloads are
the wheel-build tools in `python3-build-deps.json` (hatchling and what it uses, and Babel),
pure-Python wheels pinned with their SHA-256s, which `packaging/flatpak/make_build_deps.py`
writes. Their module's cleanup drops them from the finished app. The manifest asks for no
network access.

The release workflow's `flatpak` job builds it in Flathub's KDE container and starts it
inside the sandbox with `--smoke-test`.

Submitting to Flathub is the maintainer's job, after the first release:

1. Fork [flathub/flathub](https://github.com/flathub/flathub) and branch from
   `new-pr`, as Flathub's [submission guide](https://docs.flathub.org/docs/for-app-authors/submission)
   says.
2. Copy the manifest and `python3-build-deps.json` in. Replace the `dir` source with a
   `git` source: this repository's URL, the release's `tag`, and its `commit`.
3. Add screenshots to the metainfo (Flathub requires them), with URLs to images at the
   release tag, and run `flatpak run --command=flatpak-builder-lint org.flatpak.Builder
   manifest <manifest>`.
4. Open the pull request against `new-pr`. After it's merged, Flathub builds and publishes
   the app. Claim it as verified with the `io.github.inmymoonsuit` ID, which Flathub checks
   against this GitHub account.

## CI

[`.github/workflows/release.yml`](../../.github/workflows/release.yml) builds the generic
edition on Windows, macOS, and Linux. Branded editions are never built there.

* **On a push to the `distribution` branch, or a pull request** that touches packaging,
  the workflow, `pyproject.toml`, or `uv.lock`, it's a **dry run**: it builds, smoke-tests,
  and uploads each platform's artifacts. On Windows it also builds the installer, installs
  and uninstalls it, and validates the winget manifests. On Linux it validates the
  `.desktop` file and the metainfo, builds the AppImage and starts it, and a separate job
  builds the Flatpak from source and starts it in the sandbox. On macOS it builds the `.dmg`
  and starts the app from the mounted image. It builds and checks the wheel and the sdist,
  and writes `SHA256SUMS` over every release file. It never signs, attests, drafts a
  release, or publishes. A newer push cancels a superseded dry run.
* **On a `v*` tag** it also signs the installer, once signing is switched on, attests
  every release file, and attaches them with `SHA256SUMS` to a **draft** GitHub release for
  the maintainer to publish. It publishes the wheel and the sdist to TestPyPI, then PyPI,
  each after the maintainer approves it ([PyPI](#pypi)).
* **Every action is pinned** to a full commit SHA, with its version in a comment, and
  Dependabot (`.github/dependabot.yml`) proposes updates weekly, grouped in one pull
  request.
* A failed build's last lines become a public annotation, since job logs need a signed-in
  reader.
