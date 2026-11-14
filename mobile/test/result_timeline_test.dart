import 'dart:ui' as ui;
import 'package:material_ui/material_ui.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sanor_mobile/result_panel.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('playback labels keep 20 ms boundaries', () {
    expect(audioTime(9.08), '00:00:09.08');
    expect(audioTime(10.36), '00:00:10.36');
  });
  test(
    'native graph does not extend a snore into its overview bucket',
    () async {
      final rows = <Map<String, dynamic>>[
        {
          'start_seconds': 0.0,
          'duration_seconds': 9.08,
          'prediction': 'non_snore',
          'rms_dbfs': -50,
        },
        {
          'start_seconds': 9.08,
          'duration_seconds': 1.28,
          'prediction': 'snore',
          'rms_dbfs': -20,
        },
        {
          'start_seconds': 10.36,
          'duration_seconds': 34.64,
          'prediction': 'non_snore',
          'rms_dbfs': -50,
        },
      ];
      final recorder = ui.PictureRecorder(), canvas = Canvas(recorder);
      AudioTimelinePainter(rows, 45).paint(canvas, const Size(1000, 125));
      final image = await recorder.endRecording().toImage(1000, 125);
      final rgba = await image.toByteData(format: ui.ImageByteFormat.rawRgba);
      List<int> pixel(double seconds) {
        final index = (10 * 1000 + (seconds / 45 * 1000).floor()) * 4;
        return rgba!.buffer.asUint8List().sublist(index, index + 3);
      }

      expect(pixel(9.02), isNot(pixel(9.2)));
      image.dispose();
    },
  );
}
