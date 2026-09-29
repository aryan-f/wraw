# API reference

The public API is exported from the top-level `wraw` package.

## Entry point

- [`wraw.read(path)`](./readers#read) opens a Waters RAW directory and returns a [`RawFile`](./readers#rawfile).

## Readers

- [`RawFile`](./readers#rawfile) represents one `.raw` directory.
- [`RawFunction`](./readers#rawfunction) represents one acquisition function and provides scan access.

## Data models

- [`Spectrum`](./models#spectrum) contains decoded m/z and intensity arrays.
- [`Calibration`](./models#calibration) contains the calibration polynomial associated with a function.

## Exceptions

- [`WRawError`](./exceptions#wrawerror) is the base package exception.
- [`InvalidRawDirectoryError`](./exceptions#invalidrawdirectoryerror) reports invalid or incomplete RAW directories.
- [`UnsupportedFormatError`](./exceptions#unsupportedformaterror) reports layouts that the reader does not support.
- [`CorruptRawFileError`](./exceptions#corruptrawfileerror) reports internally inconsistent files.
