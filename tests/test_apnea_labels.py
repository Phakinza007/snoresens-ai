import unittest
from prepare_apnea import label_windows


class ApneaLabelTests(unittest.TestCase):
    def test_explicit_scored_sleep_is_required_for_negative_labels(self):
        self.assertEqual(label_windows(60,[],[]),[])
        self.assertEqual(label_windows(60,[(0,60)],[]),
                         [dict(start_seconds=0,duration_seconds=30,label=0),dict(start_seconds=30,duration_seconds=30,label=0)])
    def test_overlap_union_and_boundary_windows(self):
        events=[dict(start_seconds=5,end_seconds=12,event_type='obstructive_apnea'),
                dict(start_seconds=10,end_seconds=16,event_type='hypopnea'),
                dict(start_seconds=58,end_seconds=65,event_type='central_apnea')]
        rows=label_windows(90,[(0,90)],events)
        self.assertEqual(rows,[dict(start_seconds=0,duration_seconds=30,label=1)])
    def test_wake_artifact_and_partial_windows_are_excluded(self):
        events=[dict(start_seconds=40,end_seconds=41,event_type='artifact')]
        self.assertEqual(label_windows(65,[(0,25),(30,65)],events),[])
    def test_invalid_annotations_rejected(self):
        for event in [dict(start_seconds=-1,end_seconds=5,event_type='hypopnea'),
                      dict(start_seconds=1,end_seconds=5,event_type='snore')]:
            with self.assertRaises(ValueError):label_windows(60,[(0,60)],[event])


if __name__ == '__main__':unittest.main()
