"""Experimental 200 ms acoustic verifier. Not a timestamp-trained snore model."""
import numpy as np
from scipy.signal import stft
RATE=16000
SIZE=3200
# Forty fixed log-spaced frequency bands. Relative spectral power removes gain.
EDGES=np.geomspace(40,7600,41)
FREQ=np.fft.rfftfreq(512,1/RATE)
BANDS=[np.flatnonzero((FREQ>=lo)&(FREQ<hi)) for lo,hi in zip(EDGES[:-1],EDGES[1:])]
def local_window(audio,center):
 start=max(0,min(int(center)-SIZE//2,len(audio)-SIZE))
 x=np.zeros(SIZE,dtype=np.float32);data=audio[start:start+SIZE];x[:len(data)]=data
 return x
def local_features(audio):
 x=np.asarray(audio,dtype=np.float64);x=x-x.mean()
 if np.max(np.abs(x))>0:x=x/np.max(np.abs(x))
 _,_,s=stft(x,fs=RATE,window='hann',nperseg=400,noverlap=240,nfft=512,boundary=None,padded=False)
 power=np.abs(s)**2
 bands=np.stack([power[ids].sum(axis=0) if len(ids) else np.zeros(power.shape[1]) for ids in BANDS])
 relative=bands/(bands.sum(axis=0,keepdims=True)+1e-12)
 log=np.log(np.maximum(relative,1e-8))
 return np.r_[log.mean(axis=1),log.std(axis=1)].astype(np.float32)

def balanced_file_weights(labels,weights):
 labels=np.asarray(labels);result=np.asarray(weights,dtype=float).copy()
 for label in (0,1):
  selected=labels==label;total=result[selected].sum()
  if total<=0:raise ValueError('Both classes need positive weight')
  result[selected]*=len(labels)/(2*total)
 return result
