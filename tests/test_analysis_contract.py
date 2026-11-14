import unittest
import numpy as np
from predict import summarize, build_output


class ContractTests(unittest.TestCase):
    def test_sound_review_and_breathing_outputs_are_available_without_timeline_export(self):
        summary, events, timeline = summarize([.1]*31, [0]*31, [None]*31, [1]*30+[.25], [-30]*31, .63)
        for row in timeline:
            row.update(yamnet_breathing_score=.9, yamnet_speech_score=.01)
        sr=16000; t=np.arange(int(30.25*sr))/sr
        audio=(.04+.03*np.cos(2*np.pi*t/4))*np.sin(2*np.pi*600*t)
        result=build_output('breathing.wav',summary,events,timeline,-45,10,False,audio=audio)
        self.assertNotIn('timeline',result)
        self.assertEqual(result['sound_review']['categories'][-1]['detected_seconds'],30.25)
        self.assertAlmostEqual(result['breathing_rate']['median_breaths_per_minute'],15,delta=.5)
        self.assertEqual(result['breathing_rate']['windows'][-1]['status'],'insufficient_duration')

    def test_partial_final_window_and_existing_fields(self):
        summary, events, timeline = summarize([0.8, 0.9], [0, 0], [None, None], [1, 0.25], [-30, None], 0.63)
        self.assertEqual(summary['recording_seconds'], 1.25)
        self.assertEqual(summary['detected_snore_seconds'], 1.25)
        self.assertEqual(events[0]['end_seconds'], 1.25)
        self.assertEqual(timeline[-1]['duration_seconds'], 0.25)
        output = build_output('sample.wav', summary, events, timeline, -45, 10, True)
        self.assertEqual(output['audio_patterns']['schema_version'], 1)
        self.assertIsInstance(output['timeline'][0]['snore_probability'], float)
        self.assertIn('snore_events', output)
        self.assertNotIn('timeline', build_output('sample.wav', summary, events, timeline, -45, 10, False))


if __name__ == '__main__':
    unittest.main()
