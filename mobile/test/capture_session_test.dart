import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:record/record.dart';

import 'helpers/fake_recorder.dart';

import 'package:sanor_mobile/capture_session.dart';
import 'package:sanor_mobile/recording_store.dart';

void main() {
  late Directory dir;
  late RecordingStore store;
  late FakeRecorder recorder;
  late CaptureSession session;
  setUp(() async {
    dir = await Directory.systemTemp.createTemp('capture-');
    store = RecordingStore(dir);
    recorder = FakeRecorder();
    session = CaptureSession(store, recorder: recorder, protect: (_) async {});
  });
  tearDown(() async {
    await session.close();
    await dir.delete(recursive: true);
  });
  test(
    'permission refusal does not start microphone or create a session',
    () async {
      recorder.permission = false;
      await session.start();
      expect(recorder.starts, 0);
      expect(session.active, false);
      expect(await store.list(), isEmpty);
      expect(session.message, contains('Settings'));
    },
  );
  test('rapid start taps start exactly one durable recording', () async {
    recorder.gate = Completer<void>();
    recorder.beforeStart = () async =>
        expect((await store.list()).single.status, 'recording');
    final first = session.start();
    await session.start();
    recorder.gate!.complete();
    await first;
    expect(recorder.starts, 1);
    expect(session.active, true);
    expect(session.paused, false);
    final pending = await session.stop();
    expect(pending!.status, 'pending');
    expect((await store.list()).single.status, 'pending');
    expect(session.active, false);
  });
  test('native interruption events update pause state and allow manual continuation', () async {
    await session.start();
    recorder.controller.add(RecordState.pause);
    expect(session.paused, true);
    final pausedTime = session.elapsed;
    await Future<void>.delayed(const Duration(milliseconds: 15));
    expect(session.elapsed, pausedTime);
    await session.togglePause();
    expect(session.paused, false);
    await session.togglePause();
    expect(session.paused, true);
    recorder.controller.add(RecordState.record);
    expect(session.paused, false);
  });
  test('start failure preserves a discoverable pending entry and the original error', () async {
    recorder.failStart = true;
    await session.start();
    expect(session.active, false);
    expect((await store.list()).single.status, 'pending');
    expect(session.message, contains('start failed'));
  });
  test('failed cleanup retains controls until native stop succeeds', () async {
    recorder.failStart = true;
    recorder.failStop = true;
    await session.start();
    expect(session.active, true);
    expect(session.message, contains('start failed'));
    recorder.failStop = false;
    expect(await session.stop(), isNotNull);
    expect(session.active, false);
  });
  test('failed stop keeps the take accessible for retry', () async {
    await session.start();
    recorder.failStop = true;
    expect(await session.stop(), isNull);
    expect(session.active, true);
    recorder.failStop = false;
    expect(await session.stop(), isNotNull);
    expect(session.active, false);
  });
  test(
    'native stop freezes clock and does not resume a stopped take',
    () async {
      await session.start();
      recorder.controller.add(RecordState.stop);
      expect(session.stopped, true);
      await session.togglePause();
      expect(session.paused, true);
      expect(await session.stop(), isNotNull);
      expect(recorder.stops, 0);
    },
  );
  test('native policy resumes eligible interruptions and pauses after route changes', () {
    expect(captureConfig.audioInterruption, AudioInterruptionMode.pauseResume);
    expect(captureConfig.audioRouteChange, AudioRouteChangeMode.pause);
    expect(captureConfig.iosConfig.categoryOptions, isEmpty);
  });
}
