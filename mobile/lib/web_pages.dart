import 'dart:math' as math;

import 'package:material_ui/material_ui.dart';

import 'recording_store.dart';
import 'recording_clock.dart' show recordingTime;
import 'web_style.dart';
import 'morning_checklist.dart' show morningLevels;

String thaiDate(DateTime date, {bool short = false}) {
  final d = date.toLocal();
  return '${d.day} ${const ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'][d.month - 1]}${short ? '' : ' ${d.year + 543}'}';
}

String durationLabel(num seconds) {
  final s = seconds.toDouble();
  return s >= 3600
      ? '${s ~/ 3600} ชม. ${s % 3600 ~/ 60} น.'
      : s >= 60
      ? '${s ~/ 60} น. ${s.toInt() % 60} วิ.'
      : '${s.toStringAsFixed(1)} วิ.';
}

bool isSample(RecordingEntry e) => e.id.startsWith('sample_');
double entryPercent(RecordingEntry e) =>
    (e.summary?['snore_percent_of_recording'] as num?)?.toDouble() ?? 0;

class WebEmpty extends StatelessWidget {
  final VoidCallback? onUpload;
  final bool compact;
  const WebEmpty({super.key, this.onUpload, this.compact = false});
  @override
  Widget build(BuildContext context) => WebSurface(
    padding: EdgeInsets.all(compact ? 18 : 24),
    child: Column(
      crossAxisAlignment: compact
          ? CrossAxisAlignment.start
          : CrossAxisAlignment.center,
      children: [
        if (!compact) ...[
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              color: const Color(0xfff1f5ff),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const Center(child: Glyph('moon', color: Color(0xff99b1e8))),
          ),
          const SizedBox(height: 12),
        ],
        Text(
          'ยังไม่มีรายงานการนอน',
          style: type(compact ? 14 : 15, weight: FontWeight.w700),
        ),
        const SizedBox(height: 5),
        Text(
          'เริ่มจากบันทึกเสียงหรืออัปโหลดไฟล์ WAV แล้วดูผลการวิเคราะห์ที่นี่',
          textAlign: compact ? TextAlign.start : TextAlign.center,
          style: type(compact ? 12 : 13, color: muted, height: 1.75),
        ),
        if (!compact)
          TextButton.icon(
            onPressed: onUpload,
            icon: const Glyph('upload', size: 18),
            label: const Text('เลือกไฟล์เสียง'),
          ),
      ],
    ),
  );
}

class WebRecordCard extends StatelessWidget {
  final RecordingEntry entry;
  final VoidCallback? onTap, onRetry, onDelete;
  final bool latest;
  const WebRecordCard({
    super.key,
    required this.entry,
    this.onTap,
    this.onRetry,
    this.onDelete,
    this.latest = false,
  });
  @override
  Widget build(BuildContext context) {
    final done = entry.status == 'processed';
    return WebSurface(
      radius: 20,
      padding: EdgeInsets.all(latest ? 18 : 20),
      onTap: onTap,
      child: Row(
        children: [
          if (latest) ...[
            const Glyph('sun', size: 27),
            const SizedBox(width: 15),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${thaiDate(entry.createdAt, short: latest)}${latest && done ? ' · บันทึก ${durationLabel(entry.summary?['recording_seconds'] ?? 0)}' : ''}',
                  style: type(14, weight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                Text(
                  done
                      ? '${latest ? '' : '${durationLabel(entry.summary?['recording_seconds'] ?? 0)} · '}${isSample(entry) ? 'เสียงตัวอย่าง' : 'วิเคราะห์จากเสียงจริง'}'
                      : entry.status == 'recording'
                      ? 'กำลังบันทึกเสียง'
                      : 'รอวิเคราะห์ · ${entry.name}',
                  style: type(12, color: muted),
                ),
                if (entry.error != null) ...[
                  const SizedBox(height: 6),
                  Text(
                    entry.error!,
                    style: type(12, color: const Color(0xffb84155)),
                  ),
                ],
                if (latest && done) ...[
                  const SizedBox(height: 8),
                  BluePill(
                    'พบกรน ${entryPercent(entry).toStringAsFixed(1)}%',
                    amber: true,
                  ),
                ],
                if (!done && entry.status != 'recording')
                  Wrap(
                    spacing: 14,
                    children: [
                      TextButton.icon(
                        onPressed: onRetry,
                        icon: const Glyph('chart-no-axes-column', size: 16),
                        label: const Text('วิเคราะห์ต่อ'),
                      ),
                      TextButton(onPressed: onDelete, child: const Text('ลบ')),
                    ],
                  ),
              ],
            ),
          ),
          if (done && !latest) ...[
            const SizedBox(width: 8),
            BluePill('พบกรน ${entryPercent(entry).toStringAsFixed(1)}%'),
          ],
          if (latest && done) ...[
            const SizedBox(width: 10),
            const Glyph('chevron-right', size: 20, color: muted),
          ],
        ],
      ),
    );
  }
}

class WebHome extends StatelessWidget {
  final List<RecordingEntry> records;
  final bool active, enabled;
  final VoidCallback onStart, onUpload, onSample, onHistory, onGuide;
  final ValueChanged<RecordingEntry> onOpen, onRetry, onDelete;
  const WebHome({
    super.key,
    required this.records,
    required this.active,
    required this.enabled,
    required this.onStart,
    required this.onUpload,
    required this.onSample,
    required this.onHistory,
    required this.onGuide,
    required this.onOpen,
    required this.onRetry,
    required this.onDelete,
  });
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      WebHeader(onGuide: onGuide),
      Text(
        'คืนนี้ ฟังการนอนของคุณ',
        style: type(
          MediaQuery.sizeOf(context).width <= 370 ? 22 : 24,
          weight: FontWeight.w700,
          height: 1.45,
        ).copyWith(letterSpacing: -.6),
      ),
      const SizedBox(height: 6),
      Text(
        'รู้จักเสียงกรน เพื่อเข้าใจการพักผ่อน',
        style: type(14, color: muted, height: 1.75),
      ),
      const SizedBox(height: 26),
      Semantics(
        label: 'คืนที่ดี เริ่มจากการรับฟัง วางโทรศัพท์ข้างเตียง แล้วให้เราบันทึกเสียงระหว่างพักผ่อน',
        child: ExcludeSemantics(
          child: Container(
            constraints: const BoxConstraints(minHeight: 256),
            decoration: BoxDecoration(
              color: navy,
              borderRadius: BorderRadius.circular(28),
            ),
            child: Stack(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(22, 25, 22, 20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 240),
                        child: Text(
                          'คืนที่ดี เริ่มจากการรับฟัง',
                          style: type(
                            MediaQuery.sizeOf(context).width <= 370 ? 18 : 20,
                            color: Colors.white,
                            weight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'วางโทรศัพท์ข้างเตียง\nแล้วให้เราบันทึกเสียงระหว่างพักผ่อน',
                        style: type(
                          14,
                          color: const Color(0xffc5d4f0),
                          height: 1.85,
                        ),
                      ),
                      const SizedBox(height: 16),
                      const DecorativeWave(height: 48),
                      const SizedBox(height: 18),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 11,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: .125),
                          borderRadius: BorderRadius.circular(13),
                        ),
                        child: Row(
                          children: [
                            const Glyph(
                              'shield-check',
                              size: 16,
                              color: Color(0xffd8e2f7),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                'คุณเป็นผู้ควบคุมข้อมูลเสียงของคุณ',
                                style: type(11, color: const Color(0xffd8e2f7)),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                if (MediaQuery.textScalerOf(context).scale(1) <= 1.3)
                  Positioned(
                    right: MediaQuery.sizeOf(context).width <= 370 ? 23 : 34,
                    top: 29,
                    child: MoonArt(
                      size: MediaQuery.sizeOf(context).width <= 370 ? 55 : 66,
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
      const SizedBox(height: 24),
      FilledButton(
        onPressed: enabled ? onStart : null,
        child: Text(active ? 'กลับไปดูการบันทึก' : 'เริ่มบันทึกคืนนี้'),
      ),
      const SizedBox(height: 2),
      TextButton(
        onPressed: enabled && !active ? onUpload : null,
        child: const Text('มีไฟล์เสียงอยู่แล้ว? อัปโหลดไฟล์เสียง'),
      ),
      const SizedBox(height: 20),
      Row(
        children: [
          Expanded(
            child: Text(
              'ผลการบันทึกครั้งล่าสุด',
              style: type(17, weight: FontWeight.w700),
            ),
          ),
          TextButton(
            onPressed: onHistory,
            style: TextButton.styleFrom(
              minimumSize: const Size(44, 26),
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              padding: EdgeInsets.zero,
            ),
            child: Text('ดูทั้งหมด', style: type(12, color: blue)),
          ),
        ],
      ),
      const SizedBox(height: 6),
      if (records.isEmpty)
        const WebEmpty(compact: true)
      else
        WebRecordCard(
          entry: records.first,
          latest: true,
          onTap: records.first.status == 'processed'
              ? () => onOpen(records.first)
              : null,
          onRetry: enabled ? () => onRetry(records.first) : null,
          onDelete: enabled ? () => onDelete(records.first) : null,
        ),
      const SizedBox(height: 12),
      Center(
        child: TextButton.icon(
          onPressed: enabled && !active ? onSample : null,
          icon: const Glyph('headphones', size: 18),
          label: const Text('ลองวิเคราะห์เสียงตัวอย่าง'),
        ),
      ),
      const SizedBox(height: 4),
      Text(
        'ผลเป็นการประมาณเสียงกรน ไม่ใช่การวินิจฉัยโรค',
        style: type(11, color: muted, height: 1.8),
      ),
    ],
  );
}

class WebHistory extends StatelessWidget {
  final List<RecordingEntry> records;
  final bool enabled;
  final Map<String, Map<String, dynamic>> checklists;
  final VoidCallback onBack, onUpload, onExport, onCsv;
  final ValueChanged<RecordingEntry> onOpen, onRetry, onDelete;
  const WebHistory({
    super.key,
    required this.records,
    required this.enabled,
    required this.onBack,
    required this.onUpload,
    required this.onExport,
    required this.onCsv,
    this.checklists = const {},
    required this.onOpen,
    required this.onRetry,
    required this.onDelete,
  });
  @override
  Widget build(BuildContext context) {
    final chart = records
        .where((r) => r.status == 'processed')
        .take(7)
        .toList()
        .reversed
        .toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        WebHeader(title: 'ประวัติการนอน', onBack: onBack),
        Text(
          'ภาพรวม ${chart.isEmpty ? 'การบันทึกของคุณ' : '${chart.length} รายการล่าสุด'}',
          style: type(14, color: muted),
        ),
        const SizedBox(height: 22),
        if (checklists.isNotEmpty) ...[
          WebSurface(
            radius: 25,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'อาการตอนเช้า ${checklists.length.clamp(0, 7)} คืนล่าสุด',
                  style: type(14, weight: FontWeight.w600),
                ),
                const SizedBox(height: 20),
                Row(
                  children: [
                    for (final e
                        in records
                            .where((r) => checklists.containsKey(r.id))
                            .take(7)
                            .toList()
                            .reversed)
                      Expanded(
                        child: InkWell(
                          onTap: enabled ? () => onOpen(e) : null,
                          child: Column(
                            children: [
                              Container(
                                width: 12,
                                height: 12,
                                decoration: BoxDecoration(
                                  color:
                                      morningLevels[checklists[e.id]!['level']]!
                                          .$3,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                '${(checklists[e.id]!['symptoms'] as List).length}',
                                style: type(16, weight: FontWeight.w600),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                '${e.createdAt.toLocal().day}',
                                style: type(11, color: muted),
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  'ตัวเลขคือจำนวนอาการตอนเช้า · สีคือผลเช็กลิสต์',
                  style: type(11, color: muted),
                ),
              ],
            ),
          ),
          const SizedBox(height: 26),
        ],
        if (records.isEmpty)
          WebEmpty(onUpload: enabled ? onUpload : null)
        else ...[
          if (chart.isNotEmpty) ...[
            WebSurface(
              radius: 25,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'สัดส่วนเสียงกรนในการบันทึก',
                    style: type(14, weight: FontWeight.w600),
                  ),
                  const SizedBox(height: 20),
                  SizedBox(
                    height: 145,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        for (var i = 0; i < chart.length; i++)
                          Expanded(
                            child: InkWell(
                              onTap: enabled ? () => onOpen(chart[i]) : null,
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.end,
                                children: [
                                  Text(
                                    '${entryPercent(chart[i]).toStringAsFixed(0)}%',
                                    style: type(11, color: muted),
                                  ),
                                  const SizedBox(height: 5),
                                  Container(
                                    width: 25,
                                    height: math.max(
                                      3,
                                      entryPercent(chart[i]).clamp(0, 100) /
                                          100 *
                                          math.max(
                                            3,
                                            145 -
                                                33 *
                                                    MediaQuery.textScalerOf(
                                                      context,
                                                    ).scale(1) -
                                                15,
                                          ),
                                    ),
                                    decoration: BoxDecoration(
                                      color: i == chart.length - 1
                                          ? blue
                                          : const Color(0xffb5cdf7),
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                  ),
                                  const SizedBox(height: 10),
                                  Text(
                                    '${chart[i].createdAt.toLocal().day}',
                                    style: type(11, color: muted),
                                  ),
                                ],
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'บันทึกหลายครั้งในวันเดียวกันจะแสดงแยกกัน ไม่รวมเป็นผลการนอนทั้งคืน',
              style: type(11, color: muted),
            ),
            const SizedBox(height: 12),
          ],
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              OutlinedButton.icon(
                onPressed: enabled ? onExport : null,
                icon: const Glyph('download', size: 17),
                label: const Text('ทั้งหมด JSON'),
              ),
              OutlinedButton.icon(
                onPressed: enabled ? onCsv : null,
                icon: const Glyph('download', size: 17),
                label: const Text('ตาราง CSV'),
              ),
            ],
          ),
          const SizedBox(height: 26),
          Row(
            children: [
              Expanded(
                child: Text(
                  'รายงานทั้งหมด',
                  style: type(17, weight: FontWeight.w600),
                ),
              ),
              Text('${records.length} รายการ', style: type(12, color: muted)),
            ],
          ),
          const SizedBox(height: 14),
          for (final r in records) ...[
            WebRecordCard(
              entry: r,
              onTap: enabled && r.status == 'processed'
                  ? () => onOpen(r)
                  : null,
              onRetry: enabled ? () => onRetry(r) : null,
              onDelete: enabled ? () => onDelete(r) : null,
            ),
            const SizedBox(height: 14),
          ],
        ],
      ],
    );
  }
}

class WebProfile extends StatelessWidget {
  final String name;
  final int count;
  final bool enabled;
  final VoidCallback onBack, onName, onPrivacy, onExplanation, onGuide, onClear;
  final VoidCallback? onAbout;
  const WebProfile({
    super.key,
    required this.name,
    required this.count,
    required this.enabled,
    required this.onBack,
    required this.onName,
    required this.onPrivacy,
    required this.onExplanation,
    required this.onGuide,
    required this.onClear,
    this.onAbout,
  });
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      WebHeader(title: 'โปรไฟล์และการตั้งค่า', onBack: onBack),
      const SizedBox(height: 16),
      WebSurface(
        color: navy,
        radius: 24,
        padding: const EdgeInsets.all(24),
        onTap: enabled ? onName : null,
        child: Row(
          children: [
            const Glyph('user-round', size: 32, color: Color(0xffbfd4ff)),
            const SizedBox(width: 21),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: type(
                      20,
                      color: Colors.white,
                      weight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Snoresens AI · พื้นที่ส่วนตัวบนเครื่องนี้',
                    style: type(12, color: const Color(0xffb8ccec)),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 30),
      for (final item in [
        ('shield-check', 'ความเป็นส่วนตัวและข้อมูล', onPrivacy),
        ('file-text', 'คำอธิบายประกอบการประเมิน', onExplanation),
        ('moon', 'คำแนะนำก่อนเริ่มบันทึก', onGuide),
      ]) ...[
        WebSurface(
          radius: 20,
          onTap: item.$3,
          child: Row(
            children: [
              Glyph(item.$1, size: 22),
              const SizedBox(width: 18),
              Expanded(child: Text(item.$2, style: type(14))),
              const SizedBox(width: 6),
              const Glyph('chevron-right', size: 18, color: muted),
            ],
          ),
        ),
        const SizedBox(height: 14),
      ],
      const SizedBox(height: 14),
      const InfoPanel(
        title: 'ออกแบบเพื่อเข้าใจเสียงระหว่างนอน',
        text: 'วิเคราะห์เสียงบน iPhone ของคุณ\nผลเป็นข้อมูลเบื้องต้น ไม่ใช่การวินิจฉัยโรค',
      ),
      const SizedBox(height: 20),
      Align(
        alignment: Alignment.centerLeft,
        child: TextButton.icon(
          onPressed: enabled ? onClear : null,
          icon: const Glyph('trash-2', size: 20, color: Color(0xffb84155)),
          label: Text(
            'ลบเสียงและผลทั้งหมดบนเครื่องนี้',
            style: type(13, color: const Color(0xffb84155)),
          ),
        ),
      ),
      const SizedBox(height: 8),
      Text(
        '$count รายการบน iPhone นี้ · ถอนแอปจะลบประวัติด้วย',
        style: type(11, color: muted),
      ),
      const SizedBox(height: 8),
      Align(
        alignment: Alignment.centerLeft,
        child: TextButton(
          onPressed: onAbout,
          child: Text(
            'Snoresens AI 0.3.0 · เกี่ยวกับแอป',
            style: type(11, color: muted),
          ),
        ),
      ),
    ],
  );
}

class WebPrepare extends StatelessWidget {
  final VoidCallback onBack, onNext;
  const WebPrepare({super.key, required this.onBack, required this.onNext});
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      WebHeader(title: 'เตรียมก่อนบันทึก', onBack: onBack),
      const SizedBox(height: 16),
      const BedArt(),
      const SizedBox(height: 22),
      for (final item in const [
        ('mic', 'หันไมโครโฟนเข้าหาตัว', 'วางให้มั่นคง และอย่าคลุมไมโครโฟน'),
        (
          'volume-2',
          'เตรียมแบตเตอรี่ให้เพียงพอ',
          'ระหว่างอัดเสียงสามารถล็อกหน้าจอได้',
        ),
        (
          'audio-lines',
          'ลดเสียงรบกวนรอบตัว',
          'เสียงจากคู่นอนอาจมีผลต่อการวิเคราะห์',
        ),
      ]) ...[
        WebSurface(
          radius: 24,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xffe4ebff),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Glyph(item.$1, size: 21),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.$2, style: type(15, weight: FontWeight.w600)),
                    const SizedBox(height: 5),
                    Text(item.$3, style: type(12, color: muted)),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
      ],
      const SizedBox(height: 14),
      Text(
        'หลังคุณหยุดบันทึก ระบบจะเริ่มวิเคราะห์เสียง\nไฟล์ยาววิเคราะห์ทีละส่วน และกลับมาทำต่อได้',
        textAlign: TextAlign.center,
        style: type(12, color: muted, height: 1.9),
      ),
      const SizedBox(height: 38),
      FilledButton(
        onPressed: onNext,
        child: const Text('พร้อมแล้ว ดำเนินการต่อ'),
      ),
    ],
  );
}

class WebConsent extends StatelessWidget {
  final bool accepted, enabled;
  final ValueChanged<bool> onAccept;
  final VoidCallback onBack, onBegin;
  const WebConsent({
    super.key,
    required this.accepted,
    required this.enabled,
    required this.onAccept,
    required this.onBack,
    required this.onBegin,
  });
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      WebHeader(title: 'ความเป็นส่วนตัว', onBack: onBack),
      const SizedBox(height: 26),
      const Center(child: Glyph('shield-check', size: 60)),
      const SizedBox(height: 24),
      Text(
        'เสียงของคุณ เป็นข้อมูลส่วนตัว',
        textAlign: TextAlign.center,
        style: type(22, weight: FontWeight.w700),
      ),
      const SizedBox(height: 14),
      Text(
        'ก่อนเริ่ม โปรดอ่านรายละเอียดการใช้ข้อมูล',
        textAlign: TextAlign.center,
        style: type(13, color: muted),
      ),
      const SizedBox(height: 28),
      WebSurface(
        radius: 26,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('เราบันทึกอะไรบ้าง', style: type(15, weight: FontWeight.w600)),
            const SizedBox(height: 20),
            for (final t in [
              'เสียงในห้องระหว่างช่วงที่คุณกดบันทึก',
              'ใช้เพื่อวิเคราะห์กรนและรูปแบบเสียง',
              'คุณเลือกดูและลบประวัติได้',
              'หากมีคู่นอน ควรแจ้งให้ทราบก่อน',
            ])
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 5),
                child: Text(
                  '•  $t',
                  style: type(12, color: muted, height: 1.9),
                ),
              ),
          ],
        ),
      ),
      const SizedBox(height: 24),
      Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Checkbox(
            key: const ValueKey('record-consent'),
            value: accepted,
            onChanged: enabled ? (v) => onAccept(v ?? false) : null,
            activeColor: blue,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'ฉันยินยอมให้บันทึกและวิเคราะห์เสียง\nตามรายละเอียดข้างต้น',
                style: type(13, height: 1.9),
              ),
            ),
          ),
        ],
      ),
      const SizedBox(height: 28),
      Text(
        'วิเคราะห์บน iPhone ของคุณ\nเสียงและผลเก็บในเครื่อง ไม่ส่งไปเซิร์ฟเวอร์',
        textAlign: TextAlign.center,
        style: type(12, color: muted, height: 1.9),
      ),
      const SizedBox(height: 36),
      FilledButton(
        onPressed: accepted && enabled ? onBegin : null,
        child: const Text('ยินยอมและเริ่มบันทึก'),
      ),
    ],
  );
}

class WebRecording extends StatelessWidget {
  final bool active, paused, stopped, changing;
  final Duration elapsed;
  final String message;
  final VoidCallback onPause, onStop, onHome;
  const WebRecording({
    super.key,
    required this.active,
    required this.paused,
    required this.stopped,
    required this.changing,
    required this.elapsed,
    required this.message,
    required this.onPause,
    required this.onStop,
    required this.onHome,
  });
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Row(
        children: [
          Expanded(
            child: Text('Snoresens AI', style: type(21, color: Colors.white)),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 5),
            decoration: BoxDecoration(
              color: const Color(0xff255260),
              borderRadius: BorderRadius.circular(30),
            ),
            child: Text(
              stopped
                  ? 'หยุดรับเสียง'
                  : paused
                  ? 'พักการบันทึก'
                  : active
                  ? 'กำลังบันทึก'
                  : 'กำลังเตรียมไฟล์',
              style: type(11, color: const Color(0xffa0dcd3)),
            ),
          ),
        ],
      ),
      const SizedBox(height: 62),
      const Center(child: MoonArt(size: 90)),
      const SizedBox(height: 48),
      Text(
        paused ? 'พักการบันทึกไว้' : 'พักผ่อนให้เต็มที่',
        textAlign: TextAlign.center,
        style: type(27, color: Colors.white, weight: FontWeight.w700),
      ),
      const SizedBox(height: 10),
      Text(
        paused ? 'กดบันทึกต่อ เมื่อคุณพร้อม' : 'เรากำลังบันทึกเสียงของคืนนี้',
        textAlign: TextAlign.center,
        style: type(14, color: const Color(0xffbfcfec)),
      ),
      const SizedBox(height: 34),
      FittedBox(
        fit: BoxFit.scaleDown,
        child: Text(
          recordingTime(elapsed),
          style: type(48, color: Colors.white),
        ),
      ),
      const SizedBox(height: 4),
      Text(
        'เวลาที่รับเสียงได้จริง · ไม่นับช่วงพัก',
        textAlign: TextAlign.center,
        style: type(12, color: const Color(0xff9cb3d7)),
      ),
      const SizedBox(height: 36),
      const Padding(
        padding: EdgeInsets.symmetric(horizontal: 22),
        child: DecorativeWave(flat: true, height: 66),
      ),
      const SizedBox(height: 36),
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: .07),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(
          children: [
            const Glyph('info', size: 19, color: Color(0xffa3bee9)),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                message,
                style: type(12, color: const Color(0xffcbdcf8)),
              ),
            ),
          ],
        ),
      ),
      const SizedBox(height: 26),
      Wrap(
        spacing: 12,
        runSpacing: 12,
        children: [
          SizedBox(
            width:
                (MediaQuery.sizeOf(context).width -
                    (MediaQuery.sizeOf(context).width <= 370 ? 36 : 48) -
                    12) /
                2,
            child: FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xff304d79),
                textStyle: type(14, weight: FontWeight.w600),
              ),
              onPressed: changing || stopped ? null : onPause,
              child: Text(paused ? 'บันทึกต่อ' : 'พักการบันทึก'),
            ),
          ),
          SizedBox(
            width:
                (MediaQuery.sizeOf(context).width -
                    (MediaQuery.sizeOf(context).width <= 370 ? 36 : 48) -
                    12) /
                2,
            child: FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: navy,
                textStyle: type(14, weight: FontWeight.w600),
              ),
              onPressed: changing ? null : onStop,
              child: const Text('จบการบันทึก'),
            ),
          ),
        ],
      ),
      const SizedBox(height: 28),
      Text(
        'ล็อกจอระหว่างอัดได้ เมื่อมีสายโทรเข้า\nหรือเปลี่ยนอุปกรณ์เสียง ให้กลับมาตรวจสถานะ',
        textAlign: TextAlign.center,
        style: type(12, color: const Color(0xff9cb3d7), height: 1.85),
      ),
      const SizedBox(height: 8),
      Center(
        child: TextButton(
          onPressed: onHome,
          child: Text(
            'กลับหน้าหลัก',
            style: type(12, color: const Color(0xffbfd4ff)),
          ),
        ),
      ),
    ],
  );
}

/// Owns its controller until the dialog route's exit animation is finished.
class NameDialog extends StatefulWidget {
  final String name;
  const NameDialog({super.key, required this.name});
  @override
  State<NameDialog> createState() => _NameDialogState();
}

class _NameDialogState extends State<NameDialog> {
  late final controller = TextEditingController(text: widget.name);
  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('ชื่อที่แสดง'),
    content: TextField(
      controller: controller,
      maxLength: 50,
      decoration: const InputDecoration(labelText: 'ชื่อของคุณ'),
      autofocus: true,
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('ยกเลิก'),
      ),
      FilledButton(
        onPressed: () => Navigator.pop(context, controller.text.trim()),
        child: const Text('บันทึกชื่อ'),
      ),
    ],
  );
}
