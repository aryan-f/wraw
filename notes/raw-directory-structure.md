# Waters RAW directory structure

> [!NOTE]
> These are reverse-engineering notes based on the Waters Xevo G2-XS RAW
> directories currently available to this project. They describe observed
> layouts, not a complete specification for every Waters instrument or
> MassLynx version.

A Waters `.raw` acquisition is a directory rather than a single file. It acts
like a small database: directory-level files describe the run and its
acquisition functions, while each function has binary data, index, and status
files.

## Typical layout

```text
sample.raw/
|-- _HEADER.TXT
|-- _FUNCTNS.INF
|-- _extern.inf
|-- _INLET.INF          # optional
|-- _FUNC001.DAT
|-- _FUNC001.IDX
|-- _FUNC001.STS
|-- _FUNC002.DAT        # present when a second function exists
|-- _FUNC002.IDX
|-- _FUNC002.STS
`-- ...
```

The numeric suffix is the one-based function number. A run containing only
function 1 has `_FUNC001.*`; a run with additional acquisition functions may
also have `_FUNC002.*`, `_FUNC003.*`, and so on.

Files or subdirectories added by downstream software are not necessarily part
of the original Waters format and must not automatically be treated as
authoritative RAW metadata.

## Directory-level metadata

### `_HEADER.TXT`

This is a plain-text collection of run-level metadata. Observed fields include:

- acquisition and sample names;
- acquisition date and time;
- instrument name;
- method paths;
- calibration names and parameters; and
- calibration polynomial coefficients for individual functions.

For example, a line ending in `T1` identifies the calibration equation family
used for that function. `wraw` reads the coefficients from this file and
applies them to the decoded raw mass values.

### `_FUNCTNS.INF`

This is a binary table of acquisition-function descriptors. In the available
samples, each function descriptor occupies 416 bytes. Fields already
identified include:

- scan and interscan times;
- acquisition mass limits; and
- bytes whose meanings have not yet been established.

The descriptor order corresponds to `_FUNC001.*`, `_FUNC002.*`, and so forth.
The exact interpretation of every byte is not yet known.

### `_extern.inf`

This is a human-readable export of the instrument and acquisition method. It
provides useful labels and values that complement `_FUNCTNS.INF`, including:

- ionization polarity;
- instrument settings;
- acquisition mass range;
- function descriptions;
- continuum or centroid acquisition mode;
- collision energy; and
- acquisition-specific parameters such as DESI stage settings.

`Data Format: Continuum` describes the acquisition data mode. It does **not**
by itself identify the lower-level binary encoding used by `_FUNCnnn.DAT`.

### `_INLET.INF`

This optional text file describes the inlet or chromatography method. It is
present in the available DESI acquisition but absent from the available REIMS
acquisition. It is not required for basic spectrum decoding.

## Per-function files

### `_FUNCnnn.DAT`

This contains the spectral point data for one acquisition function. The scans
are concatenated into a single binary stream:

```text
scan 0 points | scan 1 points | scan 2 points | ... | final scan
```

The observed DAT files do not have a self-describing header before every scan.
Random access therefore depends on the corresponding IDX file.

### `_FUNCnnn.IDX`

This is the scan index for the corresponding DAT stream. In the currently
supported layout:

- every IDX record is 30 bytes;
- there is one record per scan;
- the retention time is stored as a little-endian 32-bit float at byte offset
  `0x0c`; and
- the DAT byte offset is stored as a little-endian unsigned 32-bit integer at
  byte offset `0x16`.

Consequently, the scan count is:

```text
IDX file size / 30 bytes per record
```

For example, the DESI sample has a 1,350,390-byte index:

```text
1,350,390 / 30 = 45,013 scans
```

The meanings of the remaining IDX bytes have not yet been established.

#### Offsets larger than 4 GiB

The observed DAT offset field is only 32 bits wide, so it can represent values
from 0 through 4,294,967,295. When a DAT stream crosses a 4 GiB boundary, the
stored value rolls over to a small number. Only the numeric offset wraps; the
spectral data remains sequential in the DAT file.

The full byte position can be reconstructed as:

```text
actual offset = stored offset + rollover count * 4,294,967,296
```

A rollover is detected when the next stored offset is smaller than the
previous one. The 9.47 GB DESI DAT stream crosses two such boundaries. After
unwrapping those offsets, they are monotonic and every indexed scan boundary
is valid.

### `_FUNCnnn.STS`

This appears to contain per-scan status and statistics. Likely candidates
include total ion current, base-peak mass and intensity, peak count, collision
energy, instrument settings, and error flags, but their locations have not yet
been established.

The STS format has not yet been decoded and is not required to retrieve the
m/z and intensity arrays from the observed DAT files.

## Functions

A Waters *function* is an independently configured acquisition stream inside
one run. Different functions may represent different scan types, mass ranges,
collision energies, or other acquisition conditions. Each function has its own
scan sequence and normally its own DAT, IDX, and STS files.

The available DESI sample contains one function. This is supported by all of
the following:

- `_FUNCTNS.INF` contains one observed 416-byte descriptor;
- only `_FUNC001.*` files are present; and
- `_extern.inf` contains one section headed `Function 1 - TOF MS FUNCTION`.

For that sample, `_extern.inf` identifies negative electrospray polarity,
continuum acquisition, and a nominal mass range of m/z 50-1500. The binary
function descriptor independently contains mass limits of 50 and 1500.

## DESI raster parameters

The DESI method in `_extern.inf` contains these stage parameters:

```text
DesiXStart   9.8000
DesiYStart  -10.9000
DesiXLength 24.2000
DesiXStep    0.1000
DesiYLength 18.6000
DesiYStep    0.1000
```

These imply, rather than explicitly store, the following nominal raster:

```text
24.2 / 0.1 = 242 X positions
18.6 / 0.1 = 186 Y positions
242 * 186  = 45,012 positions
```

The nominal final coordinates can similarly be derived as 33.9 on X and 7.6
on Y. The start positions and step sizes are explicit; the raster dimensions,
final coordinates, and relationship between stage positions and raw scans are
inferences. Exact spatial mapping should not be assumed until it is established
from authoritative acquisition data.

## DAT encoding detection

No authoritative field has yet been found that explicitly declares the
observed eight-byte packed DAT representation. In particular, the
continuum/centroid setting in `_extern.inf` is not such a flag.

The current decoder identifies the observed representation structurally:

1. IDX records provide the byte boundaries of each scan.
2. Every indexed scan length is divisible by eight.
3. Decoding the eight-byte words with the recovered bit layout produces
   plausible m/z and intensity values.
4. The decoded boundary masses agree with the acquisition range declared in
   the function metadata.
5. Decoded point counts, mass bounds, and intensity statistics are consistent
   across the available REIMS and DESI acquisitions.

Other Waters instruments or software versions may use centroided data,
different IDX layouts, different DAT encodings, or multidimensional data such
as ion mobility. The available samples do not establish those layouts. `wraw`
should therefore accept only layouts it can positively validate and fail
clearly for unknown variants.

## Minimum path for reading spectra

```text
_HEADER.TXT
    -> calibration

_FUNCTNS.INF + _extern.inf
    -> function and acquisition metadata

_FUNCnnn.IDX
    -> scan count, retention times, and DAT byte positions

_FUNCnnn.DAT
    -> packed m/z and intensity values
```
