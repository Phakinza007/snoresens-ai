import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:sanor_mobile/web_pages.dart';
import 'package:sanor_mobile/web_style.dart';

import 'helpers/ui_helpers.dart';

void main() {
  testWidgets(
    'night controls fit a narrow phone with large text and remain actionable',
    (tester) async {
      await loadUiFont(tester);
      tester.view.physicalSize = const Size(320, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      var pauses = 0, stops = 0;
      await tester.pumpWidget(
        MaterialApp(
          theme: snoresensTheme(),
          home: Scaffold(
            backgroundColor: navy,
            body: MediaQuery(
              data: const MediaQueryData(
                size: Size(320, 844),
                textScaler: TextScaler.linear(2),
              ),
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(18),
                child: WebRecording(
                  active: true,
                  paused: false,
                  stopped: false,
                  changing: false,
                  elapsed: const Duration(hours: 8, minutes: 1),
                  message: 'กำลังรับเสียง · ล็อกหน้าจอได้',
                  levels: List<double>.generate(46, (i) => i / 45),
                  onPause: () => pauses++,
                  onStop: () => stops++,
                  onHome: () {},
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await tapVisible(tester, find.text('พักการบันทึก'));
      await tapVisible(tester, find.text('จบการบันทึก'));
      expect(pauses, 1);
      expect(stops, 1);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets('home and all four tabs fit a narrow screen with large text', (
    tester,
  ) async {
    await loadUiFont(tester);
    tester.view.physicalSize = const Size(320, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      MaterialApp(
        theme: snoresensTheme(),
        home: MediaQuery(
          data: const MediaQueryData(
            size: Size(320, 844),
            textScaler: TextScaler.linear(1.6),
          ),
          child: Scaffold(
            bottomNavigationBar: WebNav(selected: 0, onSelect: (_) {}),
            body: SingleChildScrollView(
              padding: const EdgeInsets.all(18),
              child: WebHome(
                records: const [],
                active: false,
                enabled: true,
                onStart: () {},
                onUpload: () {},
                onSample: () {},
                onHistory: () {},
                onGuide: () {},
                onOpen: (_) {},
                onRetry: (_) {},
                onDelete: (_) {},
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    await tapVisible(tester, find.text('เริ่มบันทึกคืนนี้'));
    expect(tester.takeException(), isNull);
  });
  testWidgets('consent displays start error near the action button', (
    tester,
  ) async {
    await loadUiFont(tester);
    await tester.pumpWidget(
      MaterialApp(
        theme: snoresensTheme(),
        home: Scaffold(
          body: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: WebConsent(
              accepted: true,
              enabled: true,
              error: 'กรุณาอนุญาตไมโครโฟนใน Settings',
              onAccept: (_) {},
              onBack: () {},
              onBegin: () {},
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('กรุณาอนุญาตไมโครโฟนใน Settings'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
