import 'package:material_ui/material_ui.dart';

import 'web_style.dart';

// Same project rules as the production website; not clinically validated.
const morningQuestions = [
  (
    'sore_throat',
    'อาการตอนตื่น (หายใจทางปาก)',
    'ตื่นมาเจ็บคอหรือคอแห้ง',
    [('none', 'ไม่มี'), ('mild', 'เล็กน้อย'), ('severe', 'มาก')],
  ),
  (
    'dry_mouth',
    'อาการตอนตื่น (หายใจทางปาก)',
    'ปากแห้งตอนตื่น',
    [('yes', 'ใช่'), ('no', 'ไม่ใช่')],
  ),
  (
    'choking',
    'การหายใจขณะหลับ',
    'สะดุ้งตื่นเพราะสำลัก หายใจเฮือก หรือหายใจไม่ออก',
    [('yes', 'ใช่'), ('no', 'ไม่ใช่')],
  ),
  (
    'witnessed',
    'การหายใจขณะหลับ',
    'คนข้าง ๆ เห็นว่าหยุดหายใจขณะหลับ',
    [('yes', 'ใช่'), ('no', 'ไม่ใช่'), ('unknown', 'ไม่มีคนสังเกต')],
  ),
  (
    'congestion',
    'ปัจจัยที่อาจทำให้ผลคลาดเคลื่อน',
    'เมื่อคืนคัดจมูก เป็นหวัด หรือภูมิแพ้',
    [('yes', 'ใช่'), ('no', 'ไม่ใช่')],
  ),
];
bool _yes(Object? v) => v == 'yes' || v == 'mild' || v == 'severe';
List<String> morningSymptoms(Map<String, dynamic> a) =>
    ['sore_throat', 'dry_mouth'].where((id) => _yes(a[id])).toList();
bool completeMorning(Map<String, dynamic> a) =>
    morningQuestions.every((q) => q.$4.any((o) => o.$1 == a[q.$1]));
Map<String, dynamic> evaluateMorning(
  Map<String, dynamic> answers, {
  double? snorePct,
  List<Map<String, dynamic>> history = const [],
}) {
  final reasons = <String>[],
      symptoms = morningSymptoms(answers),
      congested = _yes(answers['congestion']),
      snoring = snorePct != null && snorePct.isFinite && snorePct >= 10;
  final recent = [answers, ...history].take(7).toList(),
      symptomNights = recent
          .where((a) => morningSymptoms(a).isNotEmpty && !_yes(a['congestion']))
          .length;
  var level = 'monitor';
  if (_yes(answers['witnessed'])) {
    level = 'urgent';
    reasons.add('มีคนเห็นว่าหยุดหายใจขณะหลับ');
  }
  if (_yes(answers['choking'])) {
    level = 'urgent';
    reasons.add('สะดุ้งตื่นเพราะสำลักหรือหายใจไม่ออก');
  }
  if (snoring && symptoms.isNotEmpty && !congested) {
    if (level == 'monitor') level = 'consult';
    reasons.add(
      'แอปตรวจพบกรน ${snorePct.toStringAsFixed(0)}% ของเวลาบันทึก ร่วมกับอาการหายใจทางปากตอนตื่น',
    );
  }
  if (symptomNights >= 3) {
    if (level == 'monitor') level = 'consult';
    reasons.add(
      'มีอาการหายใจทางปาก $symptomNights ใน ${recent.length} คืนล่าสุด',
    );
  }
  return {
    'level': level,
    'reasons': reasons,
    'symptoms': symptoms,
    'snoring': snoring,
    'snorePct': snorePct,
    'symptomNights': symptomNights,
    'nightsConsidered': recent.length,
    'confounder': congested,
  };
}

const morningLevels = {
  'urgent': (
    'ควรพบแพทย์',
    'มีสัญญาณการหายใจผิดปกติขณะหลับ ควรให้แพทย์ประเมิน',
    Color(0xffc44f5c),
  ),
  'consult': (
    'แนะนำปรึกษาแพทย์',
    'กรนร่วมกับอาการหายใจทางปาก หรือมีอาการซ้ำหลายคืน',
    Color(0xffc29136),
  ),
  'monitor': (
    'ติดตามอาการต่อ',
    'ยังไม่เข้าเกณฑ์ ทำเช็กลิสต์ทุกเช้าเพื่อดูแนวโน้ม',
    Color(0xff49a38c),
  ),
};

class MorningCard extends StatelessWidget {
  final Map<String, dynamic>? result;
  final VoidCallback onOpen, onInfo;
  const MorningCard({
    super.key,
    this.result,
    required this.onOpen,
    required this.onInfo,
  });
  @override
  Widget build(BuildContext context) {
    final r = result, level = r == null ? null : morningLevels[r['level']]!;
    return WebSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            r == null ? 'เช็กลิสต์ตอนเช้า' : 'ผลเช็กลิสต์ตอนเช้า',
            style: type(12, color: muted),
          ),
          const SizedBox(height: 12),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  level?.$1 ?? 'ตื่นมาแล้วรู้สึกอย่างไร',
                  style: type(18, weight: FontWeight.w700),
                ),
              ),
              if (level != null)
                Container(
                  width: 12,
                  height: 12,
                  margin: const EdgeInsets.only(top: 6),
                  decoration: BoxDecoration(
                    color: level.$3,
                    shape: BoxShape.circle,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            level?.$2 ?? 'ตอบ 5 ข้อสั้น ๆ เพื่อดูว่าอาการน่าเป็นห่วงไหม และควรพบแพทย์หรือไม่',
            style: type(12, color: muted),
          ),
          if (r == null) ...[
            const SizedBox(height: 16),
            FilledButton(
              onPressed: onOpen,
              child: const Text('ทำเช็กลิสต์ตอนเช้า'),
            ),
          ] else ...[
            for (final reason in r['reasons'] as List) ...[
              const SizedBox(height: 8),
              Text('• $reason', style: type(12)),
            ],
            const SizedBox(height: 12),
            Text(
              'อาการหายใจทางปาก ${r['symptomNights']} จาก ${r['nightsConsidered']} คืนล่าสุด',
              style: type(12),
            ),
            const SizedBox(height: 8),
            Text(
              'กรนจากแอป ${r['snorePct'] == null ? '—' : '${(r['snorePct'] as num).toStringAsFixed(1)}% ของเวลาบันทึก'}',
              style: type(12),
            ),
            if (r['confounder'] == true) ...[
              const SizedBox(height: 8),
              Text(
                'คืนนี้คัดจมูก เป็นหวัด หรือภูมิแพ้ จึงไม่นับเจ็บคอหรือปากแห้งของคืนนี้',
                style: type(12, color: muted),
              ),
            ],
            const SizedBox(height: 12),
            Text(
              'เป็นการคัดกรองเบื้องต้น เกณฑ์รวมของโครงการยังไม่ผ่านการตรวจสอบทางคลินิก ไม่ใช่การวินิจฉัยโรค',
              style: type(12, color: muted),
            ),
            Wrap(
              spacing: 16,
              children: [
                TextButton(onPressed: onOpen, child: const Text('แก้ไขคำตอบ')),
                TextButton(
                  onPressed: onInfo,
                  child: const Text('เกณฑ์นี้คิดอย่างไร'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class MorningForm extends StatefulWidget {
  final Map<String, dynamic> initial;
  final bool saving;
  final Future<void> Function(Map<String, dynamic>) onSave;
  final VoidCallback onBack, onSkip;
  final String date;
  const MorningForm({
    super.key,
    required this.initial,
    required this.saving,
    required this.onSave,
    required this.onBack,
    required this.onSkip,
    required this.date,
  });
  @override
  State<MorningForm> createState() => _MorningFormState();
}

class _MorningFormState extends State<MorningForm> {
  late Map<String, dynamic> answers = Map.of(widget.initial);
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      WebHeader(title: 'เช็กลิสต์ตอนเช้า', onBack: widget.onBack),
      Text(
        'การบันทึกเมื่อ ${widget.date} · ตอบตามที่รู้สึกเมื่อตื่นนอน',
        style: type(13, color: muted),
      ),
      const SizedBox(height: 24),
      for (var i = 0; i < morningQuestions.length; i++) ...[
        if (i == 0 || morningQuestions[i].$2 != morningQuestions[i - 1].$2) ...[
          const SizedBox(height: 14),
          Text(
            morningQuestions[i].$2,
            style: type(15, weight: FontWeight.w700),
          ),
          const SizedBox(height: 14),
        ],
        WebSurface(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                morningQuestions[i].$3,
                style: type(14, weight: FontWeight.w600),
              ),
              const SizedBox(height: 14),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final option in morningQuestions[i].$4)
                    ChoiceChip(
                      key: ValueKey('${morningQuestions[i].$1}-${option.$1}'),
                      label: Text(option.$2),
                      selected: answers[morningQuestions[i].$1] == option.$1,
                      onSelected: widget.saving
                          ? null
                          : (_) => setState(
                              () => answers[morningQuestions[i].$1] = option.$1,
                            ),
                      selectedColor: const Color(0xffdfe8ff),
                      labelStyle: type(
                        13,
                        color: answers[morningQuestions[i].$1] == option.$1
                            ? blue
                            : ink,
                      ),
                      side: const BorderSide(color: line),
                      showCheckmark: false,
                    ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
      ],
      const SizedBox(height: 16),
      FilledButton(
        onPressed: completeMorning(answers) && !widget.saving
            ? () => widget.onSave(answers)
            : null,
        child: const Text('บันทึกและดูผล'),
      ),
      TextButton(
        onPressed: widget.saving ? null : widget.onSkip,
        child: const Text('ข้ามไปดูรายงาน'),
      ),
    ],
  );
}
