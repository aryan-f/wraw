---
layout: home

hero:
  name: wraw
  text: Read Waters RAW data with Python
  tagline: A small, cross-platform, NumPy-only reader for Waters MassLynx .raw directories.
  actions:
    - theme: brand
      text: Get started
      link: /guide/getting-started
    - theme: alt
      text: API reference
      link: /api/

features:
  - title: NumPy only
    details: No vendor runtime or platform-specific binary dependency is required.
  - title: Lazy spectrum access
    details: Large DAT files are memory-mapped and individual spectra are decoded on demand.
  - title: Explicit validation
    details: Unrecognized layouts raise clear exceptions instead of being decoded speculatively.
---

## Quick example

```python
import wraw

raw = wraw.read("sample.raw")
function = raw.function(1)
spectrum = function.read_spectrum(0)

print(spectrum.mz)
print(spectrum.intensity)
```
