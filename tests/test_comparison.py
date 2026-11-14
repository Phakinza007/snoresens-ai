import unittest
from compare import comparison_row, session_summary


def recording(seconds, snore, events, part=1, contiguous=False):
    return dict(summary=dict(recording_seconds=seconds, detected_snore_seconds=snore,
                             snore_event_count=len(events), snore_percent_of_recording=100*snore/seconds,
                             snore_median_rms_dbfs=None), snore_events=events, timeline=[],
                session_id='night', part=part, contiguous_with_previous=contiguous)


class ComparisonTests(unittest.TestCase):
    def test_normalized_measures_and_missing_fields(self):
        item = recording(1800, 300, [])
        row = comparison_row('a.wav', item)
        self.assertEqual(row['snore_minutes_per_recording_hour'], 10)
        self.assertEqual(row['snore_percent_of_recording'], item['summary']['snore_percent_of_recording'])
        self.assertIsNone(row['median_dominant_frequency_hz'])
        self.assertIsNone(row['snore_median_rms_dbfs'])

    def test_session_weighting_and_boundary_merge(self):
        a = recording(10, 2, [dict(start_seconds=8, end_seconds=10, duration_seconds=2)])
        b = recording(30, 3, [dict(start_seconds=0, end_seconds=3, duration_seconds=3)], 2, True)
        result = session_summary([b, a])
        self.assertEqual(result['summary']['snore_percent_of_recording'], 12.5)
        self.assertEqual(result['summary']['snore_event_count'], 1)
        self.assertEqual(result['snore_events'][0]['duration_seconds'], 5)

    def test_unknown_join_does_not_merge_or_create_rhythm(self):
        a = recording(10, 2, [dict(start_seconds=8, end_seconds=10, duration_seconds=2)])
        b = recording(30, 3, [dict(start_seconds=0, end_seconds=3, duration_seconds=3)], 3, True)
        result = session_summary([a, b])
        self.assertEqual(result['summary']['snore_event_count'], 2)
        self.assertEqual(result['audio_patterns']['rhythm_summary']['interval_count'], 0)
        self.assertFalse(result['session_continuous'])

    def test_unknown_join_preserves_gaps_in_other_continuous_runs(self):
        a = recording(7, 1, [dict(start_seconds=0, end_seconds=1, duration_seconds=1)])
        b = recording(7, 1, [dict(start_seconds=6, end_seconds=7, duration_seconds=1)], 2, True)
        c = recording(1, 1, [dict(start_seconds=0, end_seconds=1, duration_seconds=1)], 4, False)
        a['timeline'] = [dict(start_seconds=i, duration_seconds=1, rms_dbfs=-20 if i==0 else None,
                              prediction='snore' if i==0 else 'non_snore') for i in range(7)]
        b['timeline'] = [dict(start_seconds=i, duration_seconds=1, rms_dbfs=-20 if i==6 else None,
                              prediction='snore' if i==6 else 'non_snore') for i in range(7)]
        result = session_summary([a,b,c])
        self.assertEqual(result['audio_patterns']['quiet_gaps'],
                         [dict(start_seconds=1.0, end_seconds=13.0, duration_seconds=12.0)])

    def test_session_rejects_mixed_ids_and_duplicate_parts(self):
        a = recording(10, 0, [])
        b = recording(10, 0, [])
        with self.assertRaises(ValueError): session_summary([a, b])
        b['part'] = 2
        b['session_id'] = 'other'
        with self.assertRaises(ValueError): session_summary([a, b])


if __name__ == '__main__': unittest.main()
