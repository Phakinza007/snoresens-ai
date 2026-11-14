/// Local measurements shared by inference, exports, and timeline views.
library;

import 'dart:math';
import 'dart:typed_data';

double rounded(double value, [int digits = 3]) =>
    double.parse(value.toStringAsFixed(digits));
double? median(List<double> values) {
  if (values.isEmpty) return null;
  final sorted = [...values]..sort();
  final middle = sorted.length ~/ 2;
  return sorted.length.isOdd
      ? sorted[middle]
      : (sorted[middle - 1] + sorted[middle]) / 2;
}

double? frameRmsDbfs(List<double> frame) {
  if (frame.isEmpty) return null;
  final energy = frame.fold<double>(0, (sum, x) => sum + x * x) / frame.length;
  return energy > 0 ? 10 * log(energy) / ln10 : null;
}

Map<String, double?> spectralFeatures(List<double> frame, int sampleRate) {
  const missing = <String, double?>{
    'dominant_frequency_hz': null,
    'spectral_centroid_hz': null,
  };
  if (frame.length < 4 || sampleRate <= 0 || frame.any((x) => !x.isFinite)) {
    return missing;
  }
  final mean = frame.reduce((a, b) => a + b) / frame.length;
  if (frame.every((x) => (x - mean).abs() <= 1e-12)) return missing;
  var size = 1;
  while (size < frame.length) {
    size <<= 1;
  }
  final real = Float64List(size), imag = Float64List(size);
  for (var i = 0; i < frame.length; i++) {
    real[i] =
        (frame[i] - mean) * 0.5 * (1 - cos(2 * pi * i / (frame.length - 1)));
  }
  // In-place radix-2 FFT; zero padding matches Python's next-power-of-two FFT.
  for (var i = 1, j = 0; i < size; i++) {
    var bit = size >> 1;
    while ((j & bit) != 0) {
      j ^= bit;
      bit >>= 1;
    }
    j ^= bit;
    if (i < j) {
      final temp = real[i];
      real[i] = real[j];
      real[j] = temp;
    }
  }
  for (var length = 2; length <= size; length <<= 1) {
    final angle = -2 * pi / length, wr = cos(-2 * pi / length), wi = sin(angle);
    for (var start = 0; start < size; start += length) {
      var ar = 1.0, ai = 0.0;
      for (var j = 0; j < length ~/ 2; j++) {
        final even = start + j, odd = even + length ~/ 2;
        final br = real[odd] * ar - imag[odd] * ai,
            bi = real[odd] * ai + imag[odd] * ar;
        real[odd] = real[even] - br;
        imag[odd] = imag[even] - bi;
        real[even] += br;
        imag[even] += bi;
        final next = ar * wr - ai * wi;
        ai = ar * wi + ai * wr;
        ar = next;
      }
    }
  }
  var total = 0.0, weighted = 0.0, peak = -1.0, peakBin = 0;
  for (var i = 1; i <= size ~/ 2; i++) {
    final magnitude = sqrt(real[i] * real[i] + imag[i] * imag[i]);
    total += magnitude;
    weighted += magnitude * i * sampleRate / size;
    if (magnitude > peak) {
      peak = magnitude;
      peakBin = i;
    }
  }
  if (total <= 1e-12) return missing;
  return {
    'dominant_frequency_hz': rounded(peakBin * sampleRate / size),
    'spectral_centroid_hz': rounded(weighted / total),
  };
}

List<Map<String, dynamic>> detectQuietGaps(
  List<Map<String, dynamic>> timeline,
  List<Map<String, dynamic>> events, {
  double quietThresholdDbfs = -45,
  double minGapSeconds = 10,
}) {
  if (!quietThresholdDbfs.isFinite ||
      quietThresholdDbfs > 0 ||
      !minGapSeconds.isFinite ||
      minGapSeconds <= 0) {
    throw ArgumentError('Invalid quiet gap settings');
  }
  final sorted = [...events]
    ..sort(
      (a, b) =>
          (a['start_seconds'] as num).compareTo(b['start_seconds'] as num),
    );
  final gaps = <Map<String, dynamic>>[];
  double? start, end;
  var preceding = -1;
  void finish() {
    if (start == null || end == null || end - start + 1e-6 < minGapSeconds) {
      return;
    }
    while (preceding + 1 < sorted.length &&
        (sorted[preceding + 1]['start_seconds'] as num) <= start) {
      preceding++;
    }
    if (preceding >= 0 &&
        preceding < sorted.length - 1 &&
        (sorted[preceding]['end_seconds'] as num) <= start + 1e-6 &&
        end <= (sorted[preceding + 1]['start_seconds'] as num) + 1e-6) {
      gaps.add({
        'start_seconds': rounded(start),
        'end_seconds': rounded(end),
        'duration_seconds': rounded(end - start),
      });
    }
  }

  for (final row in timeline) {
    final t = (row['start_seconds'] as num).toDouble(),
        duration = (row['duration_seconds'] as num).toDouble();
    final level = (row['rms_dbfs'] as num?)?.toDouble();
    final quiet =
        row['prediction'] != 'snore' &&
        (level == null || level.isFinite && level <= quietThresholdDbfs);
    if (end != null && (t - end).abs() > 1e-6) {
      finish();
      start = end = null;
    }
    if (quiet) {
      start ??= t;
      end = t + duration;
    } else {
      finish();
      start = end = null;
    }
  }
  finish();
  return gaps;
}

Map<String, dynamic> summarizeRhythm(List<Map<String, dynamic>> events) {
  final starts =
      events.map((e) => (e['start_seconds'] as num).toDouble()).toList()
        ..sort();
  final intervals = [
    for (var i = 1; i < starts.length; i++) starts[i] - starts[i - 1],
  ];
  final mean = intervals.isEmpty
      ? null
      : intervals.reduce((a, b) => a + b) / intervals.length;
  final std = intervals.length < 2
      ? null
      : sqrt(
          intervals.fold<double>(0, (sum, x) => sum + pow(x - mean!, 2)) /
              intervals.length,
        );
  return {
    'interval_count': intervals.length,
    'mean_start_interval_seconds': mean == null ? null : rounded(mean, 6),
    'std_start_interval_seconds': std == null ? null : rounded(std, 6),
    'interval_cv': std == null || mean == null || mean <= 0
        ? null
        : rounded(std / mean, 6),
  };
}

Map<String, dynamic> buildPatterns(
  List<Map<String, dynamic>> timeline,
  List<Map<String, dynamic>> events, {
  double quietThresholdDbfs = -45,
  double minGapSeconds = 10,
}) {
  double? featureMedian(String key) {
    final values = timeline
        .where((r) => r['prediction'] == 'snore' && r[key] != null)
        .map((r) => (r[key] as num).toDouble())
        .toList();
    final value = median(values);
    return value == null ? null : rounded(value);
  }

  return {
    'schema_version': 1,
    'config': {
      'quiet_threshold_dbfs': quietThresholdDbfs,
      'min_quiet_gap_seconds': minGapSeconds,
      'window_seconds': timeline.isEmpty
          ? null
          : (timeline.first['analysis_hop_seconds'] ??
                timeline.first['duration_seconds']),
      'spectral_enabled': true,
      'frequency_method':
          'mean-removed Hann rFFT magnitude; DC excluded; next-power-of-two padding',
      'rhythm_method':
          'consecutive snoring-segment start intervals; population std',
    },
    'quiet_gaps': detectQuietGaps(
      timeline,
      events,
      quietThresholdDbfs: quietThresholdDbfs,
      minGapSeconds: minGapSeconds,
    ),
    'frequency_summary': {
      'median_dominant_frequency_hz': featureMedian('dominant_frequency_hz'),
      'median_spectral_centroid_hz': featureMedian('spectral_centroid_hz'),
    },
    'rhythm_summary': summarizeRhythm(events),
  };
}
