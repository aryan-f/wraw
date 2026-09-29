# wraw

`wraw` is a pure Python reader for Waters MassLynx `.raw` directories. The project currently targets the file layouts produced by the Waters instruments used in our lab and rejects layouts it cannot positively identify.

Please [open an issue](https://github.com/aryan-f/wraw/issues) to suggest new features or report bugs. Contributions are welcome!

## Installation

Install the current development version directly from GitHub:

```bash
pip install git+https://github.com/aryan-f/wraw.git
```

## Basic usage

```python
import wraw

raw = wraw.read("sample.raw")

print(raw.metadata["Instrument"])
print(raw.polarity)

function = raw.function(1)
print(function.scan_count)
print(function.mass_range)

spectrum = function.read_spectrum(0)
print(spectrum.mz)
print(spectrum.intensity)
```

Function numbers are one-based because they correspond to files such as
`_FUNC001.DAT`. Scan indices are zero-based Python indices. See
[examples](#examples) for more details.

## Current scope

The initial reader supports the 30-byte scan index and eight-byte packed
spectrum records validated against our Xevo G2-XS acquisitions. Large DAT
files are read lazily with NumPy memory maps. Unknown layouts raise an explicit
error rather than being decoded speculatively.

See [Waters RAW directory structure](notes/raw-directory-structure.md) for the
current format notes.

## Examples

See the following notebooks for examples of reading Waters RAW files:

- [REIMS Skin MS](example/reims.ipynb)
- [DESI Colon MSI](example/desi.ipynb)
