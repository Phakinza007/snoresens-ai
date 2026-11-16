import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:sanor_mobile/recording_store.dart';
import 'package:sanor_mobile/recording_clock.dart';
import 'package:sanor_mobile/wav_parts.dart';

void main() {
  test('clock excludes pauses and duplicate events', () {
    final c = RecordingClock();
    c.record(const Duration(seconds: 1));
    c.record(const Duration(seconds: 2));
    c.pause(const Duration(seconds: 4));
    c.pause(const Duration(seconds: 5));
    c.record(const Duration(seconds: 10));
    expect(c.elapsed(const Duration(seconds: 12)), const Duration(seconds: 5));
  });
  test('durable pending recording and analysis survive restart', () async {
    final dir = await Directory.systemTemp.createTemp('snore-store-');
    addTearDown(() => dir.delete(recursive: true));
    final s = RecordingStore(dir);
    await s.save(
      RecordingEntry(
        id: 'night1',
        name: 'night',
        createdAt: DateTime.utc(2026),
        status: 'pending',
      ),
    );
    await s.saveAnalysis('night1', {
      'summary': {'recording_seconds': 1},
    });
    final reopened = RecordingStore(dir);
    expect((await reopened.list()).single.status, 'pending');
    expect(
      (await reopened.readAnalysis('night1'))['summary']['recording_seconds'],
      1,
    );
    expect(() => s.audioPath('../escape'), throwsArgumentError);
  });
  test('malformed metadata does not hide valid sessions', () async {
    final dir = await Directory.systemTemp.createTemp('snore-corrupt-');
    addTearDown(() => dir.delete(recursive: true));
    final s = RecordingStore(dir);
    await s.save(
      RecordingEntry(
        id: 'good',
        name: 'night',
        createdAt: DateTime.utc(2026),
        status: 'pending',
      ),
    );
    await File('${dir.path}/bad.record.json').writeAsString('broken');
    expect((await s.list()).length, 1);
  });
  test(
    'large WAV splits without dropping samples or reading whole file',
    () async {
      final dir = await Directory.systemTemp.createTemp('snore-wav-');
      addTearDown(() => dir.delete(recursive: true));
      final f = File('${dir.path}/sound.wav');
      final pcm = Uint8List(16000 * 2 * 3 + 246);
      for (var i = 0; i < pcm.length; i++) {
        pcm[i] = i % 251;
      }
      await f.writeAsBytes(wrapPcm(pcm, 16000, 1));
      final chunks = await wavParts(f, secondsPerPart: 1).toList();
      expect(chunks.length, 4);
      final combined = chunks.expand((x) => x.sublist(44)).toList();
      expect(combined, pcm);
      expect(chunks.last.length, 44 + 246);
    },
  );
  test('truncated or empty WAV stays invalid', () async {
    final dir = await Directory.systemTemp.createTemp('snore-invalid-');
    addTearDown(() => dir.delete(recursive: true));
    final f = File('${dir.path}/bad.wav');
    await f.writeAsBytes(wrapPcm(Uint8List(0), 16000, 1));
    await expectLater(wavParts(f).drain<void>(), throwsFormatException);
  });
  test(
    'terminated capture is found after reopening without losing raw audio',
    () async {
      final dir = await Directory.systemTemp.createTemp('recover-');
      addTearDown(() => dir.delete(recursive: true));
      final store = RecordingStore(dir);
      await store.save(
        RecordingEntry(
          id: 'night',
          name: 'night',
          createdAt: DateTime.utc(2026),
          status: 'recording',
        ),
      );
      await File(store.audioPath('night')).writeAsString('unfinished WAV');
      final reopened = RecordingStore(dir);
      await reopened.recoverInterrupted();
      expect((await reopened.list()).single.status, 'pending');
      expect(
        await File(store.audioPath('night')).readAsString(),
        'unfinished WAV',
      );
    },
  );
  test('truncated PCM and unsupported sample rates are rejected', () async {
    final dir = await Directory.systemTemp.createTemp('bad-wave-');
    addTearDown(() => dir.delete(recursive: true));
    final f = File('${dir.path}/bad.wav');
    final wav = wrapPcm(Uint8List(320), 16000, 1);
    await f.writeAsBytes(wav.sublist(0, wav.length - 2));
    await expectLater(wavParts(f).drain<void>(), throwsFormatException);
    await f.writeAsBytes(wrapPcm(Uint8List(320), 48000, 1));
    await expectLater(wavParts(f).drain<void>(), throwsFormatException);
  });
}
