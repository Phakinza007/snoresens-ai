import json
import unittest

import numpy as np

from sleep_audio import add_sound_scores, build_sound_events, breathing_rate_over_time


def rows(seconds, **overrides):
    return [dict(start_seconds=i, duration_seconds=min(1, seconds-i),
                 prediction='non_snore', rms_dbfs=-30,
                 yamnet_breathing_score=0.9, yamnet_speech_score=0.01,
                 yamnet_cough_score=0.01, cough_probability=None, **overrides)
            for i in range(int(np.ceil(seconds)))]


class SleepAudioTests(unittest.TestCase):
    def test_official_yamnet_class_indexes_and_invalid_scores(self):
        scores = np.zeros((1, 521)); scores[0, 0] = .8; scores[0, 36] = .7
        row = {}; add_sound_scores(row, scores)
        self.assertEqual(row['yamnet_speech_score'], .8)
        self.assertEqual(row['yamnet_breathing_score'], .7)
        with self.assertRaises(ValueError): add_sound_scores({}, np.zeros(520))
        scores[0, 36] = np.nan
        with self.assertRaises(ValueError): add_sound_scores({}, scores)

    def test_events_allow_overlap_and_do_not_bridge_missing_time(self):
        timeline = rows(3)
        for row in timeline:
            row.update(prediction='snore', yamnet_speech_score=.8,
                       yamnet_breathing_score=.1, cough_probability=.9)
        timeline[-1].update(start_seconds=4, duration_seconds=.25)
        output = build_sound_events(timeline, cough_threshold=.51)
        for kind in ('snore', 'speech', 'cough'):
            events = [e for e in output['events'] if e['sound_type'] == kind]
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]['duration_seconds'], 2)
            self.assertEqual(events[-1]['end_seconds'], 4.25)
        self.assertFalse(output['clinical_validation'])
        self.assertNotIn('bruxism', output['supported_types'])
        self.assertNotIn('sleep_talking', output['supported_types'])
        json.dumps(output, allow_nan=False)

    def test_silence_and_missing_scores_do_not_become_sound_events(self):
        timeline = rows(2)
        timeline[0]['rms_dbfs'] = None
        timeline[1].pop('yamnet_breathing_score')
        self.assertEqual(build_sound_events(timeline)['events'], [])
        timeline[1]['cough_probability'] = .9
        timeline[1]['yamnet_cough_score'] = .01
        self.assertEqual(build_sound_events(timeline)['events'], [])
        self.assertEqual(build_sound_events(timeline, cough_threshold=.51)['events'][0]['sound_type'], 'cough')
        timeline[1]['cough_probability'] = None
        timeline[1]['yamnet_cough_score'] = .8
        self.assertEqual(build_sound_events(timeline)['events'][0]['source'], 'yamnet_review')

    def test_known_breathing_envelope_and_partial_window(self):
        sr = 4000; t = np.arange(int(65.25*sr))/sr
        signal = (.04 + .03*np.cos(2*np.pi*t/4))*np.sin(2*np.pi*600*t)
        result = breathing_rate_over_time(signal, sr, rows(65.25))
        self.assertEqual([r['duration_seconds'] for r in result['windows']], [30, 30, 5.25])
        for window in result['windows'][:2]:
            self.assertEqual(window['status'], 'estimated')
            self.assertAlmostEqual(window['breaths_per_minute'], 15, delta=.5)
        self.assertEqual(result['windows'][-1]['status'], 'insufficient_duration')
        self.assertIsNone(result['windows'][-1]['breaths_per_minute'])
        self.assertAlmostEqual(result['estimated_seconds'], 60)
        self.assertFalse(result['clinical_validation'])
        json.dumps(result, allow_nan=False)

    def test_abstains_from_silence_noise_constant_tone_and_missing_breathing_evidence(self):
        sr=4000; t=np.arange(sr*30)/sr
        for signal in (np.zeros(len(t)), .1*np.sin(2*np.pi*600*t),
                       np.random.default_rng(2).normal(0,.05,len(t))):
            result=breathing_rate_over_time(signal,sr,rows(30))
            self.assertIsNone(result['median_breaths_per_minute'])
        periodic=(.04+.03*np.cos(2*np.pi*t/4))*np.sin(2*np.pi*600*t)
        for timeline in ([], rows(30, yamnet_breathing_score_missing=True)):
            if timeline:
                for row in timeline: row.pop('yamnet_breathing_score')
            result=breathing_rate_over_time(periodic,sr,timeline)
            self.assertEqual(result['windows'][0]['status'], 'insufficient_breathing_evidence')
        for key, value in [('yamnet_speech_score',.9),('cough_probability',.9),('prediction','snore')]:
            timeline=rows(30)
            for row in timeline: row[key]=value
            self.assertIsNone(breathing_rate_over_time(periodic,sr,timeline,cough_threshold=.51)['median_breaths_per_minute'])

    def test_invalid_input_and_clipping(self):
        with self.assertRaises(ValueError): breathing_rate_over_time(np.array([np.nan]),4000,[])
        with self.assertRaises(ValueError): breathing_rate_over_time(np.zeros(100),100,[])
        result=breathing_rate_over_time(np.ones(30*4000),4000,rows(30))
        self.assertEqual(result['windows'][0]['status'],'clipped_signal')
        result=breathing_rate_over_time(np.zeros(0),4000,[])
        self.assertEqual(result['windows'],[])


if __name__ == '__main__': unittest.main()
