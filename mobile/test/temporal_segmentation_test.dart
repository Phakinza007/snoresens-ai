import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:sanor_mobile/temporal_segmentation.dart';

void main() {
  test('20 ms cells preserve partial recording and reuse 100 ms contexts', () {
    final rows = analysisPlan(37603).toList();
    expect(rows.length, 118);
    expect(rows.fold<int>(0, (n, r) => n + r.length), 37603);
    expect(rows.last.length, 163);
    expect(rows.take(5).map((r) => r.contextStart).toSet().length, 1);
  });
  test(
    'silence and a negative parent cannot inherit neighboring positive context',
    () {
      expect(isSnore(.99, null, -20, .44, -40), false);
      expect(isSnore(.99, -20, -50, .44, -40), false);
      expect(isSnore(.99, -20, -20, .44, -40), true);
      expect(isSnore(.2, -20, -20, .44, -40), false);
    },
  );
  test('adaptive gate agrees with Python and JavaScript', () {
    expect(
      activityThreshold([
        ...List<double>.filled(20, -36),
        ...List<double>.filled(10, -15),
      ]),
      -30,
    );
    expect(activityThreshold([null, null]), -60);
  });
  test(
    'all demo boundaries and decisions agree with frozen Python fixture',
    () {
      final fixture =
          jsonDecode(
                File('test/fixtures/temporal_micro20.json').readAsStringSync(),
              )
              as Map<String, dynamic>;
      final rows = (fixture['rows'] as List).cast<Map<String, dynamic>>();
      final plan = analysisPlan(45 * 16000).toList();
      expect(plan.length, rows.length);
      for (var i = 0; i < rows.length; i++) {
        final r = rows[i];
        expect(plan[i].at / 16000, r['start_seconds']);
        expect(
          plan[i].contextStart / 16000,
          closeTo(r['context_start_seconds'], .00051),
        );
        expect(
          isSnore(
            (r['snore_probability'] as num).toDouble(),
            (r['rms_dbfs'] as num?)?.toDouble(),
            (r['parent_rms_dbfs'] as num?)?.toDouble(),
            (fixture['threshold'] as num).toDouble(),
            (fixture['floor'] as num).toDouble(),
          ),
          r['prediction'] == 'snore',
          reason: 'cell $i',
        );
      }
    },
  );
}
