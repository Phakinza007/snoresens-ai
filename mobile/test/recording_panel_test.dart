import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:sanor_mobile/recording_panel.dart';

void main() {
  testWidgets(
    'recording controls remain reachable on a narrow phone and large text',
    (tester) async {
      var paused = false;
      var stops = 0;
      final boundary = GlobalKey();
      final font = Platform.environment['SNORESENS_PREVIEW_FONT'];
      if (font != null) {
        final loader = FontLoader('SnoresensPreview')
          ..addFont(
            Future.value(ByteData.sublistView(File(font).readAsBytesSync())),
          );
        await tester.runAsync(() => loader.load());
      }
      final icons = Platform.environment['SNORESENS_PREVIEW_ICONS'];
      if (icons != null) {
        final loader = FontLoader('MaterialIcons')
          ..addFont(
            Future.value(ByteData.sublistView(File(icons).readAsBytesSync())),
          );
        await tester.runAsync(() => loader.load());
      }
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      for (final width in [390.0, 320.0]) {
        tester.view.physicalSize = Size(width, 844);
        tester.view.devicePixelRatio = 1;
        await tester.pumpWidget(
          MaterialApp(
            theme: ThemeData(
              fontFamily: font == null ? null : 'SnoresensPreview',
              colorScheme: ColorScheme.fromSeed(
                seedColor: const Color(0xff3157f5),
              ),
            ),
            home: RepaintBoundary(
              key: boundary,
              child: Scaffold(
                appBar: AppBar(title: const Text('Snoresens AI')),
                body: MediaQuery(
                  data: MediaQueryData(
                    size: Size(width, 844),
                    textScaler: TextScaler.linear(width == 320 ? 2 : 1),
                  ),
                  child: ListView(
                    padding: const EdgeInsets.all(24),
                    children: [
                      const Text(
                        'คืนนี้ กำลังรับฟัง',
                        style: TextStyle(fontSize: 28),
                      ),
                      const SizedBox(height: 24),
                      StatefulBuilder(
                        builder: (context, setState) => RecordingPanel(
                          active: true,
                          paused: paused,
                          stopped: false,
                          enabled: true,
                          changing: false,
                          elapsed: const Duration(
                            hours: 1,
                            minutes: 23,
                            seconds: 45,
                          ),
                          message: paused
                              ? 'พักการบันทึก'
                              : 'กำลังรับเสียง · ล็อกหน้าจอได้',
                          onStart: () {},
                          onPause: () => setState(() => paused = !paused),
                          onStop: () => stops++,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        await tester.ensureVisible(find.text('พักการบันทึก'));
        await tester.pumpAndSettle();
        await tester.tap(find.text('พักการบันทึก'));
        await tester.pumpAndSettle();
        expect(find.widgetWithText(FilledButton, 'บันทึกต่อ'), findsOneWidget);
        await tester.ensureVisible(find.text('บันทึกต่อ'));
        await tester.pumpAndSettle();
        await tester.tap(find.text('บันทึกต่อ'));
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.text('จบและวิเคราะห์'));
        await tester.pumpAndSettle();
        await tester.tap(find.text('จบและวิเคราะห์'));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        final out = Platform.environment['SNORESENS_PREVIEW_DIR'];
        if (out != null) {
          await tester.runAsync(() async {
            final image =
                await (boundary.currentContext!.findRenderObject()!
                        as RenderRepaintBoundary)
                    .toImage(pixelRatio: 2);
            final bytes = await image.toByteData(
              format: ui.ImageByteFormat.png,
            );
            await Directory(out).create(recursive: true);
            await File('$out/recording-${width.toInt()}.png')
                .writeAsBytes(bytes!.buffer.asUint8List());
            image.dispose();
          });
        }
      }
      expect(stops, 2);
    },
  );
  testWidgets(
    'pending operations disable repeated actions; a stopped take can only be finalized',
    (tester) async {
      Widget panel(bool changing, bool stopped) => MaterialApp(
        home: Scaffold(
          body: RecordingPanel(
            active: true,
            paused: true,
            stopped: stopped,
            enabled: true,
            changing: changing,
            elapsed: Duration.zero,
            message: 'กำลังเก็บไฟล์',
            onStart: () {},
            onPause: () {},
            onStop: () {},
          ),
        ),
      );
      await tester.pumpWidget(panel(true, false));
      expect(
        tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull,
      );
      expect(
        tester.widget<OutlinedButton>(find.byType(OutlinedButton)).onPressed,
        isNull,
      );
      await tester.pumpWidget(panel(false, true));
      expect(
        tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull,
      );
      expect(
        tester.widget<OutlinedButton>(find.byType(OutlinedButton)).onPressed,
        isNotNull,
      );
    },
  );
}
