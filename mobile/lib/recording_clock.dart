/// Monotonic UI clock. Final captured duration always comes from WAV samples.
class RecordingClock {
  Duration _total = Duration.zero;
  Duration? _since;
  void record(Duration now) {
    _since ??= now;
  }

  void pause(Duration now) {
    if (_since != null) {
      if (now >= _since!) _total += now - _since!;
      _since = null;
    }
  }

  Duration elapsed(Duration now) =>
      _total +
      (_since != null && now >= _since! ? now - _since! : Duration.zero);
}

String recordingTime(Duration d) =>
    '${d.inHours.toString().padLeft(2, '0')}:${(d.inMinutes % 60).toString().padLeft(2, '0')}:${(d.inSeconds % 60).toString().padLeft(2, '0')}';
