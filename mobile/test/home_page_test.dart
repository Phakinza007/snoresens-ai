import 'dart:io';
import 'dart:typed_data';

import 'package:material_ui/material_ui.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sanor_mobile/main.dart';
import 'package:sanor_mobile/inference.dart';
import 'package:sanor_mobile/audio_patterns.dart';
import 'package:sanor_mobile/wav_parts.dart';
import 'package:sanor_mobile/web_style.dart';
import 'package:sanor_mobile/recording_store.dart';

import 'helpers/fake_recorder.dart';
import 'helpers/ui_helpers.dart';

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
      'detected_snore_seconds': .5,
      'snore_percent_of_recording': 25.0,
      'snore_event_count': 1,
      'analysis_hop_seconds': .02,
      'model_version': 'snore-v2-breathing-negatives',
    },
    [],
    [
      {'start_seconds': 0.0, 'end_seconds': .5, 'duration_seconds': .5},
    ],
    buildPatterns([], []),
    audioPath: audioPath,
  );
}

void main() {
  testWidgets(
    'web-style guided recording, consent, pause, report and durable history',
    (tester) async {
      await loadUiFont(tester);
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final dir = (await tester.runAsync(
        () => Directory.systemTemp.createTemp('home-parity-'),
      ))!;
      addTearDown(() => tester.runAsync(() => dir.delete(recursive: true)));
      final recorder = DiskRecorder();
      final boundary = GlobalKey();
      Widget app(FakeRecorder rec) => MaterialApp(
        theme: snoresensTheme(),
        home: RepaintBoundary(
          key: boundary,
          child: HomePage(
            documents: () async => dir,
            engine: TestEngine(),
            recorder: rec,
            enablePlayback: false,
          ),
        ),
      );
      await tester.pumpWidget(app(recorder));
      await waitForUi(
        tester,
        () =>
            tester
                .widget<FilledButton>(
                  find.widgetWithText(FilledButton, 'เริ่มบันทึกคืนนี้'),
                )
                .onPressed !=
            null,
      );
      await tester.pumpAndSettle();
      await saveUiPreview(tester, boundary, 'home-390');
      await tapVisible(tester, find.text('เริ่มบันทึกคืนนี้'));
      expect(find.text('เตรียมก่อนบันทึก'), findsOneWidget);
      expect(recorder.starts, 0);
      await saveUiPreview(tester, boundary, 'prepare-390');
      await tapVisible(tester, find.text('พร้อมแล้ว ดำเนินการต่อ'));
      expect(find.text('ความเป็นส่วนตัว'), findsOneWidget);
      expect(
        tester
            .widget<FilledButton>(
              find.widgetWithText(FilledButton, 'ยินยอมและเริ่มบันทึก'),
            )
            .onPressed,
        isNull,
      );
      await saveUiPreview(tester, boundary, 'consent-390');
      await tapVisible(tester, find.byKey(const ValueKey('record-consent')));
      await tapVisible(tester, find.text('ยินยอมและเริ่มบันทึก'));
      await waitForUi(
        tester,
        () => find.text('จบการบันทึก').evaluate().isNotEmpty,
      );
      await tester.pumpAndSettle();
      await saveUiPreview(tester, boundary, 'record-390');
      await tapVisible(tester, find.text('พักการบันทึก'));
      expect(find.widgetWithText(FilledButton, 'บันทึกต่อ'), findsOneWidget);
      await tapVisible(tester, find.widgetWithText(FilledButton, 'บันทึกต่อ'));
      await tapVisible(tester, find.text('จบการบันทึก'));
      await waitForUi(
        tester,
        () => find.text('เช็กลิสต์ตอนเช้า').evaluate().isNotEmpty,
      );
      await tester.pumpAndSettle();
      expect(recorder.starts, 1);
      expect(recorder.stops, 1);
      await tapVisible(tester, find.text('ข้ามไปดูรายงาน'));
      await waitForUi(
        tester,
        () => find.text('พบกรน 25.0%').evaluate().isNotEmpty,
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await tapVisible(tester, find.byKey(const ValueKey('nav-2')));
      expect(find.text('ประวัติการนอน'), findsOneWidget);
      await saveUiPreview(tester, boundary, 'history-390');
      await tapVisible(tester, find.byKey(const ValueKey('nav-3')));
      expect(find.text('โปรไฟล์และการตั้งค่า'), findsOneWidget);
      await saveUiPreview(tester, boundary, 'profile-390');
      await tapVisible(tester, find.text('ผู้ใช้ทั่วไป'));
      await tester.enterText(find.byType(TextField), 'ชื่อทดสอบ');
      await tapVisible(tester, find.text('บันทึกชื่อ'));
      await waitForUi(
        tester,
        () =>
            find.byType(TextField).evaluate().isEmpty &&
            find.text('ชื่อทดสอบ').evaluate().isNotEmpty,
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);

      await tester.pumpWidget(const SizedBox());
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 40)),
      );
      await tester.pumpWidget(app(DiskRecorder()));
      await waitForUi(
        tester,
        () => find.text('พบกรน 25.0%').evaluate().isNotEmpty,
      );
      await tapVisible(tester, find.byKey(const ValueKey('nav-1')));
      await waitForUi(
        tester,
        () => find.text('ฟังเสียงและดูช่วงที่ตรวจพบ').evaluate().isNotEmpty,
      );
      await tapVisible(tester, find.text('ลบผลการบันทึกนี้'));
      await tapVisible(tester, find.text('ยกเลิก'));
      expect(find.text('รายงานการนอน'), findsOneWidget);
      await tapVisible(tester, find.text('ทำเช็กลิสต์ตอนเช้า'));
      await tester.pumpAndSettle();
      for (final key in [
        'sore_throat-none',
        'dry_mouth-no',
        'choking-no',
        'witnessed-unknown',
        'congestion-no',
      ]) {
        await tapVisible(tester, find.byKey(ValueKey(key)));
      }
      await tapVisible(tester, find.text('บันทึกและดูผล'));
      await waitForUi(
        tester,
        () => find.text('ติดตามอาการต่อ').evaluate().isNotEmpty,
      );
      expect(tester.takeException(), isNull);
      final pref = await tester.runAsync(
        () =>
            RecordingStore(Directory('${dir.path}/Snoresens'))
                .readPreferences(),
      );
      expect((pref!['checklists'] as Map).length, 1);
      await tapVisible(tester, find.byKey(const ValueKey('nav-3')));
      expect(find.text('ชื่อทดสอบ'), findsOneWidget);
      await tapVisible(tester, find.text('ลบเสียงและผลทั้งหมดบนเครื่องนี้'));
      await tapVisible(tester, find.text('ยกเลิก'));
      expect(find.textContaining('1 รายการบน iPhone'), findsOneWidget);
      await tapVisible(tester, find.text('ลบเสียงและผลทั้งหมดบนเครื่องนี้'));
      await tapVisible(tester, find.widgetWithText(FilledButton, 'ลบ'));
      await waitForUi(
        tester,
        () => find.textContaining('0 รายการบน iPhone').evaluate().isNotEmpty,
      );
      expect(find.text('ชื่อทดสอบ'), findsOneWidget);
      final after = await tester.runAsync(
        () =>
            RecordingStore(Directory('${dir.path}/Snoresens'))
                .readPreferences(),
      );
      expect(after!['checklists'], isEmpty);

      await tester.pumpWidget(const SizedBox());
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 40)),
      );
    },
  );
}
