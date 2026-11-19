import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sanor_mobile/morning_checklist.dart';
import 'package:sanor_mobile/inference.dart';
import 'package:sanor_mobile/result_panel.dart';
import 'package:sanor_mobile/recording_store.dart';

void main() {
  test('web checklist combinations, precedence, thresholds and seven-session history agree', () {
    final cases = jsonDecode(
      File('test/fixtures/web-checklist.json').readAsStringSync(),
    ) as List;
    for (final c in cases) {
      expect(
        evaluateMorning(
          Map<String, dynamic>.from(c['answers']),
          snorePct: (c['snorePct'] as num?)?.toDouble(),
          history: (c['history'] as List)
              .map((x) => Map<String, dynamic>.from(x))
              .toList(),
        ),
        c['expected'],
        reason: jsonEncode(c),
      );
    }
  });
  test('experimental composite matches the web and rejects unavailable or invalid inputs', () {
    final cases = jsonDecode(
      File('test/fixtures/web-composite.json').readAsStringSync(),
    ) as List;
    for (final c in cases) {
      final d = c['item'];
      final r = SnoreResult(
        'fixture',
        Map<String, dynamic>.from(d['summary']),
        [],
        (d['snore_events'] as List)
            .map((x) => Map<String, dynamic>.from(x))
            .toList(),
        {},
      );
      expect(experimentalAudioScore(r), c['expected']);
    }
  });
  test('profile and checklist persist; clearing recordings keeps profile and removes orphaned analysis', () async {
    final dir = await Directory.systemTemp.createTemp('preferences-');
    addTearDown(() => dir.delete(recursive: true));
    final s = RecordingStore(dir);
    await s.savePreferences({
      'name': 'ผู้ใช้ทดสอบ',
      'checklists': {
        'night': {
          'answers': {'dry_mouth': 'yes'},
        },
      },
    });
    await s.save(
      RecordingEntry(
        id: 'night',
        name: 'night',
        createdAt: DateTime.utc(2026),
        status: 'pending',
      ),
    );
    await File(s.audioPath('night')).writeAsString('fixture');
    await File('${dir.path}/broken.record.json').writeAsString('broken');
    final reopen = RecordingStore(dir);
    expect(
      (await reopen
          .readPreferences())['checklists']['night']['answers']['dry_mouth'],
      'yes',
    );
    await reopen.clearRecordings();
    expect(await reopen.list(), isEmpty);
    expect(await File(s.audioPath('night')).exists(), false);
    expect((await reopen.readPreferences())['name'], 'ผู้ใช้ทดสอบ');
    expect(await File('${dir.path}/broken.record.json').exists(), false);
  });
}
