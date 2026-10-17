# Third-party notices

CADD Calculator is licensed under the Apache License 2.0 ([LICENSE.md](LICENSE.md)). It
includes, or its packaged builds bundle, the third-party components below, each under its
own license.

## Included in the source and in every build

### Tabler Icons 3.49.0

* **Files:** `src/caddcalc/gui/assets/icons/tabler/`. Only the icons the app uses are
  included; they're listed with their SHA-256 hashes in `manifest.toml`.
* **Source:** https://github.com/tabler/tabler-icons (npm package `@tabler/icons` 3.49.0)
* **License:** MIT. The full text follows, and also ships as
  `src/caddcalc/gui/assets/icons/tabler/LICENSE.txt`.

```text
MIT License

Copyright (c) 2020-2026 Paweł Kuna

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Bundled in packaged builds only

Packaged builds (`packaging/build.py`) also contain the runtime components below. Their
full license texts will be added here before the first public release (KI-016).

| Component | License | Project |
|---|---|---|
| Qt 6 (Core, Gui, Widgets, Svg) | LGPL-3.0 | https://www.qt.io/ |
| PySide6 and Shiboken6 (Qt for Python) | LGPL-3.0 | https://wiki.qt.io/Qt_for_Python |
| CPython | Python Software Foundation License 2.0 | https://www.python.org/ |
| OpenSSL (libcrypto) | Apache-2.0 | https://www.openssl.org/ |
| libffi | MIT | https://sourceware.org/libffi/ |
| Nuitka runtime | Apache-2.0 | https://nuitka.net/ |
| Microsoft Visual C++ runtime (Windows builds) | Microsoft redistributable license | https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist |

The Qt and PySide6 libraries ship as separate shared libraries in the app folder, so they
can be replaced with other compatible builds, as the LGPL-3.0 allows.
