import 'dart:async';

import 'package:record/record.dart';
import 'package:sanor_mobile/capture_session.dart';

class FakeRecorder implements CaptureRecorder {
  final controller = StreamController<RecordState>.broadcast(sync: true);
  bool permission = true, failStart = false, failStop = false;
  int starts = 0, stops = 0;
  Completer<void>? gate;
  Future<void> Function()? beforeStart;
  @override
  Stream<RecordState> get states => controller.stream;
  @override
  Future<bool> hasPermission() async {
    await gate?.future;
    return permission;
  }

  @override
  Future<void> start(String path) async {
    starts++;
    await beforeStart?.call();
    if (failStart) throw StateError('start failed');
    controller.add(RecordState.record);
  }

  @override
  Future<void> pause() async => controller.add(RecordState.pause);
  @override
  Future<void> resume() async => controller.add(RecordState.record);
  @override
  Future<void> stop() async {
    stops++;
    if (failStop) throw StateError('stop failed');
    controller.add(RecordState.stop);
  }

  @override
  Future<void> dispose() => controller.close();
}
