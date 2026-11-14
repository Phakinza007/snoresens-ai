from pathlib import Path
import tempfile
import unittest
import numpy as np
from train_apnea import choose_threshold, evaluate_windows, fit_baseline
from apnea_research import FEATURE_NAMES, ResearchModel


class ApneaTrainingTests(unittest.TestCase):
    def test_threshold_uses_supplied_validation_predictions(self):
        threshold=choose_threshold(np.array([0,0,1,1]),np.array([0.1,0.2,0.6,0.8]))
        self.assertGreater(threshold,0.2)
        self.assertLessEqual(threshold,0.6)
        with self.assertRaises(ValueError):choose_threshold(np.array([1,1]),np.array([0.5,0.6]))
    def test_threshold_matches_brute_force_with_ties_and_extreme_scores(self):
        rng=np.random.default_rng(7)
        for _ in range(20):
            y=np.array([0,1]*25)
            scores=rng.choice([0,0.1,0.2,0.5,0.9,1.0],len(y))
            candidates=np.unique(np.clip(np.concatenate(([0.5],scores)),1e-9,1-1e-9))
            expected=max(((float((scores[y==1]>=t).mean())+float((scores[y==0]<t).mean()))/2,
                          float((scores[y==0]<t).mean()),float(t)) for t in candidates)[2]
            self.assertEqual(choose_threshold(y,scores),expected)

    def test_window_metrics_use_recorded_scored_duration(self):
        result=evaluate_windows(np.array([0,0,1,1]),np.array([0.8,0.1,0.9,0.2]),0.5,
                                ['a','a','b','b'])
        self.assertEqual(result['recall'],0.5)
        self.assertEqual(result['specificity'],0.5)
        self.assertEqual(result['false_positive_windows_per_scored_hour'],30)
        self.assertIsNone(result['per_person']['a']['recall'])
    def test_portable_model_matches_training_scores_and_stays_synthetic(self):
        rng=np.random.default_rng(42)
        rows=[];features=[]
        for split in ('train','validation','test'):
            for person in range(2):
                for label in (0,1):
                    rows.append(dict(split=split,person_id=f'{split}-{person}',label=label))
                    features.append(rng.normal(0,0.1,len(FEATURE_NAMES))+label*2)
        with tempfile.TemporaryDirectory() as folder:
            result=fit_baseline(rows,np.array(features),Path(folder),synthetic=True,manifest_sha256='test')
            model=ResearchModel(Path(folder),allow_synthetic=True)
            self.assertEqual(model.config['validation_status'],'synthetic_only')
            expected=result.pop('test_scores')
            actual=[model.score(x) for row,x in zip(rows,features) if row['split']=='test']
            np.testing.assert_allclose(actual,expected,rtol=1e-10)
            self.assertFalse(model.config['clinical_validation'])
            self.assertNotIn('risk_percent',result['test_metrics'])


if __name__ == '__main__':unittest.main()
