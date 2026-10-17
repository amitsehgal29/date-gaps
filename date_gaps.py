#!/usr/bin/env python3
"""date-gaps: find missing days, hours or months in a load history.

Standard library only. Reads dates from a CSV column, from dt=YYYY-MM-DD
partition paths (one per line, e.g. the output of `ls` or `hdfs dfs -ls`),
or from stdin, then reports every expected period that has no data, grouped
into contiguous ranges. Exits 1 when gaps are found, so it can fail a
pipeline check.
"""
import argparse
import csv
import json
import re
import sys
from datetime import date, datetime, timedelta

PART_RE = re.compile(r"(?:dt|date|ds)=(\d{4}-\d{2}-\d{2})(?:[/ ]+(?:hr|hour|hh)=(\d{1,2}))?")


def to_period(value, grain):
    v = value.strip()
    if not v:
        return None
    m = PART_RE.search(v)
    if m:
        d = date.fromisoformat(m.group(1))
        if grain == "hour":
            return datetime(d.year, d.month, d.day, int(m.group(2) or 0))
        v = m.group(1)
    t = v[:-1] + "+00:00" if v[-1:] in "Zz" else v
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo:
        dt = dt.replace(tzinfo=None) - (dt.utcoffset() or timedelta(0))
    if grain == "hour":
        return dt.replace(minute=0, second=0, microsecond=0)
    if grain == "month":
        return date(dt.year, dt.month, 1)
    return dt.date()


def step(p, grain):
    if grain == "hour":
        return p + timedelta(hours=1)
    if grain == "month":
        return date(p.year + (p.month == 12), p.month % 12 + 1, 1)
    return p + timedelta(days=1)


def find_gaps(periods, grain, start=None, end=None):
    """Return list of (first_missing, last_missing, count) ranges."""
    have = set(p for p in periods if p is not None)
    if not have and (start is None or end is None):
        return []
    lo = start if start is not None else min(have)
    hi = end if end is not None else max(have)
    gaps, cur, run_start, run_n, prev = [], lo, None, 0, None
    while cur <= hi:
        if cur in have:
            if run_start is not None:
                gaps.append((run_start, prev, run_n))
                run_start, run_n = None, 0
        else:
            if run_start is None:
                run_start = cur
            run_n += 1
            prev = cur
        cur = step(cur, grain)
    if run_start is not None:
        gaps.append((run_start, prev, run_n))
    return gaps


def fmt(p, grain):
    if grain == "hour":
        return p.strftime("%Y-%m-%dT%H:00")
    if grain == "month":
        return p.strftime("%Y-%m")
    return p.isoformat()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Report missing periods in a series of load dates.")
    ap.add_argument("source", nargs="?", default="-", help="CSV file, text file of paths, or - for stdin")
    ap.add_argument("--column", help="CSV column holding the date (omit for one value or path per line)")
    ap.add_argument("--grain", choices=["day", "hour", "month"], default="day")
    ap.add_argument("--start", help="expected first period (default: earliest seen)")
    ap.add_argument("--end", help="expected last period (default: latest seen)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    a = ap.parse_args(argv)

    f = sys.stdin if a.source == "-" else open(a.source, newline="", encoding="utf-8")
    try:
        if a.column:
            r = csv.DictReader(f)
            if a.column not in (r.fieldnames or []):
                print(f"date-gaps: column {a.column!r} not found", file=sys.stderr)
                return 2
            values = [row[a.column] for row in r]
        else:
            values = f.read().splitlines()
    finally:
        if f is not sys.stdin:
            f.close()

    periods = [to_period(v, a.grain) for v in values]
    bad = sum(1 for v, p in zip(values, periods) if v.strip() and p is None)
    start = to_period(a.start, a.grain) if a.start else None
    end = to_period(a.end, a.grain) if a.end else None
    if (a.start and start is None) or (a.end and end is None):
        print("date-gaps: could not parse --start/--end", file=sys.stderr)
        return 2
    gaps = find_gaps(periods, a.grain, start, end)
    missing = sum(n for _, _, n in gaps)

    if a.json:
        print(json.dumps({"grain": a.grain, "missing": missing, "unparseable": bad,
                          "gaps": [{"from": fmt(s, a.grain), "to": fmt(e, a.grain), "count": n} for s, e, n in gaps]}))
    else:
        for s, e, n in gaps:
            print(fmt(s, a.grain) if n == 1 else f"{fmt(s, a.grain)} .. {fmt(e, a.grain)} ({n})")
        print(f"date-gaps: {missing} missing {a.grain}(s) in {len(gaps)} gap(s), {bad} unparseable", file=sys.stderr)
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
