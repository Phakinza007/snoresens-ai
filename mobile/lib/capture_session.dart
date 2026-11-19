import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:record/record.dart';

import 'recording_clock.dart';
import 'recording_store.dart';

const captureConfig = RecordConfig(
  encoder: AudioEncoder.wav,
  sampleRate: 16000,
  numChannels: 1,
  autoGain: false,
  echoCancel: false,
  noiseSuppress: false,
  audioInterruption: AudioInterruptionMode.pauseResume,
  audioRouteChange: AudioRouteChangeMode.pause,
  iosConfig: IosRecordConfig(categoryOptions: []),
);

double normalizeAmplitude(double dbfs) {
  if (!dbfs.isFinite || dbfs <= -65) return 0;
  return ((dbfs + 65) / 60).clamp(0.0, 1.0);
}

/// The native plugin owns the audio session, including background interruptions.
abstract interface class CaptureRecorder {
  Stream<RecordState> get states;
  Stream<double> get levels;
  Future<bool> hasPermission();
  Future<void> start(String path);
  Future<void> pause();
  Future<void> resume();
  Future<void> stop();
  Future<void> dispose();
}

class NativeCaptureRecorder implements CaptureRecorder {
  final _recorder = AudioRecorder();
  @override
  Stream<RecordState> get states => _recorder.onStateChanged();
  @override
  Stream<double> get levels => _recorder
      .onAmplitudeChanged(const Duration(milliseconds: 120))
      .map((amp) => normalizeAmplitude(amp.current));
  @override
  Future<bool> hasPermission() => _recorder.hasPermission();
  @override
  Future<void> start(String path) => _recorder.start(captureConfig, path: path);
  @override
  Future<void> pause() => _recorder.pause();
  @override
  Future<void> resume() => _recorder.resume();
  @override
  Future<void> stop() async {
    try {
      await _recorder.stop();
    } finally {
      await _restorePlaybackSession();
    }
  }

  Future<void> _restorePlaybackSession() async {
    try {
      await _recorder.ios?.setAudioSessionCategory(
        category: IosAudioCategory.playback,
        options: const [],
      );
      await _recorder.ios?.setAudioSessionActive(false);
    } catch (_) {
      /* Keep stop successful even if iOS rejects audio session handoff. */
    }
  }

  @override
  Future<void> dispose() async {
    try {
      await _recorder.dispose();
    } finally {
      await _restorePlaybackSession();
    }
  }
}

class CaptureSession extends ChangeNotifier {
  final RecordingStore store;
  final CaptureRecorder recorder;
  final Future<void> Function(String) protect;
  CaptureSession(
    this.store, {
    CaptureRecorder? recorder,
    Future<void> Function(String)? protect,
  }) : recorder = recorder ?? NativeCaptureRecorder(),
       protect = protect ?? _protect {
    _sub = this.recorder.states.listen(
      _state,
      onError: (Object error) {
        clock.pause(_watch.elapsed);
        paused = true;
        message = 'ไมโครโฟนขัดข้อง กรุณากดจบเพื่อเก็บไฟล์: $error';
        _emit();
      },
    );
  }
  StreamSubscription<RecordState>? _sub;
  StreamSubscription<double>? _levelSub;
  Timer? _ticker;
  final _watch = Stopwatch()..start();
  RecordingClock clock = RecordingClock();
  RecordingEntry? entry;
  RecordState? _lastState;
  List<double> levels = List.filled(46, 0);
  bool paused = false, changing = false, stopped = false, _closed = false;
  String message = 'พร้อมบันทึก';
  bool get active => entry != null;
  Duration get elapsed => clock.elapsed(_watch.elapsed);
  void _emit() {
    if (!_closed) notifyListeners();
  }

  void _resetLevels() {
    if (levels.any((v) => v != 0)) levels = List.filled(46, 0);
  }

  void _pushLevel(double value) {
    if (!active || paused || stopped || _closed || !value.isFinite) return;
    levels = [...levels.skip(1), value.clamp(0.0, 1.0)];
    _emit();
  }

  void _state(RecordState state) {
    if (!active || _closed) return;
    _lastState = state;
    stopped = state == RecordState.stop;
    if (state == RecordState.record) {
      paused = false;
      clock.record(_watch.elapsed);
      message = 'กำลังรับเสียง · ล็อกหน้าจอได้';
    } else {
      clock.pause(_watch.elapsed);
      paused = true;
      _resetLevels();
      message = state == RecordState.pause
          ? 'พักการอัด · หากมีสายโทรเข้า รอให้สายจบแล้วตรวจสถานะ'
          : 'ระบบหยุดรับเสียง · กดจบเพื่อเก็บไฟล์';
    }
    _emit();
  }

  Future<void> start() async {
    if (active || changing || _closed) return;
    changing = true;
    _emit();
    try {
      if (!await recorder.hasPermission()) {
        message = 'กรุณาอนุญาตไมโครโฟนใน Settings';
        return;
      }
      if (_closed) return;
      final now = DateTime.now();
      final e = RecordingEntry(
        id: 'night_${now.microsecondsSinceEpoch}',
        name: 'บันทึก ${now.toLocal().toString().substring(0, 16)}',
        createdAt: now,
        status: 'recording',
      );
      // Persist before starting the microphone, so a terminated take is discoverable.
      await store.save(e);
      entry = e;
      _lastState = null;
      clock = RecordingClock();
      try {
        await protect(store.root.path);
        if (_closed) throw StateError('Capture session closed');
        await recorder.start(store.audioPath(e.id));
        await protect(store.audioPath(e.id));
        if (_closed) throw StateError('Capture session closed');
        if (_lastState == null) _state(RecordState.record);
        await _levelSub?.cancel();
        _levelSub = recorder.levels.listen(
          _pushLevel,
          onError: (_) {},
        );
        _ticker = Timer.periodic(const Duration(seconds: 1), (_) => _emit());
      } catch (error) {
        var cleaned = false;
        try {
          await recorder.stop();
          cleaned = true;
        } catch (_) {
          /* Preserve controls if native capture could still be active. */
        }
        if (cleaned) {
          entry = null;
        } else {
          paused = true;
          clock.pause(_watch.elapsed);
        }
        await store.save(
          e.copy(
            status: cleaned ? 'pending' : 'recording',
            error: 'เริ่มอัดไม่สำเร็จ: $error',
          ),
        );
        rethrow;
      }
    } catch (error) {
      message = 'เริ่มบันทึกไม่ได้: $error';
    } finally {
      changing = false;
      _emit();
    }
  }

  static Future<void> _protect(String path) async {
    if (defaultTargetPlatform == TargetPlatform.iOS) {
      await const MethodChannel('snoresens/files')
          .invokeMethod<void>('protect', {'path': path});
    }
  }

  Future<void> togglePause() async {
    if (!active || changing || stopped || _closed) return;
    changing = true;
    _emit();
    try {
      if (paused) {
        await recorder.resume();
        _state(RecordState.record);
      } else {
        await recorder.pause();
        _state(RecordState.pause);
      }
    } catch (error) {
      message = 'เปลี่ยนสถานะไม่ได้: $error';
    } finally {
      changing = false;
      _emit();
    }
  }

  Future<RecordingEntry?> stop() async {
    if (!active || changing || _closed) return null;
    changing = true;
    _emit();
    final e = entry!;
    try {
      if (!stopped) {
        await recorder.stop();
        stopped = true;
      }
      clock.pause(_watch.elapsed);
      _ticker?.cancel();
      await _levelSub?.cancel();
      _levelSub = null;
      _resetLevels();
      final pending = e.copy(status: 'pending');
      await store.save(pending);
      entry = null;
      message = 'เก็บเสียงแล้ว พร้อมวิเคราะห์';
      return pending;
    } catch (error) {
      message = 'จบการอัดไม่ได้ ลองกดจบอีกครั้ง: $error';
      return null;
    } finally {
      changing = false;
      _emit();
    }
  }

  Future<void> close() async {
    if (_closed) return;
    _closed = true;
    _ticker?.cancel();
    await _levelSub?.cancel();
    await _sub?.cancel();
    await recorder.dispose();
    super.dispose();
  }
}
