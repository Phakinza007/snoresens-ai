import csv
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import soundfile as sf
from apnea_research import WINDOW_SECONDS, FEATURE_NAMES, audio_features, load_manifest, model_status, ResearchModel


class ApneaResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def manifest(self, rows):
        path=self.root/'windows.csv'
        with path.open('w',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=['audio_path','person_id','night_id','start_seconds','duration_seconds','label','split','reference','alignment_verified'])
            writer.writeheader();writer.writerows(rows)
        return path
    def rows(self):
        return [dict(audio_path=f'{split}-{person}-{label}.wav',person_id=f'{split}-{person}',night_id=f'{split}-{person}-night',
                     start_seconds=0,duration_seconds=30,label=label,split=split,reference='PSG',alignment_verified='true')
                for split in ('train','validation','test') for person in (1,2) for label in (0,1)]
    def test_manifest_clinical_reference_alignment_and_split(self):
        rows=self.rows()
        self.assertEqual(len(load_manifest(self.manifest(rows))),12)
        for key,value in [('reference','snore_dataset'),('alignment_verified','false'),('duration_seconds',1),('label',2)]:
            changed=[dict(r) for r in rows];changed[0][key]=value
            with self.assertRaises(ValueError): load_manifest(self.manifest(changed))
    def test_person_night_and_source_leakage(self):
        for key in ('person_id','night_id','audio_path'):
            rows=self.rows();rows[4][key]=rows[0][key]
            with self.assertRaises(ValueError):load_manifest(self.manifest(rows))
    def test_overlapping_source_windows_rejected(self):
        rows=self.rows();rows[1]['audio_path']=rows[0]['audio_path'];rows[1]['start_seconds']=15
        with self.assertRaises(ValueError):load_manifest(self.manifest(rows))
    def test_features_finite_and_fixed_size(self):
        for signal in (np.zeros(30*16000), np.sin(2*np.pi*200*np.arange(30*16000)/16000)):
            features=audio_features(signal)
            self.assertEqual(features.shape,(len(FEATURE_NAMES),))
            self.assertTrue(np.isfinite(features).all())
        with self.assertRaises(ValueError):audio_features(np.zeros(16000))
    def test_missing_and_corrupt_model_status(self):
        self.assertEqual(model_status(self.root)['status'],'not_trained')
        (self.root/'apnea_research.json').write_text('{}')
        self.assertEqual(model_status(self.root)['status'],'invalid_model')
    def test_exact_waveform_leakage_and_out_of_bounds_windows(self):
        from apnea_research import collect_features, read_window
        signal=np.sin(2*np.pi*200*np.arange(30*8000)/8000).astype(np.float32)
        wav=self.root/'same.wav';sf.write(wav,signal,8000)
        self.assertEqual(len(read_window(wav,0)),30*16000)
        with self.assertRaises(ValueError):read_window(wav,1)
        rows=[dict(audio_path=str(wav),start_seconds=0,split=split) for split in ('train','test')]
        with self.assertRaisesRegex(ValueError,'duplicate'):collect_features(rows)

    def test_export_parity_and_abstention(self):
        from apnea_research import save_model
        features=np.zeros(len(FEATURE_NAMES))
        config=dict(schema_version=1,feature_version=1,feature_names=FEATURE_NAMES,window_seconds=30,
                    sample_rate=16000,threshold=0.5,validation_status='research_only',target='apnea_hypopnea_window',
                    input_modality='ambient_microphone_audio',clinical_validation=False)
        save_model(self.root, np.zeros_like(features),np.ones_like(features),np.ones_like(features),0.2,config)
        model=ResearchModel(self.root)
        self.assertAlmostEqual(model.score(features),1/(1+np.exp(-0.2)),places=6)
        wav=self.root/'silent.wav';sf.write(wav,np.zeros(31*16000),16000)
        result=model.analyze(wav)
        self.assertEqual(result['windows'][0]['status'],'insufficient_signal')
        self.assertIsNone(result['windows'][0]['model_score'])
        self.assertEqual(result['windows'][1]['status'],'insufficient_duration')
        self.assertIsNone(result['risk_percent'])
        config['validation_status']='synthetic_only'
        save_model(self.root,features,np.ones_like(features),features,0,config,overwrite=True)
        with self.assertRaises(ValueError):ResearchModel(self.root)


if __name__ == '__main__':unittest.main()
