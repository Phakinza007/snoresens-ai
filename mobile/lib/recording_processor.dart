import 'dart:io';
import 'dart:typed_data';

import 'inference.dart';
import 'recording_store.dart';
import 'wav_parts.dart';

typedef RecordingAnalyzer = Future<SnoreResult> Function(
  String name,
  Uint8List bytes, {
  String? audioPath,
  bool Function()? shouldContinue,
});

/// Holds at most one five-minute waveform/result at a time; completed parts survive restarts.
class RecordingProcessor {
  final RecordingStore store;
  final RecordingAnalyzer analyze;
  final bool Function() foreground;
  final void Function(int part) onProgress;
  RecordingProcessor(
    this.store, {
    required this.analyze,
    required this.foreground,
    required this.onProgress,
  });

  Future<bool> process(RecordingEntry entry) async {
    if (entry.parentId != null) {
      throw ArgumentError('Process the original recording');
    }
    final existing = {for (final e in await store.list()) e.id: e};
    final summaries = <Map<String, dynamic>>[];
    var index = 0;
    await store.save(entry.copy(status: 'processing'));
    try {
      await for (final bytes in wavParts(File(store.audioPath(entry.id)))) {
        if (!foreground()) throw const AnalysisDeferred();
        index++;
        onProgress(index);
        final id = '${entry.id}_p$index';
        final previous = existing[id];
        if (previous?.status == 'done' && previous?.summary != null) {
          try {
            SnoreResult.fromJson(await store.readAnalysis(id));
            if (await File(store.audioPath(id)).exists()) {
              summaries.add(previous!.summary!);
              continue;
            }
          } catch (_) {
            /* Rebuild an incomplete saved part from the original. */
          }
        }
        final part = RecordingEntry(
          id: id,
          name: '${entry.name} · ส่วน $index',
          createdAt: entry.createdAt.add(Duration(microseconds: index)),
          status: 'pending',
          parentId: entry.id,
        );
        await store.save(part);
        await File(store.audioPath(id)).writeAsBytes(bytes, flush: true);
        final result = await analyze(
          part.name,
          bytes,
          audioPath: store.audioPath(id),
          shouldContinue: foreground,
        );
        if (!foreground()) throw const AnalysisDeferred();
        await store.saveAnalysis(id, result.toJson());
        await store.save(part.copy(status: 'done', summary: result.summary));
        summaries.add(result.summary);
      }
      final total = summaries.fold<double>(
        0,
        (v, s) => v + (s['recording_seconds'] as num).toDouble(),
      );
      final snore = summaries.fold<double>(
        0,
        (v, s) => v + (s['detected_snore_seconds'] as num).toDouble(),
      );
      await store.save(
        entry.copy(
          status: 'processed',
          summary: {
            'recording_seconds': total,
            'detected_snore_seconds': snore,
            'snore_percent_of_recording': total > 0 ? 100 * snore / total : 0,
            'part_count': summaries.length,
            'part_duration_seconds': 300,
            'snore_event_count_by_part': summaries.fold<int>(
              0,
              (v, s) => v + (s['snore_event_count'] as num).toInt(),
            ),
            'events_may_split_at_part_boundaries': true,
            'model_version': summaries.first['model_version'],
          },
        ),
      );
      return true;
    } on AnalysisDeferred {
      await store.save(
        entry.copy(
          status: 'pending',
          error: 'พักการวิเคราะห์ เปิดแอปแล้วกดวิเคราะห์ต่อ',
        ),
      );
      return false;
    } catch (error) {
      await store.save(entry.copy(status: 'pending', error: '$error'));
      rethrow;
    }
  }
}
