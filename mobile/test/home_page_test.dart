import 'dart:io';
import 'dart:typed_data';

import 'package:material_ui/material_ui.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sanor_mobile/main.dart';
import 'package:sanor_mobile/inference.dart';
import 'package:sanor_mobile/audio_patterns.dart';
import 'package:sanor_mobile/wav_parts.dart';

import 'helpers/fake_recorder.dart';

class DiskRecorder extends FakeRecorder {
  @override
  Future<void> start(String path) async {
    await File(path).writeAsBytes(wrapPcm(Uint8List(64000), 16000, 1));
    await super.start(path);
  }
}

class TestEngine extends SnoreEngine {
  @override
  Future<void> load() async {}
  @override
  void close() {}
  @override
  Future<SnoreResult> analyze(
    String name,
    Uint8List bytes, {
    String? audioPath,
    double quietThresholdDbfs = -45,
    double minGapSeconds = 10,
    bool Function()? shouldContinue,
  }) async => SnoreResult(
    name,
    {
      'recording_seconds': 2.0,
      'detected_snore_seconds': 0.5,
      'snore_event_count': 1,
    },
    [],
    [],
    buildPatterns([], []),
    audioPath: audioPath,
  );
}

void main() {
  testWidgets(
    'record, pause, finish, reopen history and cancel deletion in the real home screen',
    (tester) async {
      final dir = (await tester.runAsync(
        () => Directory.systemTemp.createTemp('home-'),
      ))!;
      addTearDown(() => tester.runAsync(() => dir.delete(recursive: true)));
      final recorder = DiskRecorder();
      Future<void> until(bool Function() predicate) async {
        for (var i = 0; i < 100; i++) {
          await tester.runAsync(
            () => Future<void>.delayed(const Duration(milliseconds: 10)),
          );
          await tester.pump();
          if (predicate()) return;
        }
        fail('Home operation did not finish');
      }

      Widget home() => MaterialApp(
        home: HomePage(
          documents: () async => dir,
          engine: TestEngine(),
          recorder: recorder,
        ),
      );
      await tester.pumpWidget(home());
      await until(
        () => find.text('พร้อมบันทึก · โมเดลรุ่น 2').evaluate().isNotEmpty,
      );
      await tester.tap(find.text('เริ่มบันทึกคืนนี้'));
      await until(() => find.text('พักการบันทึก').evaluate().isNotEmpty);
      await tester.tap(find.text('พักการบันทึก'));
      await tester.pump();
      expect(find.text('บันทึกต่อ'), findsOneWidget);
      await tester.tap(find.text('บันทึกต่อ'));
      await tester.pump();
      await tester.tap(find.text('จบและวิเคราะห์'));
      await until(() => find.textContaining('กรน 25.0%').evaluate().isNotEmpty);
      expect(recorder.starts, 1);
      expect(recorder.stops, 1);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 30)),
      );
      await tester.pumpWidget(
        MaterialApp(
          home: HomePage(
            documents: () async => dir,
            engine: TestEngine(),
            recorder: DiskRecorder(),
          ),
        ),
      );
      await until(() => find.textContaining('กรน 25.0%').evaluate().isNotEmpty);
      await tester.ensureVisible(find.byTooltip('ลบ'));
      await tester.tap(find.byTooltip('ลบ'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('ยกเลิก'));
      await tester.pumpAndSettle();
      expect(find.textContaining('กรน 25.0%'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 30)),
      );
    },
  );
}
