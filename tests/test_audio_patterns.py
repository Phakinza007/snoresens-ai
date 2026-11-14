import json
import unittest
import numpy as np
from audio_patterns import detect_quiet_gaps, spectral_features, summarize_rhythm, build_patterns


def row(start, duration=1, level=-60):
    return dict(start_seconds=start, duration_seconds=duration, rms_dbfs=level)


class AudioPatternTests(unittest.TestCase):
    def test_gap_boundaries_and_real_duration(self):
        events = [dict(start_seconds=0, end_seconds=1), dict(start_seconds=11, end_seconds=12)]
        self.assertEqual(detect_quiet_gaps([row(i) for i in range(1, 11)], events),
                         [dict(start_seconds=1.0, end_seconds=11.0, duration_seconds=10.0)])
        self.assertEqual(detect_quiet_gaps([row(1, 9.9)], events), [])
        self.assertEqual(detect_quiet_gaps([row(1, 9), row(10, 1)], events),
                         [dict(start_seconds=1.0, end_seconds=11.0, duration_seconds=10.0)])

    def test_noise_breaks_quiet_run_and_silence_needs_snore_bounds(self):
        events = [dict(start_seconds=0, end_seconds=1), dict(start_seconds=22, end_seconds=23)]
        timeline = [row(i, level=-20 if i == 11 else None) for i in range(1, 22)]
        self.assertEqual(len(detect_quiet_gaps(timeline, events)), 2)
        self.assertEqual(detect_quiet_gaps([row(0, 30, None)], []), [])
        self.assertEqual(detect_quiet_gaps([row(0, 30, -20)], events), [])

    def test_noncontiguous_rows_do_not_create_gap(self):
        events = [dict(start_seconds=0, end_seconds=1), dict(start_seconds=22, end_seconds=23)]
        self.assertEqual(detect_quiet_gaps([row(1, 6), row(16, 6)], events), [])

    def test_invalid_settings(self):
        for threshold, duration in [(float('nan'), 10), (-45, 0), (-45, float('inf'))]:
            with self.assertRaises(ValueError):
                detect_quiet_gaps([], [], threshold, duration)

    def test_frequency(self):
        for hz in (200, 800):
            signal = np.sin(2 * np.pi * hz * np.arange(16000) / 16000)
            result = spectral_features(signal, 16000)
            self.assertAlmostEqual(result['dominant_frequency_hz'], hz, delta=1)
            self.assertAlmostEqual(result['spectral_centroid_hz'], hz, delta=1)

    def test_zero_dc_short_frames(self):
        for signal in [np.zeros(16000), np.ones(16000), np.array([0.1]), np.array([])]:
            self.assertIsNone(spectral_features(signal, 16000)['dominant_frequency_hz'])

    def test_rhythm(self):
        events = [dict(start_seconds=t) for t in (0, 5, 10, 15)]
        result = summarize_rhythm(events)
        self.assertEqual(result['interval_count'], 3)
        self.assertEqual(result['mean_start_interval_seconds'], 5)
        self.assertEqual(result['std_start_interval_seconds'], 0)
        self.assertEqual(result['interval_cv'], 0)
        self.assertIsNone(summarize_rhythm(events[:2])['interval_cv'])

    def test_strict_json_silence(self):
        result = build_patterns([row(0, 1, None)], [], -45, 10)
        json.dumps(result, allow_nan=False)
        self.assertIsNone(result['frequency_summary']['median_dominant_frequency_hz'])


if __name__ == '__main__':
    unittest.main()
