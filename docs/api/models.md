# Data models

## `Spectrum`

```python
wraw.Spectrum(
    function_number,
    scan_index,
    retention_time_min,
    mz,
    intensity,
)
```

Immutable data class representing one decoded mass spectrum.

### Attributes

`function_number` : `int`
: One-based acquisition function number.

`scan_index` : `int`
: Zero-based scan index within the function.

`retention_time_min` : `float`
: Scan retention time in minutes.

`mz` : `numpy.ndarray`
: Read-only, one-dimensional float32 m/z values.

`intensity` : `numpy.ndarray`
: Read-only, one-dimensional float32 intensities corresponding to `mz`.

### `tic`

```python
spectrum.tic
```

Total ion current as a `float`, calculated with a float64 accumulator.

### `base_peak_index`

```python
spectrum.base_peak_index
```

Index of the first maximum-intensity point, or `None` for an empty spectrum.

The base-peak values can be retrieved from the spectrum arrays:

```python
index = spectrum.base_peak_index
if index is not None:
    base_peak_mz = spectrum.mz[index]
    base_peak_intensity = spectrum.intensity[index]
```

## `Calibration`

```python
wraw.Calibration(coefficients, kind)
```

Immutable data class containing the calibration polynomial associated with an acquisition function.

### Attributes

`coefficients` : `tuple[float, ...]`
: Polynomial coefficients in ascending order.

`kind` : `str`
: Calibration equation identifier, such as `"T1"`.
