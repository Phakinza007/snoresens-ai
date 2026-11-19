import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sanor_mobile/inference.dart';
import 'package:sanor_mobile/recording_processor.dart';
import 'package:sanor_mobile/recording_store.dart';
import 'package:sanor_mobile/wav.dart';
import 'package:sanor_mobile/wav_parts.dart';

void main() {
  late Directory dir;
  late RecordingStore store;
  late RecordingEntry entry;
  setUp(() async {
    dir = await Directory.systemTemp.createTemp('processor-');
    store = RecordingStore(dir);
    entry = RecordingEntry(
      id: 'night',
      name: 'night',
      createdAt: DateTime.utc(2026),
      status: 'pending',
    );
    await store.save(entry);
    await File(store.audioPath(entry.id))
        .writeAsBytes(wrapPcm(Uint8List(16000 * 2 * 601), 16000, 1));
  });
  tearDown(() => dir.delete(recursive: true));
  Future<SnoreResult> analyze(
    String name,
    Uint8List bytes, {
    String? audioPath,
    bool Function()? shouldContinue,
  }) async {
    final seconds = decodeWav(bytes).length / 16000;
    expect(seconds, lessThanOrEqualTo(300));
    return SnoreResult(
      name,
      {
        'recording_seconds': seconds,
        'detected_snore_seconds': seconds / 4,
        'snore_event_count': 1,
      },
      [],
      [],
      {},
      audioPath: audioPath,
    );
  }

  test('long recording retains its tail and a duration-weighted summary after reopening', () async {
    final job = RecordingProcessor(
      store,
      analyze: analyze,
      foreground: () => true,
      onProgress: (_) {},
    );
    expect(await job.process(entry), true);
    final list = await RecordingStore(dir).list();
    final parent = list.singleWhere((e) => e.id == 'night');
    expect(parent.status, 'processed');
    expect(parent.summary!['recording_seconds'], 601);
    expect(parent.summary!['detected_snore_seconds'], 150.25);
    expect(parent.summary!['snore_percent_of_recording'], 25);
    expect(parent.summary!['part_count'], 3);
    expect(list.where((e) => e.status == 'done').length, 3);
    final result = SnoreResult.fromJson(
      await store.readAnalysis('night_p3'),
      audioPath: store.audioPath('night_p3'),
    );
    expect(result.seconds, 1);
    expect(result.audioPath, store.audioPath('night_p3'));
    expect(await File(store.audioPath('night')).exists(), true);
  });
  test('leaving foreground keeps completed parts; retry only analyzes unfinished parts', () async {
    var foreground = true;
    final calls = <String>[];
    final job = RecordingProcessor(
      store,
      foreground: () => foreground,
      onProgress: (_) {},
      analyze: (name, bytes, {audioPath, shouldContinue}) async {
        calls.add(name);
        if (calls.length == 2) {
          foreground = false;
          throw const AnalysisDeferred();
        }
        return analyze(
          name,
          bytes,
          audioPath: audioPath,
          shouldContinue: shouldContinue,
        );
      },
    );
    expect(await job.process(entry), false);
    expect(
      (await store.list()).singleWhere((e) => e.id == 'night').status,
      'pending',
    );
    expect((await store.list()).where((e) => e.status == 'done').length, 1);
    foreground = true;
    expect(await job.process(entry), true);
    expect(calls.where((name) => name.endsWith('ส่วน 1')).length, 1);
    expect(calls.where((name) => name.endsWith('ส่วน 2')).length, 2);
  });
  test(
    'invalid source stays on disk with an error and retryable status',
    () async {
      await File(store.audioPath('night')).writeAsString('not a wav');
      final job = RecordingProcessor(
        store,
        analyze: analyze,
        foreground: () => true,
        onProgress: (_) {},
      );
      await expectLater(job.process(entry), throwsFormatException);
      final parent = (await store.list()).single;
      expect(parent.status, 'pending');
      expect(parent.error, isNotEmpty);
      expect(await File(store.audioPath('night')).readAsString(), 'not a wav');
    },
  );
  test(
    'saved part with broken analysis is rebuilt from the preserved original',
    () async {
      var calls = 0;
      final job = RecordingProcessor(
        store,
        foreground: () => true,
        onProgress: (_) {},
        analyze: (name, bytes, {audioPath, shouldContinue}) async {
          calls++;
          return analyze(name, bytes, audioPath: audioPath);
        },
      );
      await job.process(entry);
      expect(calls, 3);
      await File('${dir.path}/night_p2.analysis.json').writeAsString('broken');
      await job.process(entry);
      expect(calls, 4);
      expect(
        SnoreResult.fromJson(await store.readAnalysis('night_p2')).seconds,
        300,
      );
    },
  );
  test('explicit reanalysis recomputes completed parts instead of using the resume cache', () async {
    var calls = 0;
    final job = RecordingProcessor(
      store,
      foreground: () => true,
      onProgress: (_) {},
      analyze: (name, bytes, {audioPath, shouldContinue}) async {
        calls++;
        return analyze(
          name,
          bytes,
          audioPath: audioPath,
          shouldContinue: shouldContinue,
        );
      },
    );
    await job.process(entry);
    expect(calls, 3);
    await job.process(entry);
    expect(calls, 3);
    await job.process(entry, force: true);
    expect(calls, 6);
  });
}
