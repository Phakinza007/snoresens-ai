import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'package:flutter/services.dart';
import 'package:tflite_flutter/tflite_flutter.dart';
import 'audio_patterns.dart';
import 'wav.dart';

class SnoreResult {
  final String name;
  final Map<String,dynamic> summary;
  final List<Map<String,dynamic>> timeline;
  final List<Map<String,dynamic>> snoreEvents;
  final Map<String,dynamic> audioPatterns;
  final String? audioPath;
  SnoreResult(this.name,this.summary,this.timeline,this.snoreEvents,this.audioPatterns,{this.audioPath});
  double get seconds => (summary['recording_seconds'] as num).toDouble();
  double get snoreSeconds => (summary['detected_snore_seconds'] as num).toDouble();
  int get events => summary['snore_event_count'] as int;
  double get percent => seconds>0 ? 100*snoreSeconds/seconds : 0;
  double get minutesPerHour => seconds>0 ? snoreSeconds/seconds*60 : 0;
  double get eventsPerHour => seconds>0 ? events/seconds*3600 : 0;
  Map<String,dynamic> toJson() => {'name':name,'summary':summary,'timeline':timeline,
    'snore_events':snoreEvents,'audio_patterns':audioPatterns};
}

class SnoreEngine {
  Interpreter? _base, _head;
  late final double threshold;
  Future<void> load() async {
    try {
      _base=await Interpreter.fromAsset('assets/yamnet_base.tflite');
      _head=await Interpreter.fromAsset('assets/snore_score_head.tflite');
      final config=jsonDecode(await rootBundle.loadString('assets/mobile_metrics.json')) as Map<String,dynamic>;
      threshold=(config['threshold'] as num).toDouble();
    } catch (_) { close(); rethrow; }
  }

  Future<SnoreResult> analyze(String name, Uint8List bytes,
      {String? audioPath,double quietThresholdDbfs=-45,double minGapSeconds=10}) async {
    final audio=decodeWav(bytes);
    final timeline=<Map<String,dynamic>>[], events=<Map<String,dynamic>>[];
    final levels=<double>[];
    var snoreSeconds=0.0;
    double? eventStart;
    for(var start=0;start<audio.length;start+=16000) {
      final end=min(start+16000,audio.length);
      final frame=Float32List.sublistView(audio,start,end);
      final waveform=Float32List(15600);
      waveform.setRange(0,min(frame.length,15600),frame);
      final scores=[List<double>.filled(521,0)];
      _base!.run(waveform,scores);
      final prediction=[[0.0]];
      _head!.run(scores,prediction);
      final isSnore=prediction[0][0]>=threshold;
      final level=frameRmsDbfs(frame);
      final duration=frame.length/16000;
      final seconds=start/16000;
      timeline.add({'start_seconds':rounded(seconds),'duration_seconds':rounded(duration),
        'snore_probability':rounded(prediction[0][0],6),'rms_dbfs':level==null?null:rounded(level,2),
        'prediction':isSnore?'snore':'non_snore',
        'analysis_schema_version':1,'quiet_threshold_dbfs':quietThresholdDbfs,'min_quiet_gap_seconds':minGapSeconds,'spectral_enabled':true,
        ... (isSnore ? spectralFeatures(frame,16000) : {'dominant_frequency_hz':null,'spectral_centroid_hz':null})});
      if(isSnore) {
        eventStart??=seconds; snoreSeconds+=duration;
        if(level!=null) levels.add(level);
      } else if(eventStart!=null) {
        events.add({'start_seconds':rounded(eventStart),'end_seconds':rounded(seconds),'duration_seconds':rounded(seconds-eventStart)});
        eventStart=null;
      }
      if(timeline.length%20==0) await Future<void>.delayed(Duration.zero);
    }
    final seconds=audio.length/16000;
    if(eventStart!=null) events.add({'start_seconds':rounded(eventStart),'end_seconds':rounded(seconds),'duration_seconds':rounded(seconds-eventStart)});
    levels.sort();
    double? percentile(double fraction) {
      if(levels.isEmpty) return null;
      final position=(levels.length-1)*fraction, left=position.floor(), right=position.ceil();
      return rounded(levels[left]+(levels[right]-levels[left])*(position-left),2);
    }
    final summary=<String,dynamic>{'recording_seconds':rounded(seconds), 'detected_snore_seconds':rounded(snoreSeconds),
      'snore_percent_of_recording':rounded(100*snoreSeconds/seconds,2),'snore_event_count':events.length,
      'longest_snore_event_seconds':events.fold<double>(0,(value,event)=>max(value,(event['duration_seconds'] as num).toDouble())),
      'snore_median_rms_dbfs':percentile(0.5),'snore_p95_rms_dbfs':percentile(0.95),'threshold':threshold};
    return SnoreResult(name,summary,timeline,events,buildPatterns(timeline,events,
      quietThresholdDbfs:quietThresholdDbfs,minGapSeconds:minGapSeconds),audioPath:audioPath);
  }
  void close() { _base?.close(); _head?.close(); _base=null; _head=null; }
}
