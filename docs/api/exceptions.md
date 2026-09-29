# Exceptions

## `WRawError`

```python
wraw.WRawError
```

Base class for package-specific exceptions. Catch this when all reader failures should be handled in the same way.

## `InvalidRawDirectoryError`

```python
wraw.InvalidRawDirectoryError
```

Raised when the supplied path is not a recognizable RAW directory, including when required files are absent.

## `UnsupportedFormatError`

```python
wraw.UnsupportedFormatError
```

Raised when the RAW directory uses a file layout, spectrum encoding, or calibration equation that has not been implemented and validated.

## `CorruptRawFileError`

```python
wraw.CorruptRawFileError
```

Raised when files in a RAW directory are internally inconsistent, such as scan offsets outside the associated DAT file.
