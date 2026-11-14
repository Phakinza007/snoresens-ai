"""Non-overlapping 100 ms decisions from overlapping 975 ms model contexts.

Decision spacing is not a claim of 100 ms ground-truth event localization.
"""
import math
import numpy as np

SAMPLE_RATE=16000
CONTEXT_SAMPLES=15600

def analysis_windows(audio: np.ndarray,hop_seconds: float=.1):
    if not math.isfinite(hop_seconds) or not .05<=hop_seconds<=1:
        raise ValueError('Analysis hop must be between 0.05 and 1 second')
    hop=round(hop_seconds*SAMPLE_RATE)
    for at in range(0,len(audio),hop):
        cell=audio[at:min(at+hop,len(audio))]
        center=at+len(cell)//2
        start=max(0,min(center-CONTEXT_SAMPLES//2,len(audio)-CONTEXT_SAMPLES))
        context=np.zeros(CONTEXT_SAMPLES,dtype=np.float32)
        data=audio[start:start+CONTEXT_SAMPLES];context[:len(data)]=data
        yield at,cell,context,start

def activity_threshold(levels):
    finite=[x for x in levels if x is not None and math.isfinite(x) and x>=-80]
    if len(finite)<5:return -60.0
    low,high=np.percentile(finite,[20,95])
    return max(-60.0,float(low+min(6.0,(high-low)/2)))

def decision_mask(probabilities,levels,threshold,*,activity_floor=None):
    floor=-60.0 if activity_floor is None else activity_floor
    return [p>=threshold and level is not None and level>=floor
            for p,level in zip(probabilities,levels,strict=True)]
