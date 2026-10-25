# ADR-0022: Distribution and signing, starting free

* **Status:** Accepted (not built). On 2026-10-18 the maintainer chose: "let's start with the free path, and I'll figure out the Microsoft, Google Play, and Apple fees in the coming weeks."
* **Builds on:** ADR-0008 (licensing), ADR-0009 (packaging), ADR-0011 (branding packs)

## Context

* The app already builds standalone executables with Nuitka in GitHub Actions on Windows, macOS and Linux (`release.yml` on `v*` tags), plus a wheel and an sdist. None of these is signed.
* The maintainer wants distribution that's inexpensive, works on all platforms, is built safely, and doesn't hurt users' trust at install time.

## What's true in 2026 (research, with sources, in docs/dev/research/distribution.md)

* **Windows:**
  * An unsigned installer shows "Windows protected your PC". Smart App Control can block it outright.
  * A newly signed installer is still "unrecognized" until it builds reputation. That takes weeks of downloads, and it carries over to later versions with the same identity.
  * EV certificates no longer skip this; Microsoft removed that in 2024.
  * Packages from the Microsoft Store are re-signed by Microsoft, so they show no warning.
  * Since June 2023, signing keys must live in a hardware or cloud HSM, so no key file can sit in CI secrets.
* **SignPath Foundation** signs open-source projects for free:
  * Builds must come from GitHub-hosted runners.
  * Each release is approved by hand.
  * The project needs MFA, a code-signing policy page, and an existing release.
  * Windows shows "SignPath Foundation" as the publisher.
* **Microsoft Artifact Signing** isn't available on free, trial or sponsored Azure subscriptions. It needs a paid subscription (confirmed on 2026-10-18, when a deployment on a free-trial subscription was refused).
* **macOS:** with no Developer ID ($99 a year) and notarization, users must go to System Settings > Privacy & Security > "Open Anyway". Homebrew no longer accepts unsigned casks.
* **Linux:** Flathub builds from source and is trusted. An AppImage suits the Nuitka output.

## Decision

### The free tier, now

* **Windows:**
  * An Inno Setup installer wrapping the Nuitka build, signed through SignPath Foundation from GitHub-hosted runners.
  * The same installer submitted to winget.
  * An MSIX in the Microsoft Store, if the free individual account holds.
* **macOS:** the Nuitka .app in a .dmg, unsigned for now. The download page and README say plainly how to open it ("Open Anyway"), and why.
* **Linux:**
  * A Flathub listing built from source (a manifest with pip sources).
  * An AppImage of the Nuitka build as a direct download.
* **Every release, on every platform:**
  * SHA256SUMS
  * GitHub artifact attestations, verifiable with `gh attestation verify`
  * the wheel and sdist through PyPI Trusted Publishing, with its attestations
* **A code-signing policy page** in the docs, as SignPath requires, stating who signs, how builds are made, and the review that comes before each release.

### Later, at the maintainer's choice of timing

* **Apple Developer Program ($99 a year):** Developer ID signing and notarization in CI, then a Homebrew cask. This removes the macOS warning.
* **Microsoft Artifact Signing (about $120 a year, on a paid Azure subscription):** signing under the maintainer's own name. It's mainly for the branded editions, which SignPath won't sign because they're built from a private pack.
* **Google Play ($25 once)** and Android generally: a separate project. It needs a phone-sized design and PySide6's Android tooling, and Play requires a 14-day closed test with 12 testers for a new personal account.

## Consequences

* Windows and Linux users get signed or store-trusted installs for $0. Windows shows a SmartScreen prompt naming "SignPath Foundation" until the app builds reputation.
* macOS users see Apple's warning until the program fee is paid. The download notes explain how to open the app.
* The maintainer must apply to SignPath, turn on MFA everywhere, approve each signed release, open the free Store account, and submit to Flathub.

## Amendment (2026-10-25): the sources, and what they correct

The research claims above now have sources, each checked on 2026-10-25, in
[docs/dev/research/distribution.md](../research/distribution.md). The decision stands. These
corrections change only the facts behind it:

* **Store re-signing (W4):** Microsoft re-signs **MSIX** packages, not EXE or MSI
  installers. An Inno Setup installer submitted to the Store must already be signed with a
  publicly trusted certificate, so the Store plan needs the MSIX.
* **Keys in hardware (W5):** a cloud HSM or a signing service meets the rule, so CI may call
  SignPath or Artifact Signing. What CI may never hold is an exportable key file.
* **Artifact Signing (A1):** that is now its name, formerly Trusted Signing, and it's
  generally available. Basic is $9.99 a month (about $120 a year, as above). An individual
  can only validate from the US or Canada, with a government ID.
* **SignPath Foundation (S1):** besides the conditions listed, every team member needs MFA,
  and an executable needs "a certain verifiable reputation" before SignPath will sign it.
  Our first release can't be signed through SignPath: it must already be released, in the
  form to be signed.
* **Homebrew (M2):** the rule is that a cask must pass Gatekeeper, which means Developer ID
  and notarization. Casks that fail have been disabled since September 2026.
* **Attestations (G1):** `actions/attest` replaces `actions/attest-build-provenance`, which
  now only wraps it.

The code-signing policy page SignPath asks for is
[docs/user/code-signing.md](../../user/code-signing.md).

## Amendment (2026-10-25): the first release's scope

The maintainer set the first release's scope on 2026-10-25, relayed by the project
manager: an **unsigned pre-release, `v0.1.0a1`**, at the least effort and cost, with Windows
and Linux files and no macOS download yet. Self-signing was considered and dropped: a
self-signed certificate isn't trusted by Windows, so it would add work with no change to
the SmartScreen prompt users see.

* **What the release carries:** the Windows zip and installer, the Linux archive and
  AppImage, and `SHA256SUMS`, each attested. The release workflow's `RELEASE_PLATFORMS`
  list picks them; macOS is still built and smoke-tested on every run, and comes back by
  adding it to that list.
* **What waits:** signing (SignPath asks for a project that's already released), macOS
  notarization, PyPI (switched off by the `PUBLISH_PYPI` variable), and the Flathub
  submission.
* **The pre-release:** `draft-release` marks a tag with an `a`, `b`, `rc`, or `.dev`
  suffix as a pre-release.
