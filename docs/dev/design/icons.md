# Icons

The app uses [Tabler Icons](https://tabler.io/icons) (MIT), outline style, from one pinned
official release. Only the icons the app uses are in the repo.

| Where | What |
|---|---|
| `src/caddcalc/gui/assets/icons/tabler/outline/*.svg` | the vendored icons |
| `src/caddcalc/gui/assets/icons/tabler/manifest.toml` | pinned version, source, SHA-256 of every file |
| `src/caddcalc/gui/assets/icons/tabler/LICENSE.txt` | Tabler's MIT license, from the same version |
| `THIRD_PARTY_NOTICES.md` | the credit and license text; ships in builds and wheels |
| `packaging/fetch_tabler_icons.py` | downloads and verifies the icons |
| `src/caddcalc/gui/icons.py` | loads and recolors them |

## Adding, removing, or updating icons

```bash
uv run python packaging/fetch_tabler_icons.py --add copy refresh   # add by Tabler name
uv run python packaging/fetch_tabler_icons.py --remove copy        # drop one
uv run python packaging/fetch_tabler_icons.py --version 3.50.0     # move the pin
uv run python packaging/fetch_tabler_icons.py --check              # offline verify
```

Find names at https://tabler.io/icons (outline style). The script downloads only from the
official `@tabler/icons` npm package at the pinned version (through jsDelivr). It refuses
an icon or license that differs from the recorded hash, and it stops if the license is no
longer MIT. After moving the pin, update the version in `THIRD_PARTY_NOTICES.md`; a test
checks that they match.

Then use the icon in code with `icon("name")` (widgets) or `_img("name", role, scheme)`
(the results pane). `tests/test_icons.py` fails if the code uses an icon that isn't
vendored, or if a vendored icon isn't used, so the set stays minimal.

Never copy icons from other sources, including any locally purchased icon pack. Their
license terms differ (ADR-0008).

## Colors

Tabler SVGs draw in `currentColor`, which Qt's SVG renderer doesn't resolve.
`caddcalc.gui.icons` replaces it with the palette color for the icon's role (`icon`,
`icon_active`, `icon_error`, `icon_warning`; see [palette.md](palette.md#icon-colors)) in
the current light or dark scheme, then renders the SVG with QtSvg. When the system
switches between light and dark, the window clears the icon cache and recolors everything.

Packaged builds need Qt's `Svg` module, which `packaging/build.py` lists in its
pyside6-deploy spec.

## Icons in use

| Icon | Role | Used for |
|---|---|---|
| `category` | icon | domain groups in the calculator list |
| `calculator` | icon | calculators in the list |
| `info-circle` | icon | Help > About |
| `alert-triangle` | icon_warning | the Warnings heading in results |
| `alert-circle` | icon_error | "Check the inputs" in results |
