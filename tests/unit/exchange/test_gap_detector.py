from exchange.streams.gap_detector import GapDetector


class TestGapDetector:
    def test_no_gap(self):
        gd = GapDetector()
        assert gd.check({"seq": 1}) is False
        assert gd.check({"seq": 2}) is False

    def test_gap_detected(self):
        gd = GapDetector()
        gd.check({"seq": 1})
        assert gd.check({"seq": 5}) is True

    def test_duplicate_not_a_gap(self):
        gd = GapDetector()
        gd.check({"seq": 1})
        gd.check({"seq": 2})
        assert gd.check({"seq": 2}) is False

    def test_no_seq_field_returns_false(self):
        gd = GapDetector()
        assert gd.check({"data": "no seq"}) is False
