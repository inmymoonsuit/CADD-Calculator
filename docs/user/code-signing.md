# Code signing policy

How CADD Calculator's downloads are built, who signs and approves them, and how you can
check one. The project follows SignPath Foundation's
[conditions for open-source projects](https://signpath.org/terms) (checked 2026-10-25),
whichever signing service it uses. The decision behind this page is
[ADR-0022](../dev/decisions/0022-distribution-and-signing.md).

## Status

**Downloads aren't signed yet.** Signing comes with the first releases, through either
[SignPath Foundation](https://signpath.org)'s free signing for open-source projects or
Microsoft Artifact Signing under the maintainer's name. The maintainer hasn't chosen yet.
This page will name the service then. If it's SignPath, Windows will show
"SignPath Foundation" as the publisher, and this page will carry SignPath's attribution.

Until then, Windows shows "Windows protected your PC" for the installer, and macOS asks you
to allow the app in System Settings > Privacy & Security.

## Who builds

* Every download is built by this repository's release workflow
  (`.github/workflows/release.yml`), on GitHub-hosted runners, from a version tag. Nothing
  is built or signed on anyone's own computer.
* The build's settings come from the repository: the workflow, `packaging/build.py`, and
  the locked dependencies in `uv.lock`. Third-party actions are pinned to exact versions.
* Only the unbranded edition is built and signed there. Branded editions are built
  elsewhere and never signed under this policy
  ([ADR-0008](../dev/decisions/0008-licensing-and-third-party-assets.md), item 4).

## Who does what

| Role | Who | What they may do |
|---|---|---|
| Authors | the maintainer, [@inmymoonsuit](https://github.com/inmymoonsuit) | change the source without further review |
| Reviewers | the maintainer | review every change from anyone without commit rights (pull requests) before it's merged |
| Approvers | the maintainer | approve each signing request, by hand, for one release at a time |

Committers are the repository's collaborators with write access. Today that's the
maintainer alone.

## The review before a release

1. Every change reaches `main` through review. The review pays as much attention to build
   scripts and workflows as to the app, since they decide what gets built.
2. CI passes on Windows, macOS, and Linux: lint, types, the import-layer check, the tests,
   and a build of each platform's app that starts it and checks it (a smoke test).
3. The release workflow builds a **draft** release from the version tag. The maintainer
   checks its files, then publishes it by hand.
4. Signing (once set up) is a separate request for that release's files, and the maintainer
   approves it by hand. A release is never signed automatically.

## Accounts

The maintainer and every committer use multi-factor authentication on GitHub, and on the
signing service.

## Checking a download

* **The publisher (Windows, once signed):** right-click the installer, choose Properties,
  then Digital Signatures. It should name the signing service's certificate holder.
* **The checksum:** each release will attach a `SHA256SUMS` file. Compare it with your
  download's hash, for example `certutil -hashfile <file> SHA256` on Windows, or
  `shasum -a 256 <file>` on macOS and Linux.
* **The build's origin:** each release's files will carry a GitHub artifact attestation.
  With the GitHub CLI, run
  `gh attestation verify <file> --repo inmymoonsuit/CADD-Calculator`. It confirms that this
  repository's workflow built the file.

Checksums and attestations are being added to the release workflow for version 0.3.

## Privacy

CADD Calculator makes no network calls. It doesn't send any information to other
computers, now or in the background, and it has no telemetry
([ADR-0009](../dev/decisions/0009-packaging-and-distribution.md)). The packaged app doesn't
even include Qt's network module. None of the third-party components it bundles sends data
anywhere ([third-party notices](../../THIRD_PARTY_NOTICES.md)).

## Removing the app

The Windows installer adds an uninstaller: use Settings > Apps, or the Start menu. On
macOS, move the app to the Bin. On Linux, delete the AppImage, or remove the Flatpak with
`flatpak uninstall`.
