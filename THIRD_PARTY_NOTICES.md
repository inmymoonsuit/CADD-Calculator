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

### VT323, google/fonts commit 2da41909d08a

* **Files:** `src/caddcalc/gui/assets/fonts/vt323/VT323-Regular.ttf`, the welcome
  screen's display face, unmodified. It's listed with its SHA-256 hash in `manifest.toml`.
* **Source:** https://github.com/google/fonts (`ofl/vt323`, commit
  `2da41909d08a7bfeab32cfc163edb7be0c34395d`). The font's own project is
  https://github.com/phoikoi/VT323.
* **Copyright:** Copyright 2011, The VT323 Project Authors (peter.hull@oikoi.com).
  Designed by Peter Hull.
* **License:** SIL Open Font License 1.1. The full text follows, and also ships as
  `src/caddcalc/gui/assets/fonts/vt323/OFL.txt`.

```text
Copyright 2011, The VT323 Project Authors (peter.hull@oikoi.com)

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is copied below, and is also available with a FAQ at:
http://scripts.sil.org/OFL


-----------------------------------------------------------
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
-----------------------------------------------------------

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded,
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply
to any document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may
include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical
writer or other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as stand-alone text files, human-readable headers or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless explicit written permission is granted by the corresponding
Copyright Holder. This restriction only applies to the primary font name as
presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any
Modified Version, except to acknowledge the contribution(s) of the
Copyright Holder(s) and the Author(s) or with their explicit written
permission.

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are
not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
OTHER DEALINGS IN THE FONT SOFTWARE.
```

### Unicode CLDR 47, locale data

* **Files:** `src/caddcalc/core/i18n.py` holds data from CLDR: English's parent locales
  (which English locales read the British catalog) and English's plural rule
  (ADR-0020).
* **Source:** https://github.com/unicode-org/cldr, release 47
  (`common/supplemental/supplementalData.xml`, `parentLocales`; and the plural rules)
* **License:** Unicode License v3 (SPDX `Unicode-3.0`). The full text follows.

```text
UNICODE LICENSE V3

COPYRIGHT AND PERMISSION NOTICE

Copyright © 2004-2025 Unicode, Inc.

NOTICE TO USER: Carefully read the following legal agreement. BY
DOWNLOADING, INSTALLING, COPYING OR OTHERWISE USING DATA FILES, AND/OR
SOFTWARE, YOU UNEQUIVOCALLY ACCEPT, AND AGREE TO BE BOUND BY, ALL OF THE
TERMS AND CONDITIONS OF THIS AGREEMENT. IF YOU DO NOT AGREE, DO NOT
DOWNLOAD, INSTALL, COPY, DISTRIBUTE OR USE THE DATA FILES OR SOFTWARE.

Permission is hereby granted, free of charge, to any person obtaining a
copy of data files and any associated documentation (the "Data Files") or
software and any associated documentation (the "Software") to deal in the
Data Files or Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, and/or sell
copies of the Data Files or Software, and to permit persons to whom the
Data Files or Software are furnished to do so, provided that either (a)
this copyright and permission notice appear with all copies of the Data
Files or Software, or (b) this copyright and permission notice appear in
associated Documentation.

THE DATA FILES AND SOFTWARE ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT OF
THIRD PARTY RIGHTS.

IN NO EVENT SHALL THE COPYRIGHT HOLDER OR HOLDERS INCLUDED IN THIS NOTICE
BE LIABLE FOR ANY CLAIM, OR ANY SPECIAL INDIRECT OR CONSEQUENTIAL DAMAGES,
OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,
ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THE DATA
FILES OR SOFTWARE.

Except as contained in this notice, the name of a copyright holder shall
not be used in advertising or otherwise to promote the sale, use or other
dealings in these Data Files or Software without prior written
authorization of the copyright holder.

SPDX-License-Identifier: Unicode-3.0
```

## Bundled in packaged builds only

Packaged builds (`packaging/build.py`) also contain the runtime components below. Their
full license texts ship in the app folder's `licenses/`, vendored by
`packaging/fetch_notices.py` from each project's repository at a pinned tag, with their
SHA-256 in `packaging/notices/manifest.toml`. The build fails if any is missing.

| Component | License | Text in `licenses/` |
|---|---|---|
| Qt 6 (Core, Gui, Widgets, Svg, and on Linux DBus) | LGPL-3.0 | `LGPL-3.0.txt`, `GPL-3.0.txt` |
| Qt translations (`qtbase_*.qm`, from qttranslations) | LGPL-3.0 | `LGPL-3.0.txt`, `GPL-3.0.txt` |
| Third-party code inside Qt: FreeType, HarfBuzz, libpng, libjpeg-turbo, PCRE2, zlib, MD4C, double-conversion, TinyCBOR, the Unicode Character Database, the Wayland protocols, and others | each entry's own (BSD, MIT, zlib, FTL, Unicode, and others) | `Qt-third-party.txt`, one entry each with its copyright and full license text, from qtbase 6.12.0's `qt_attribution.json` files |
| PySide6 and Shiboken6 (Qt for Python) | LGPL-3.0 | `LGPL-3.0.txt`, `GPL-3.0.txt` |
| CPython | Python Software Foundation License 2.0 | `Python-LICENSE.txt` (CPython 3.12.14) |
| Software CPython includes: expat, libmpdec, zlib, libffi, OpenSSL | each one's own | `Python-incorporated-software.rst` (CPython 3.12.14's `Doc/license.rst`), and below |
| expat (`pyexpat`) | MIT | `expat-COPYING.txt` |
| OpenSSL's libcrypto | Apache-2.0 | `OpenSSL-LICENSE.txt` (OpenSSL 3.0.16) |
| libffi (`_ctypes`) | MIT | `libffi-LICENSE.txt` (libffi 3.4.4) |
| zlib | zlib License | `zlib-LICENSE.txt` (zlib 1.3.1) |
| bzip2 (`_bz2`) | bzip2 License | `bzip2-LICENSE.txt` (bzip2 1.0.8) |
| xz's liblzma (`_lzma`) | public domain before 5.4; 0BSD from 5.4 on | `xz-5.2-COPYING.txt`, `xz-COPYING.0BSD.txt` |
| Nuitka's runtime, compiled into the executable | Apache-2.0 | `Nuitka-LICENSE.txt` (Nuitka 4.1.1) |
| Microsoft Visual C++ runtime (Windows builds) | Microsoft Distributable Code terms | `Microsoft-Visual-C++-runtime.txt` (CPython 3.12.14's `PC/crtlicense.txt`) |

The texts are pinned to the versions CPython 3.12.14's own Windows build uses. Each
platform's Python may bundle other releases of the same libraries, under the same
licenses; xz's two texts cover both of its licensing eras.

The builds leave out Qt's network module, its TLS backends, and the image plugins the app
doesn't read (PDF, TIFF, WebP, TGA, WBMP, ICNS), so their notices aren't needed
(`docs/dev/packaging.md`, "What the build leaves out"). OpenSSL's libcrypto stays:
Python's `hashlib` uses it.

The Qt and PySide6 libraries ship as separate shared libraries in the app folder, and
Qt's translations as separate files (in `PySide6/translations/`, or `PySide6/Qt/translations/`
on Linux and macOS), so they can be replaced with other compatible builds, as the
LGPL-3.0 allows.
