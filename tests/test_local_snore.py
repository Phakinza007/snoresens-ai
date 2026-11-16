import unittest
import numpy as np
from local_snore import local_features,local_window,balanced_file_weights
class LocalSnoreTests(unittest.TestCase):
 def test_silence_is_finite_and_loudness_does_not_change_shape(self):
  self.assertTrue(np.isfinite(local_features(np.zeros(3200))).all())
  t=np.arange(3200)/16000; x=np.sin(2*np.pi*120*t)
  np.testing.assert_allclose(local_features(x),local_features(x*.1),atol=.002)
 def test_balancing_respects_file_weights_even_with_many_negative_windows(self):
  y=np.array([1,1]+[0]*20);w=np.array([1,1]+[.1]*20)
  result=balanced_file_weights(y,w)
  self.assertAlmostEqual(result[y==0].sum(),result[y==1].sum())
 def test_padding_and_center_are_exact(self):
  a=np.arange(16000,dtype=np.float32)
  np.testing.assert_array_equal(local_window(a,8000),a[6400:9600])
  self.assertEqual(len(local_window(a[:123],0)),3200)
 def test_different_spectra_are_distinct(self):
  t=np.arange(3200)/16000
  self.assertGreater(np.linalg.norm(local_features(np.sin(2*np.pi*120*t))-local_features(np.sin(2*np.pi*1200*t))),1)
