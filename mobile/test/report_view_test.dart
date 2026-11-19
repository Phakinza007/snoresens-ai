import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:sanor_mobile/result_panel.dart';
import 'package:sanor_mobile/inference.dart';
import 'package:sanor_mobile/web_style.dart';
import 'package:sanor_mobile/morning_checklist.dart';

import 'helpers/ui_helpers.dart';

SnoreResult fixture() {
  final path = Platform.environment['SNORESENS_WEB_REPORT_FIXTURE'];
  if (path != null) {
    final data =
        jsonDecode(File(path).readAsStringSync()) as Map<String, dynamic>;
    data['audio_patterns'] ??= <String, dynamic>{};
    return SnoreResult.fromJson(data);
  }
  return SnoreResult(
    'UI fixture',
    {
      'recording_seconds': 45.0,
      'detected_snore_seconds': 4.0,
      'snore_event_count': 2,
      'analysis_hop_seconds': .02,
    },
    [
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
        'duration_seconds': 19.64,
        'prediction': 'non_snore',
        'rms_dbfs': -50,
      },
      {
        'start_seconds': 30.0,
        'duration_seconds': 2.72,
        'prediction': 'snore',
        'rms_dbfs': -20,
      },
      {
        'start_seconds': 32.72,
        'duration_seconds': 12.28,
        'prediction': 'non_snore',
        'rms_dbfs': -50,
      },
    ],
    [
      {'start_seconds': 9.08, 'end_seconds': 10.36, 'duration_seconds': 1.28},
      {'start_seconds': 30.0, 'end_seconds': 32.72, 'duration_seconds': 2.72},
    ],
    {},
  );
}

void main() {
  testWidgets(
    'web report renders real persisted fields, 20 ms zoom, checklist and details at phone sizes',
    (tester) async {
      await loadUiFont(tester);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final key = GlobalKey();
      for (final width in [390.0, 320.0]) {
        tester.view.physicalSize = Size(width, 844);
        tester.view.devicePixelRatio = 1;
        await tester.pumpWidget(
          MaterialApp(
            theme: snoresensTheme(),
            home: RepaintBoundary(
              key: key,
              child: MediaQuery(
                data: MediaQueryData(
                  size: Size(width, 844),
                  textScaler: TextScaler.linear(width == 320 ? 1.6 : 1),
                ),
                child: Scaffold(
                  bottomNavigationBar: WebNav(selected: 1, onSelect: (_) {}),
                  body: SingleChildScrollView(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        WebHeader(title: 'รายงานการนอน', onBack: () {}),
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                'บันทึกเมื่อ 17 พฤศจิกายน 2569',
                                style: type(12, color: muted),
                              ),
                            ),
                            const BluePill('เสียงตัวอย่าง'),
                          ],
                        ),
                        const SizedBox(height: 20),
                        ResultPanel(
                          key: ValueKey(width),
                          result: fixture(),
                          enablePlayback: false,
                          onReanalyze: () {},
                          onDelete: () {},
                          checklist: MorningCard(onOpen: () {}, onInfo: () {}),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        await saveUiPreview(tester, key, 'report-${width.toInt()}');
        await tapVisible(tester, find.text('ดูรายละเอียดการวัดเสียง'));
        expect(find.text('ระดับเสียงมัธยฐาน'), findsOneWidget);
        expect(tester.takeException(), isNull);
        await tapVisible(
          tester,
          find.text('พบช่วงเสียงกรน ${fixture().events} ช่วง'),
        );
        expect(tester.takeException(), isNull);
      }
    },
  );
  testWidgets(
    'iOS playback restores playback audio context, uses stop release mode, and can play',
    (tester) async {
      await loadUiFont(tester);
      debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
      addTearDown(() => debugDefaultTargetPlatformOverride = null);
      final calls = <(String, Map<Object?, Object?>?)>[];
      final messenger =
          TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
      final mockedEventChannels = <String>['xyz.luan/audioplayers.global/events'];
      messenger.setMockMethodCallHandler(
        const MethodChannel('xyz.luan/audioplayers.global'),
        (call) async => 1,
      );
      messenger.setMockStreamHandler(
        const EventChannel('xyz.luan/audioplayers.global/events'),
        MockStreamHandler.inline(onListen: (_, _) {}),
      );
      messenger.setMockMethodCallHandler(
        const MethodChannel('xyz.luan/audioplayers'),
        (call) async {
          final args = call.arguments as Map<Object?, Object?>?;
          calls.add((call.method, args));
          if (call.method == 'create') {
            final id = args!['playerId'] as String;
            final ch = 'xyz.luan/audioplayers/events/$id';
            mockedEventChannels.add(ch);
            messenger.setMockStreamHandler(
              EventChannel(ch),
              MockStreamHandler.inline(onListen: (_, _) {}),
            );
          } else if (call.method == 'setSourceUrl') {
            final id = args!['playerId'] as String;
            await messenger.handlePlatformMessage(
              'xyz.luan/audioplayers/events/$id',
              const StandardMethodCodec().encodeSuccessEnvelope({
                'event': 'audio.onPrepared',
                'value': true,
              }),
              (_) {},
            );
          }
          if (call.method == 'getCurrentPosition') return 0;
          return 1;
        },
      );
      addTearDown(() {
        for (final ch in mockedEventChannels) {
          messenger.setMockStreamHandler(EventChannel(ch), null);
        }
        messenger.setMockMethodCallHandler(
          const MethodChannel('xyz.luan/audioplayers.global'),
          null,
        );
        messenger.setMockMethodCallHandler(
          const MethodChannel('xyz.luan/audioplayers'),
          null,
        );
      });
      final base = fixture();
      final withAudio = SnoreResult(
        base.name,
        base.summary,
        base.timeline,
        base.snoreEvents,
        base.audioPatterns,
        audioPath: '/tmp/fake_snore.wav',
      );
      await tester.pumpWidget(
        MaterialApp(
          theme: snoresensTheme(),
          home: Scaffold(
            body: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ResultPanel(result: withAudio),
            ),
          ),
        ),
      );
      await waitForUi(
        tester,
        () => calls.any((c) => c.$1 == 'setSourceUrl'),
      );
      expect(
        calls.any(
          (c) =>
              c.$1 == 'setAudioContext' && c.$2?['category'] == 'playback',
        ),
        isTrue,
      );
      expect(
        calls.any(
          (c) =>
              c.$1 == 'setReleaseMode' &&
              c.$2?['releaseMode'] == 'ReleaseMode.stop',
        ),
        isTrue,
      );
      calls.clear();
      await tapVisible(tester, find.byTooltip('เล่นเสียง'));
      expect(
        calls.any(
          (c) =>
              c.$1 == 'setAudioContext' && c.$2?['category'] == 'playback',
        ),
        isTrue,
      );
      expect(calls.any((c) => c.$1 == 'resume'), isTrue);
      expect(tester.takeException(), isNull);
    },
  );
}
