import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'package:flutter_test/flutter_test.dart';
import 'package:sanor_mobile/audio_patterns.dart';

void main() {
  test('Python parity fixtures', () {
    final fixture = jsonDecode(File('test/fixtures/audio_patterns.json').readAsStringSync()) as Map<String, dynamic>;
    final rows = (fixture['timeline'] as List).cast<Map<String, dynamic>>();
    final events = (fixture['events'] as List).cast<Map<String, dynamic>>();
    final result = buildPatterns(rows, events);
    expect(result['quiet_gaps'], fixture['expected']['quiet_gaps']);
    expect(result['rhythm_summary'], fixture['expected']['rhythm_summary']);
  });
  test('tones, silence, DC, and partial frames', () {
    for (final hz in [200.0, 800.0]) {
      final samples = List<double>.generate(16000, (i) => sin(2*pi*hz*i/16000));
      expect(spectralFeatures(samples, 16000)['dominant_frequency_hz'], closeTo(hz, 1));
      expect(spectralFeatures(samples, 16000)['spectral_centroid_hz'], closeTo(hz, 1));
    }
    for (final frame in [List<double>.filled(16000, 0), List<double>.filled(16000, 1), [0.1]]) {
      expect(spectralFeatures(frame, 16000)['dominant_frequency_hz'], isNull);
    }
    expect(frameRmsDbfs([0.1, -0.1]), closeTo(-20, 0.1));
    expect(frameRmsDbfs([0, 0]), isNull);
  });
  test('quiet settings and short rhythm', () {
    expect(() => detectQuietGaps([], [], minGapSeconds:0), throwsArgumentError);
    expect(summarizeRhythm([{'start_seconds':0}, {'start_seconds':5}])['interval_cv'], isNull);
  });
}
