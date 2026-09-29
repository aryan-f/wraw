# Getting started

## Installation

Install the package directly from GitHub:

```bash
pip install git+https://github.com/aryan-f/wraw.git
```

`wraw` requires Python 3.11 or newer and NumPy 1.26 or newer.

## Open a RAW directory

A Waters `.raw` acquisition is a directory rather than a single file. Pass that directory to [`wraw.read()`](/api/readers#read):

```python
from pathlib import Path

import wraw

raw = wraw.read(Path("sample.raw"))
```

The returned [`RawFile`](/api/readers#rawfile) parses the small metadata and index files immediately. Spectrum records remain on disk until requested.

## Inspect the acquisition

```python
print(raw.path)
print(raw.metadata["Instrument"])
print(raw.polarity)

for function in raw.functions:
    print(function.number, function.description, function.scan_count)
```

Function numbers are one-based because they correspond to files such as `_FUNC001.DAT`. Scan indices are zero-based Python indices.

## Read spectra

```python
function = raw.function(1)

spectrum = function.read_spectrum(0)
print(spectrum.retention_time_min)
print(spectrum.mz)
print(spectrum.intensity)
print(spectrum.tic)
```

To stream every spectrum without loading the entire acquisition into memory:

```python
for spectrum in function.iter_spectra():
    process(spectrum)
```

## Read scan-level traces

Retention time and total ion current are available directly from the scan index:

```python
retention_time = function.retention_times
tic = function.tic
```

Both properties return read-only NumPy arrays in scan order. They do not decode the spectra in the DAT file.

## Error handling

All package-specific exceptions inherit from [`WRawError`](/api/exceptions#wrawerror):

```python
import wraw

try:
    raw = wraw.read("sample.raw")
except wraw.InvalidRawDirectoryError as error:
    print(error)
except wraw.UnsupportedFormatError as error:
    print(error)
```

The initial implementation intentionally supports only layouts positively identified by the reader. See the [current scope](https://github.com/aryan-f/wraw#current-scope) for details.
