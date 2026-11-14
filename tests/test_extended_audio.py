import json
import unittest
import numpy as np
from audio_patterns import loudness_statistics, estimate_pitch, compare_gap_loudness, rhythm_autocorrelation, bounded_spectrogram, rhythm_over_time


class ExtendedAudioTests(unittest.TestCase):
    def test_mean_rms_weights_partial_windows_in_linear_units(self):
        result=loudness_statistics([-20,-40],[1,0.25])
        expected=(0.1+0.01*0.25)/1.25
        self.assertAlmostEqual(result['mean_rms'],expected,places=8)
        self.assertAlmostEqual(result['mean_rms_dbfs'],20*np.log10(expected),places=2)
        self.assertEqual(result['max_rms_dbfs'],-20)
        self.assertIsNone(loudness_statistics([],[])['mean_rms'])
        self.assertEqual(loudness_statistics([None],[1])['mean_rms'],0)
        self.assertIsNone(loudness_statistics([None],[1])['mean_rms_dbfs'])

    def test_pitch_tones_harmonics_silence_and_noise(self):
        t=np.arange(16000)/16000
        for hz in (80,200,400,800):
            self.assertAlmostEqual(estimate_pitch(np.sin(2*np.pi*hz*t),16000)['pitch_hz'],hz,delta=max(2,hz*0.015))
        # Strong second harmonic must not simply become the pitch.
        signal=0.6*np.sin(2*np.pi*200*t)+np.sin(2*np.pi*400*t)
        self.assertAlmostEqual(estimate_pitch(signal,16000)['pitch_hz'],200,delta=3)
        for audio in (np.zeros(16000),np.ones(16000),np.zeros(20),np.random.default_rng(3).normal(0,0.1,16000)):
            self.assertIsNone(estimate_pitch(audio,16000)['pitch_hz'])

    def test_rebound_requires_adjacent_snoring_and_real_level_rise(self):
        events=[dict(start_seconds=0,end_seconds=3),dict(start_seconds=13,end_seconds=16)]
        rows=[dict(start_seconds=i,duration_seconds=1,rms_dbfs=-30 if i<3 else -24 if i>=13 else None,
                   prediction='snore' if i<3 or i>=13 else 'non_snore') for i in range(16)]
        gaps=[dict(start_seconds=3,end_seconds=13,duration_seconds=10)]
        found=compare_gap_loudness(rows,events,gaps)
        self.assertEqual(len(found),1);self.assertEqual(found[0]['rise_db'],6)
        self.assertTrue(found[0]['is_louder'])
        events[1]['start_seconds']=14
        self.assertEqual(compare_gap_loudness(rows,events,gaps),[])

    def test_envelope_autocorrelation_finds_five_second_rhythm(self):
        sr=1000;t=np.arange(60*sr)/sr
        envelope=0.05+0.2*(np.sin(2*np.pi*t/5)>0.7)
        audio=envelope*np.sin(2*np.pi*100*t)
        result=rhythm_autocorrelation(audio,sr)
        self.assertAlmostEqual(result['dominant_period_seconds'],5,delta=0.2)
        self.assertGreater(result['autocorrelation_strength'],0.8)
        for samples in (np.zeros(sr*60),np.zeros(sr*3)):
            self.assertIsNone(rhythm_autocorrelation(samples,sr)['dominant_period_seconds'])

    def test_local_rhythm_masks_non_snoring_and_keeps_partial_window_time(self):
        sr=1000;t=np.arange(65*sr)/sr
        audio=(0.05+0.2*(np.sin(2*np.pi*t/5)>0.7))*np.sin(2*np.pi*100*t)
        timeline=[dict(start_seconds=i,duration_seconds=1,prediction='snore') for i in range(65)]
        results=rhythm_over_time(audio,sr,timeline)
        self.assertEqual([r['duration_seconds'] for r in results],[60,35])
        self.assertAlmostEqual(results[0]['dominant_period_seconds'],5,delta=0.2)
        for row in timeline:row['prediction']='non_snore'
        self.assertIsNone(rhythm_autocorrelation(audio,sr,timeline)['dominant_period_seconds'])

    def test_spectrogram_frequency_axis_and_bounded_size(self):
        sr=16000;t=np.arange(sr*3)/sr
        result=bounded_spectrogram(0.2*np.sin(2*np.pi*800*t),sr,max_columns=20)
        matrix=np.array(result['values_db'])
        self.assertLessEqual(matrix.shape[1],20)
        self.assertEqual(matrix.shape[0],128)
        hz=result['frequencies_hz'][np.argmax(matrix.mean(axis=1))]
        self.assertAlmostEqual(hz,800,delta=40)
        self.assertTrue(np.isfinite(matrix).all())
        json.dumps(bounded_spectrogram(np.zeros(sr),sr),allow_nan=False)
        self.assertEqual(bounded_spectrogram(np.zeros(10),sr)['status'],'insufficient_duration')


if __name__=='__main__':unittest.main()
