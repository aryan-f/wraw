# Readers

## `read`

```python
wraw.read(path)
```

Open a Waters MassLynx RAW directory.

### Parameters

`path` : `str` or `pathlib.Path`
: Path to a `.raw` directory.

### Returns

`RawFile`
: Parsed, lazy reader for the acquisition.

### Raises

`InvalidRawDirectoryError`
: The path is not a directory or a required file is absent.

`UnsupportedFormatError`
: The acquisition uses a layout or encoding that has not been validated.

`CorruptRawFileError`
: Scan offsets are inconsistent with the associated data file.

## `RawFile`

```python
wraw.RawFile(path)
```

Reader for one Waters MassLynx RAW directory. Prefer [`wraw.read()`](#read) for normal construction.

### Attributes

`path` : `pathlib.Path`
: Path to the RAW directory.

`metadata` : `dict[str, str]`
: Run and method metadata parsed from `_HEADER.TXT` and `_extern.inf`.

`polarity` : `str` or `None`
: Acquisition polarity, when present in `_extern.inf`.

`functions` : `tuple[RawFunction, ...]`
: Acquisition functions in file order.

`calibrations` : `dict[int, Calibration]`
: Calibrations keyed by one-based function number.

### `function`

```python
raw.function(number)
```

Return the function with the given one-based number.

#### Parameters

`number` : `int`
: One-based function number.

#### Returns

`RawFunction`
: The requested acquisition function.

#### Raises

`KeyError`
: No function has that number.

### `read_spectrum`

```python
raw.read_spectrum(function_number, scan_index)
```

Decode one spectrum selected by function and scan.

#### Parameters

`function_number` : `int`
: One-based acquisition function number.

`scan_index` : `int`
: Zero-based scan index.

#### Returns

`Spectrum`
: Decoded spectrum.

## `RawFunction`

One acquisition function with lazy random-access spectrum reads. Instances are normally obtained from [`RawFile.functions`](#attributes) or [`RawFile.function()`](#function).

### Properties

`number` : `int`
: One-based function number corresponding to `_FUNCnnn.*`.

`description` : `str` or `None`
: Human-readable function description from `_extern.inf`.

`scan_count` : `int`
: Number of indexed scans.

`scan_time_s` : `float`
: Nominal scan duration in seconds.

`interscan_time_s` : `float`
: Nominal delay between scans in seconds.

`mass_range` : `tuple[float, float]`
: Lower and upper acquisition masses.

`polarity` : `str` or `None`
: Run polarity.

`data_format` : `str` or `None`
: Human-readable acquisition mode, such as `"Continuum"`.

`encoding` : `str`
: Validated spectrum-record encoding.

`retention_times` : `numpy.ndarray`
: Read-only float32 retention times in minutes, in scan order.

`tic` : `numpy.ndarray`
: Read-only float32 total ion current values, in scan order.

### `read_spectrum`

```python
function.read_spectrum(scan_index)
```

Decode one zero-based scan.

#### Parameters

`scan_index` : `int`
: Zero-based scan index within this function.

#### Returns

`Spectrum`
: Decoded m/z and intensity arrays with scan metadata.

#### Raises

`TypeError`
: The scan index is not an integer.

`IndexError`
: The scan index is outside the function.

### `iter_spectra`

```python
function.iter_spectra()
```

Yield [`Spectrum`](./models#spectrum) instances in scan order. Only the current scan is decoded.

### `scan_byte_range`

```python
function.scan_byte_range(scan_index)
```

Return the start-inclusive and stop-exclusive DAT byte offsets for a scan as a tuple of integers.
