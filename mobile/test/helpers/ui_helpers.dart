import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/services.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';

bool _loaded = false;
Future<void> loadUiFont(WidgetTester tester) async {
  if (_loaded) return;
  await tester.runAsync(() async {
    final data = await rootBundle.load('assets/ui/thai.ttf');
    final loader = FontLoader('SnoresensThai')..addFont(Future.value(data));
    await loader.load();
  });
  _loaded = true;
}

Future<void> saveUiPreview(
  WidgetTester tester,
  GlobalKey key,
  String name,
) async {
  final out = Platform.environment['SNORESENS_PREVIEW_DIR'];
  if (out == null) return;
  await tester.runAsync(() async {
    final image =
        await (key.currentContext!.findRenderObject()! as RenderRepaintBoundary)
            .toImage(pixelRatio: 2);
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    await Directory(out).create(recursive: true);
    await File('$out/native-$name.png')
        .writeAsBytes(bytes!.buffer.asUint8List());
    image.dispose();
  });
}

Future<void> waitForUi(WidgetTester tester, bool Function() predicate) async {
  for (var i = 0; i < 300; i++) {
    await tester.runAsync(
      () => Future<void>.delayed(const Duration(milliseconds: 10)),
    );
    await tester.pump(const Duration(milliseconds:20));
    if (predicate()) return;
  }
  fail('UI operation did not finish');
}

Future<void> tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pump(const Duration(milliseconds: 200));
  await tester.tap(finder);
  await tester.pump(const Duration(milliseconds: 200));
}
