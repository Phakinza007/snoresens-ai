import unittest
import numpy as np
from temporal_segmentation import analysis_windows,decision_mask,activity_threshold
from predict import summarize

class TemporalSegmentationTests(unittest.TestCase):
    def test_cells_cover_partial_recording_once_and_context_keeps_real_samples(self):
        audio=np.arange(37600,dtype=np.float32)
        windows=list(analysis_windows(audio,.1))
        self.assertEqual(len(windows),24)
        self.assertEqual(sum(len(cell) for _,cell,_,_ in windows),len(audio))
        self.assertEqual(len(windows[-1][1]),800)
        for at,cell,context,offset in windows:
            self.assertEqual(context.shape,(15600,))
            np.testing.assert_array_equal(context,audio[offset:offset+15600])
        self.assertEqual(windows[0][0],0)
        self.assertEqual(windows[-1][0],36800)

    def test_20ms_cells_share_model_context_but_keep_a_20ms_quiet_gap(self):
        audio=np.full(16000,.1,dtype=np.float32)
        audio[320:640]=0
        windows=list(analysis_windows(audio))
        self.assertEqual(len(windows),50)
        self.assertEqual([len(x[1]) for x in windows], [320]*50)
        self.assertEqual([x[3] for x in windows[:5]], [windows[0][3]]*5)
        levels=[None if not np.any(cell) else -20 for _,cell,_,_ in windows]
        mask=decision_mask([.99]*50,levels,.44,activity_floor=-40)
        _,events,_=summarize([.99]*50,[0]*50,[None]*50,[.02]*50,levels,.44,mask)
        self.assertEqual(events[0]['end_seconds'],.02)
        self.assertEqual(events[1]['start_seconds'],.04)

    def test_context_does_not_make_digital_silence_a_snore(self):
        self.assertEqual(decision_mask([.99,.99,.99],[None,-70,-20],.44),[False,False,True])

    def test_subsecond_non_snore_gap_splits_events_without_rounding_it_away(self):
        result,events,rows=summarize([.9,.9,.9,.1,.1,.9,.9,.9],[0]*8,[None]*8,[.1]*8,[-20]*8,.44)
        self.assertEqual(result['detected_snore_seconds'],.6)
        self.assertEqual(events,[dict(start_seconds=0.0,end_seconds=.3,duration_seconds=.3),dict(start_seconds=.5,end_seconds=.8,duration_seconds=.3)])
        self.assertEqual(rows[3]['prediction'],'non_snore')

    def test_short_audio_padding_is_not_counted_as_recorded_time(self):
        audio=np.ones(123,dtype=np.float32)
        windows=list(analysis_windows(audio))
        self.assertEqual(len(windows),1)
        self.assertEqual(len(windows[0][1]),123)
        self.assertTrue(np.all(windows[0][2][123:]==0))

    def test_low_activity_gap_is_not_inherited_from_positive_neighbor_context(self):
        levels=[-36]*10+[-15]*5+[-36]*10+[-15]*5
        floor=activity_threshold(levels)
        self.assertEqual(floor,-30)
        mask=decision_mask([.99]*30,levels,.44,activity_floor=floor)
        self.assertEqual(sum(mask),10)
        _,events,_=summarize([.99]*30,[0]*30,[None]*30,[.1]*30,levels,.44,mask)
        self.assertEqual(events,[dict(start_seconds=1.0,end_seconds=1.5,duration_seconds=.5),dict(start_seconds=2.5,end_seconds=3.0,duration_seconds=.5)])

if __name__=='__main__':unittest.main()
