# date-gaps

Find missing days, hours or months in a load history. It uses only the Python standard library. It exits with code 1 when gaps are found, so you can use it as a pipeline check.

## Usage

```bash
ls -d /lake/sales/dt=* | python3 date_gaps.py                         # partition folders
python3 date_gaps.py samples/partitions.txt --start 2026-10-01 --end 2026-10-18
python3 date_gaps.py samples/loads.csv --column loaded_at --grain hour
python3 date_gaps.py samples/partitions.txt --json
```

```
2026-10-12
2026-10-16 .. 2026-10-17 (2)
date-gaps: 3 missing day(s) in 2 gap(s), 0 unparseable
```

## What it reads

- Partition paths written as `dt=` / `date=` / `ds=YYYY-MM-DD`, optionally followed by `/hr=HH`.
- ISO dates and timestamps from a CSV column or from stdin. Timestamps with an offset are converted to UTC before bucketing.
- `--start` and `--end` set the expected window, so a missing first or last period is caught too.
- Values it can't parse are counted and skipped.

## Tests

```bash
python3 -m unittest
```
