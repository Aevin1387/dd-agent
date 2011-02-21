import time
import unittest
from checks import *

class TestCore(unittest.TestCase):
    "Tests to validate the core check logic"
    
    def setUp(self):
        self.c = Check()
        self.c.gauge("test-metric")
        self.c.counter("test-counter")

    def test_gauge(self):
        self.assertEquals(self.c.is_gauge("test-metric"), True)
        self.assertEquals(self.c.is_counter("test-metric"), False)
        self.c.save_sample("test-metric", 1.0)
        # call twice in a row, should be invariant
        self.assertEquals(self.c.get_sample("test-metric"), 1.0)
        self.assertEquals(self.c.get_sample("test-metric"), 1.0)
        self.assertEquals(self.c.get_sample_with_timestamp("test-metric")[1], 1.0)
        # new value, old one should be gone
        self.c.save_sample("test-metric", 2.0)
        self.assertEquals(self.c.get_sample("test-metric"), 2.0)
        self.assertEquals(len(self.c._sample_store["test-metric"]), 1)
        # with explicit timestamp
        self.c.save_sample("test-metric", 3.0, 1298066183.607717)
        self.assertEquals(self.c.get_sample_with_timestamp("test-metric"), (1298066183.607717, 3.0))

    def testEdgeCases(self):
        self.assertRaises(CheckException, self.c.get_sample, "unknown-metric")
        # same value
        self.c.save_sample("test-counter", 1.0, 1.0)
        self.c.save_sample("test-counter", 1.0, 1.0)
        self.assertRaises(Infinity, self.c.get_sample, "test-counter")

    def test_counter(self):
        self.c.save_sample("test-counter", 1.0, 1.0)
        self.assertRaises(UnknownValue, self.c.get_sample, "test-counter")
        self.c.save_sample("test-counter", 2.0, 2.0)
        self.assertEquals(self.c.get_sample("test-counter"), 1.0)
        self.assertEquals(self.c.get_sample_with_timestamp("test-counter"), (2.0, 1.0))
        self.c.save_sample("test-counter", -2.0, 3.0)
        self.assertEquals(self.c.get_sample_with_timestamp("test-counter"), (3.0, -4.0))

    def test_samples(self):
        self.assertEquals(self.c.get_samples(), {})
        self.c.save_sample("test-metric", 1.0, 0.0)  # value, ts
        self.c.save_sample("test-counter", 1.0, 1.0) # value, ts
        self.c.save_sample("test-counter", 0.0, 2.0) # value, ts
        assert "test-metric"  in self.c.get_samples_with_timestamps(), self.c.get_samples_with_timestamps()
        self.assertEquals(self.c.get_samples_with_timestamps()["test-metric"], (0.0, 1.0))
        assert "test-counter" in self.c.get_samples_with_timestamps(), self.c.get_samples_with_timestamps()
        self.assertEquals(self.c.get_samples_with_timestamps()["test-counter"], (2.0, -1.0))

if __name__ == '__main__':
    unittest.main()
