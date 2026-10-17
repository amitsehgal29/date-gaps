import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime
from pathlib import Path

import date_gaps as g

S = Path(__file__).parent / "samples"


class CoreTests(unittest.TestCase):
    def test_partition_paths(self):
        self.assertEqual(g.to_period("/x/dt=2026-10-10/hr=07", "hour"), datetime(2026, 10, 10, 7))
        self.assertEqual(g.to_period("/x/dt=2026-10-10", "day"), date(2026, 10, 10))

    def test_offset_normalised_to_utc(self):
        self.assertEqual(g.to_period("2026-10-15T04:06:00+04:00", "hour"), datetime(2026, 10, 15, 0))

    def test_ranges(self):
        ps = [date(2026, 10, d) for d in (1, 2, 5, 7)]
        self.assertEqual(g.find_gaps(ps, "day"),
                         [(date(2026, 10, 3), date(2026, 10, 4), 2), (date(2026, 10, 6), date(2026, 10, 6), 1)])

    def test_expected_window_catches_edges(self):
        gaps = g.find_gaps([date(2026, 10, 2)], "day", date(2026, 10, 1), date(2026, 10, 3))
        self.assertEqual([n for *_, n in gaps], [1, 1])

    def test_month_rollover(self):
        self.assertEqual(g.step(date(2026, 12, 1), "month"), date(2027, 1, 1))
        self.assertEqual(g.find_gaps([date(2026, 11, 1), date(2027, 2, 1)], "month")[0][2], 2)

    def test_no_gaps(self):
        self.assertEqual(g.find_gaps([date(2026, 1, 1), date(2026, 1, 2)], "day"), [])


class CliTests(unittest.TestCase):
    def run_cli(self, *a):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = g.main(list(a))
        return code, out.getvalue()

    def test_partitions_file(self):
        code, out = self.run_cli(str(S / "partitions.txt"))
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines(), ["2026-10-12", "2026-10-16 .. 2026-10-17 (2)"])

    def test_hourly_csv(self):
        code, out = self.run_cli(str(S / "loads.csv"), "--column", "loaded_at", "--grain", "hour")
        self.assertEqual(out.splitlines(), ["2026-10-15T02:00 .. 2026-10-15T03:00 (2)"])


if __name__ == "__main__":
    unittest.main()
