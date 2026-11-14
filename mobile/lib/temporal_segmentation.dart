/// 20 ms boundary refinement; model evidence still covers 975 ms every 100 ms.
/// This spacing is not a claim of ground-truth event localization accuracy.
library;

import 'dart:math';

const sampleRate = 16000,
    hopSamples = 320,
    modelHopSamples = 1600,
    contextSamples = 15600;

class AnalysisCell {
  final int at, length, contextStart;
  const AnalysisCell(this.at, this.length, this.contextStart);
}

Iterable<AnalysisCell> analysisPlan(int length) sync* {
  for (var at = 0; at < length; at += hopSamples) {
    final size = min(hopSamples, length - at),
        parent = at ~/ modelHopSamples * modelHopSamples;
    final center = parent + min(modelHopSamples, length - parent) ~/ 2;
    yield AnalysisCell(
      at,
      size,
      max(0, min(center - contextSamples ~/ 2, length - contextSamples)),
    );
  }
}

double activityThreshold(List<double?> levels) {
  final values =
      levels.whereType<double>().where((x) => x.isFinite && x >= -80).toList()
        ..sort();
  if (values.length < 5) return -60;
  double percentile(double p) {
    final at = (values.length - 1) * p;
    return values[at.floor()] +
        (values[at.ceil()] - values[at.floor()]) * (at - at.floor());
  }

  final low = percentile(.2), high = percentile(.95);
  return max(-60, low + min(6, (high - low) / 2));
}

bool isSnore(
  double probability,
  double? level,
  double? parentLevel,
  double threshold,
  double floor,
) =>
    probability >= threshold &&
    level != null &&
    level.isFinite &&
    level >= floor &&
    parentLevel != null &&
    parentLevel.isFinite &&
    parentLevel >= floor;
