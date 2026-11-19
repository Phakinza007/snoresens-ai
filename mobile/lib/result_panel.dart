import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:audioplayers/audioplayers.dart';
import 'package:file_picker/file_picker.dart';
import 'package:material_ui/material_ui.dart';

import 'inference.dart';
import 'web_style.dart';
import 'web_pages.dart' show durationLabel;

String metric(dynamic value, [int digits = 1]) =>
    value is num ? value.toStringAsFixed(digits) : '—';
String audioTime(double seconds) {
  final hundredths = max(0, (seconds * 100).round()), whole = hundredths ~/ 100;
  return '${(whole ~/ 3600).toString().padLeft(2, '0')}:${(whole ~/ 60 % 60).toString().padLeft(2, '0')}:${(whole % 60).toString().padLeft(2, '0')}.${(hundredths % 100).toString().padLeft(2, '0')}';
}

String timelineCsv(List<Map<String, dynamic>> rows) {
  if (rows.isEmpty) return '';
  final keys = rows.first.keys.toList();
  String cell(dynamic value) =>
      '"${(value?.toString() ?? '').replaceAll('"', '""')}"';
  return '\uFEFF${[keys.map(cell).join(','), ...rows.map((row) => keys.map((key) => cell(row[key])).join(','))].join('\r\n')}';
}

/// The website's project-defined composite, not a health or sleep-quality score.
double? experimentalAudioScore(SnoreResult item) {
  final d = item.seconds, s = item.snoreSeconds, events = item.snoreEvents;
  if (!d.isFinite ||
      d <= 0 ||
      !s.isFinite ||
      s < 0 ||
      s > d ||
      events.length < 2) {
    return null;
  }
  var count = 0;
  for (var i = 0; i < events.length; i++) {
    final start = (events[i]['start_seconds'] as num).toDouble(),
        end = (events[i]['end_seconds'] as num).toDouble();
    if (!start.isFinite ||
        !end.isFinite ||
        start < 0 ||
        end <= start ||
        end > d ||
        (i > 0 && start < (events[i - 1]['end_seconds'] as num))) {
      return null;
    }
    if (i > 0) {
      final interval = start - (events[i - 1]['start_seconds'] as num);
      if (interval > 10 && interval < 100) count++;
    }
  }
  return ((100 - 50 * s / d - 50 * count / (events.length - 1)) * 10).round() /
      10;
}

class ResultPanel extends StatefulWidget {
  final SnoreResult result;
  final VoidCallback? onDelete, onReanalyze, onExplanation;
  final Widget? checklist;
  final bool enablePlayback;
  const ResultPanel({
    super.key,
    required this.result,
    this.onDelete,
    this.onReanalyze,
    this.onExplanation,
    this.checklist,
    this.enablePlayback = true,
  });
  @override
  State<ResultPanel> createState() => _ResultPanelState();
}

class _ResultPanelState extends State<ResultPanel> {
  AudioPlayer? player;
  StreamSubscription<Duration>? positionSubscription;
  StreamSubscription<PlayerState>? stateSubscription;
  double position = 0;
  int eventPage = 0;
  bool playing = false,
      playerReady = false,
      details = false,
      allEvents = false,
      mutedAudio = false;
  String? error;
  final eventsKey = GlobalKey();
  @override
  void initState() {
    super.initState();
    if (widget.enablePlayback) {
      player = AudioPlayer();
      positionSubscription = player!.onPositionChanged.listen((v) {
        if (mounted) setState(() => position = v.inMilliseconds / 1000);
      });
      stateSubscription = player!.onPlayerStateChanged.listen((v) {
        if (mounted) setState(() => playing = v == PlayerState.playing);
      });
      _prepare();
    }
  }

  Future<void> _prepare() async {
    if (widget.result.audioPath == null) return;
    try {
      await player!.setSourceDeviceFile(widget.result.audioPath!);
      if (mounted) setState(() => playerReady = true);
    } catch (e) {
      if (mounted) setState(() => error = 'เปิดเสียงไม่ได้: $e');
    }
  }

  Future<void> _seek(double value) async {
    if (!playerReady) return;
    final t = value.clamp(0, widget.result.seconds).toDouble();
    try {
      await player!.seek(Duration(milliseconds: (t * 1000).round()));
      if (mounted) setState(() => position = t);
    } catch (e) {
      if (mounted) setState(() => error = 'เลื่อนเสียงไม่ได้: $e');
    }
  }

  Future<void> _toggle() async {
    if (!playerReady) return;
    try {
      if (playing) {
        await player!.pause();
      } else {
        if (player!.state == PlayerState.completed) {
          await player!.seek(Duration.zero);
        }
        await player!.resume();
      }
    } catch (e) {
      if (mounted) setState(() => error = 'เล่นเสียงไม่ได้: $e');
    }
  }

  Future<void> _volume() async {
    if (!playerReady) return;
    try {
      await player!.setVolume(mutedAudio ? 1 : 0);
      if (mounted) setState(() => mutedAudio = !mutedAudio);
    } catch (e) {
      if (mounted) setState(() => error = 'ปรับเสียงไม่ได้: $e');
    }
  }

  Future<void> _export(String kind) async {
    try {
      final item = widget.result;
      final Uint8List bytes;
      if (kind == 'wav') {
        if (item.audioPath == null) throw StateError('ไม่มีไฟล์เสียงเดิม');
        bytes = await File(item.audioPath!).readAsBytes();
      } else {
        bytes = Uint8List.fromList(
          utf8.encode(
            kind == 'csv'
                ? timelineCsv(item.timeline)
                : const JsonEncoder.withIndent('  ').convert(item.toJson()),
          ),
        );
      }
      await FilePicker.saveFile(
        fileName: 'snoresens-analysis.$kind',
        bytes: bytes,
        mimeType: kind == 'csv'
            ? 'text/csv'
            : kind == 'wav'
            ? 'audio/wav'
            : 'application/json',
      );
    } catch (e) {
      if (mounted) setState(() => error = 'ส่งออกไม่ได้: $e');
    }
  }

  @override
  void dispose() {
    positionSubscription?.cancel();
    stateSubscription?.cancel();
    player?.dispose();
    super.dispose();
  }

  Widget _stat(String label, String value) => Expanded(
    child: WebSurface(
      radius: 22,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: type(12, color: muted)),
          const SizedBox(height: 11),
          Text(value, style: type(22, weight: FontWeight.w600, height: 1.4)),
        ],
      ),
    ),
  );
  Widget _measure(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(label, style: type(12, color: muted)),
        ),
        const SizedBox(width: 12),
        Flexible(
          child: Text(value, textAlign: TextAlign.right, style: type(12)),
        ),
      ],
    ),
  );
  Widget _timeline(double start, double end, {bool zoom = false}) =>
      LayoutBuilder(
        builder: (context, c) => GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTapDown: playerReady
              ? (d) => _seek(
                  start +
                      (d.localPosition.dx / c.maxWidth).clamp(0, 1) *
                          (end - start),
                )
              : null,
          child: Semantics(
            label: zoom ? 'เลือกเวลาในกราฟละเอียด' : 'เลือกเวลาจากกราฟเสียง',
            value: audioTime(position),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: SizedBox(
                height: zoom ? 44 : 48,
                width: double.infinity,
                child: CustomPaint(
                  painter: PreciseTimelinePainter(
                    widget.result.timeline,
                    start,
                    end,
                    position,
                    zoom: zoom,
                  ),
                ),
              ),
            ),
          ),
        ),
      );
  @override
  Widget build(BuildContext context) {
    final item = widget.result,
        pct = item.percent.clamp(0, 100),
        start = min(
          max(0.0, item.seconds - 10),
          (position / 10).floor() * 10.0,
        ),
        end = min(item.seconds, start + 10),
        frequency = (item.audioPatterns['frequency_summary'] as Map?) ?? {},
        rhythm = (item.audioPatterns['rhythm_summary'] as Map?) ?? {};
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'โมเดลรุ่น 2 · เพิ่มตัวอย่างเสียงหายใจ · ตรวจทุก ${item.summary['analysis_hop_seconds'] ?? .02} วินาที',
          style: type(12, color: muted),
        ),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton(
            onPressed: widget.onReanalyze,
            child: const Text('วิเคราะห์ใหม่แบบละเอียด'),
          ),
        ),
        const SizedBox(height: 8),
        WebSurface(
          color: navy,
          radius: 26,
          padding: const EdgeInsets.symmetric(vertical: 22, horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'ผลประเมินจากเสียง',
                style: type(12, color: const Color(0xffc0d1ef)),
              ),
              const SizedBox(height: 14),
              BluePill('พบกรน ${metric(pct)}%', amber: true),
              const SizedBox(height: 15),
              Text(
                item.snoreSeconds > 0
                    ? 'พบช่วงเสียงคล้ายกรน'
                    : 'ไม่พบเสียงกรนในไฟล์นี้',
                style: type(19, color: Colors.white, weight: FontWeight.w700),
              ),
              const SizedBox(height: 5),
              Text(
                item.snoreSeconds > 0
                    ? 'เลือกฟังช่วงเสียง เพื่อทำความเข้าใจผล'
                    : 'ผลอาจขึ้นกับคุณภาพเสียงและตำแหน่งไมโครโฟน',
                style: type(12, color: const Color(0xffb9ccec)),
              ),
            ],
          ),
        ),
        if (widget.checklist != null) ...[
          const SizedBox(height: 16),
          widget.checklist!,
        ],
        const SizedBox(height: 16),
        IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _stat('ระยะเวลาบันทึก', durationLabel(item.seconds)),
              const SizedBox(width: 14),
              _stat('เสียงกรน', durationLabel(item.snoreSeconds)),
            ],
          ),
        ),
        const SizedBox(height: 22),
        Row(
          children: [
            Expanded(
              child: Text(
                'สัดส่วนเสียง',
                style: type(16, weight: FontWeight.w600),
              ),
            ),
            Text(
              audioTime(item.seconds).split('.').first,
              style: type(12, color: muted),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Semantics(
          label: 'เสียงกรน ${metric(pct)} เปอร์เซ็นต์',
          child: ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Container(
              height: 15,
              color: const Color(0xffa8c5f3),
              alignment: Alignment.centerLeft,
              child: FractionallySizedBox(
                widthFactor: pct / 100,
                child: Container(color: blue),
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('■ กรน ${metric(pct)}%', style: type(12, color: blue)),
            Text(
              '■ ไม่พบกรน ${metric(100 - pct)}%',
              style: type(12, color: muted),
            ),
          ],
        ),
        const SizedBox(height: 22),
        WebSurface(
          radius: 18,
          padding: const EdgeInsets.all(17),
          onTap: () => Scrollable.ensureVisible(
            eventsKey.currentContext!,
            duration: const Duration(milliseconds: 250),
          ),
          child: Row(
            children: [
              const Glyph('chart-no-axes-column'),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'พบช่วงเสียงกรน ${item.events} ช่วง',
                      style: type(13, weight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'เลือกช่วงเวลาเพื่อย้อนฟังเสียง',
                      style: type(11, color: muted),
                    ),
                  ],
                ),
              ),
              const Glyph('chevron-right', size: 19),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Text(
          '${item.name}\nค่านี้ใช้เวลาที่บันทึก ไม่ใช่เวลาที่หลับจริง\nการประเมินสุขภาพต้องอาศัยข้อมูลเพิ่มเติม',
          style: type(12, color: muted, height: 1.85),
        ),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton(
            onPressed: widget.onExplanation,
            child: const Text('ดูคำอธิบายประกอบการประเมิน'),
          ),
        ),
        const SizedBox(height: 18),
        WebSurface(
          padding: const EdgeInsets.all(19),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'ฟังเสียงและดูช่วงที่ตรวจพบ',
                style: type(15, weight: FontWeight.w700),
              ),
              const SizedBox(height: 12),
              Container(
                decoration: BoxDecoration(
                  color: const Color(0xfff1f3f4),
                  borderRadius: BorderRadius.circular(28),
                ),
                child: Row(
                  children: [
                    IconButton(
                      tooltip: playing ? 'พักเสียง' : 'เล่นเสียง',
                      onPressed: playerReady ? _toggle : null,
                      icon: Glyph(
                        playing ? 'pause' : 'play',
                        size: 20,
                        color: ink,
                      ),
                    ),
                    Expanded(
                      child: Text(
                        '${audioTime(position).split('.').first} / ${audioTime(item.seconds).split('.').first}',
                        style: type(12),
                      ),
                    ),
                    IconButton(
                      tooltip: mutedAudio ? 'เปิดเสียง' : 'ปิดเสียง',
                      onPressed: playerReady ? _volume : null,
                      icon: Glyph(
                        'volume-2',
                        size: 20,
                        color: mutedAudio ? muted : ink,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              _timeline(0, item.seconds),
              const SizedBox(height: 18),
              Wrap(
                alignment: WrapAlignment.spaceBetween,
                spacing: 8,
                runSpacing: 4,
                children: [
                  Text(
                    'ซูมละเอียด · ช่วงละ ${item.summary['analysis_hop_seconds'] ?? .02} วินาที',
                    style: type(11, weight: FontWeight.w700),
                  ),
                  Text(
                    '${audioTime(start)}–${audioTime(end)}',
                    style: type(10, color: muted),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              _timeline(start, end, zoom: true),
              const SizedBox(height: 8),
              Text(
                'น้ำเงิน: ตรวจพบกรน · เทา: ไม่พบกรน · เลื่อนเวลาเพื่อดูช่วงอื่น',
                style: type(10, color: muted),
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(audioTime(position), style: type(11, color: muted)),
                  Text(audioTime(item.seconds), style: type(11, color: muted)),
                ],
              ),
              Slider(
                padding: EdgeInsets.zero,
                value: position.clamp(0, item.seconds).toDouble(),
                min: 0,
                max: max(.001, item.seconds),
                onChanged: playerReady ? _seek : null,
                semanticFormatterCallback: audioTime,
              ),
              Column(
                key: eventsKey,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  for (final e
                      in item.snoreEvents
                          .skip(allEvents ? eventPage * 20 : 0)
                          .take(allEvents ? 20 : 6)) ...[
                    const SizedBox(height: 8),
                    Container(
                      decoration: BoxDecoration(
                        color: paper,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: const Color(0xffe4eafb)),
                      ),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(12),
                        onTap: playerReady
                            ? () =>
                                  _seek((e['start_seconds'] as num).toDouble())
                            : null,
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Row(
                            children: [
                              const Glyph('play', size: 17),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  'กรน · ${audioTime((e['start_seconds'] as num).toDouble())}–${audioTime((e['end_seconds'] as num).toDouble())}',
                                  style: type(11),
                                ),
                              ),
                              const SizedBox(width: 6),
                              Text(
                                '${metric(e['duration_seconds'], 2)} วิ.',
                                style: type(11, color: muted),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                  if (item.snoreEvents.isEmpty)
                    Text(
                      'ไม่มีช่วงเสียงกรนที่ตรวจพบ',
                      style: type(12, color: muted),
                    ),
                  if (item.snoreEvents.length > 6)
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton(
                        onPressed: () => setState(() {
                          allEvents = !allEvents;
                          eventPage = 0;
                        }),
                        child: Text(
                          allEvents ? 'แสดงน้อยลง' : 'แสดงช่วงเสียงทั้งหมด',
                        ),
                      ),
                    ),
                ],
              ),
              if (error != null) ...[
                const SizedBox(height: 12),
                Text(error!, style: type(12, color: const Color(0xffb84155))),
              ],
              if (allEvents && item.snoreEvents.length > 20)
                Wrap(
                  alignment: WrapAlignment.center,
                  spacing: 12,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    TextButton(
                      onPressed: eventPage > 0
                          ? () => setState(() => eventPage--)
                          : null,
                      child: const Text('ก่อนหน้า'),
                    ),
                    Text(
                      '${eventPage + 1}/${(item.snoreEvents.length / 20).ceil()}',
                      style: type(12, color: muted),
                    ),
                    TextButton(
                      onPressed: (eventPage + 1) * 20 < item.snoreEvents.length
                          ? () => setState(() => eventPage++)
                          : null,
                      child: const Text('ถัดไป'),
                    ),
                  ],
                ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: () => setState(() => details = !details),
            icon: Glyph(details ? 'chevron-left' : 'chevron-right', size: 16),
            label: const Text('ดูรายละเอียดการวัดเสียง'),
          ),
        ),
        if (details) ...[
          _measure(
            'ระดับเสียงมัธยฐาน',
            '${metric(item.summary['snore_median_rms_dbfs'])} dBFS',
          ),
          _measure(
            'ช่วงกรนยาวที่สุด',
            '${metric(item.summary['longest_snore_event_seconds'])} วิ.',
          ),
          _measure(
            'คะแนนเสียงกรนรวม · เกณฑ์ทดลอง',
            '${metric(experimentalAudioScore(item))} / 100',
          ),
          _measure(
            'ความถี่เด่น',
            '${metric(frequency['median_dominant_frequency_hz'], 0)} Hz',
          ),
          _measure('CV ระยะห่างช่วงกรน', metric(rhythm['interval_cv'], 3)),
          Text(
            'dBFS คือความดังสัมพัทธ์ในไฟล์ คะแนนรวมเป็นเกณฑ์ทดลองของโครงการ ไม่ใช่คะแนนสุขภาพหรือความเสี่ยงโรค หากข้อมูลไม่พอจะแสดง —',
            style: type(11, color: muted),
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 125,
            width: double.infinity,
            child: CustomPaint(
              painter: AudioTimelinePainter(item.timeline, item.seconds),
            ),
          ),
          const SizedBox(height: 16),
        ],
        const SizedBox(height: 16),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final format in [
              ('json', 'ผล JSON'),
              ('csv', 'Timeline CSV'),
              ('wav', 'เสียง WAV'),
            ])
              OutlinedButton.icon(
                onPressed: format.$1 == 'wav' && item.audioPath == null
                    ? null
                    : () => _export(format.$1),
                icon: const Glyph('download', size: 17),
                label: Text(format.$2),
              ),
          ],
        ),
        const SizedBox(height: 18),
        if (widget.onDelete != null)
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: widget.onDelete,
              icon: const Glyph('trash-2', color: Color(0xffb84155)),
              label: Text(
                'ลบผลการบันทึกนี้',
                style: type(13, color: const Color(0xffb84155)),
              ),
            ),
          ),
      ],
    );
  }
}

class PreciseTimelinePainter extends CustomPainter {
  final List<Map<String, dynamic>> rows;
  final double start, end, position;
  final bool zoom;
  PreciseTimelinePainter(
    this.rows,
    this.start,
    this.end,
    this.position, {
    this.zoom = false,
  });
  @override
  void paint(Canvas c, Size s) {
    c.drawRect(Offset.zero & s, Paint()..color = const Color(0xffe7edf8));
    if (end <= start) return;
    if (zoom) {
      for (var i = 1; i < 10; i++) {
        c.drawLine(
          Offset(i * s.width / 10, 0),
          Offset(i * s.width / 10, s.height),
          Paint()..color = line,
        );
      }
    }
    for (final row in rows) {
      final a = (row['start_seconds'] as num).toDouble(),
          b = a + (row['duration_seconds'] as num).toDouble();
      if (row['prediction'] != 'snore' || b <= start || a >= end) continue;
      final left = (max(start, a) - start) / (end - start) * s.width,
          right = (min(end, b) - start) / (end - start) * s.width;
      c.drawRect(
        Rect.fromLTRB(
          left,
          zoom ? 0 : 7,
          right,
          zoom ? s.height : s.height - 7,
        ),
        Paint()..color = blue,
      );
    }
    if (position >= start && position <= end) {
      final x = (position - start) / (end - start) * s.width;
      c.drawLine(
        Offset(x, 0),
        Offset(x, s.height),
        Paint()
          ..color = ink
          ..strokeWidth = 1,
      );
    }
  }

  @override
  bool shouldRepaint(covariant PreciseTimelinePainter old) =>
      old.rows != rows ||
      old.position != position ||
      old.start != start ||
      old.end != end;
}

class AudioTimelinePainter extends CustomPainter {
  final List<Map<String, dynamic>> rows;
  final double seconds;
  AudioTimelinePainter(this.rows, this.seconds);
  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(
      Offset.zero & size,
      Paint()..color = const Color(0xffe7edf8),
    );
    if (rows.isEmpty || seconds <= 0) return;
    final count = min(700, rows.length);
    // Paint precise time spans directly; amplitude bins must not widen labels.
    for (final row in rows.where((r) => r['prediction'] == 'snore')) {
      final start = (row['start_seconds'] as num).toDouble(),
          duration = (row['duration_seconds'] as num).toDouble();
      canvas.drawRect(
        Rect.fromLTWH(
          start / seconds * size.width,
          0,
          duration / seconds * size.width,
          25,
        ),
        Paint()..color = const Color(0xff3157f5),
      );
    }
    final low = List<double?>.filled(count, null),
        high = List<double?>.filled(count, null);
    for (final row in rows) {
      final first = ((row['start_seconds'] as num) / seconds * count)
          .floor()
          .clamp(0, count - 1)
          .toInt();
      final last =
          (((row['start_seconds'] as num) + (row['duration_seconds'] as num)) /
                  seconds *
                  count)
              .ceil() -
          1;
      for (var i = first; i <= min(last, count - 1); i++) {
        final level = (row['rms_dbfs'] as num?)?.toDouble();
        if (level != null) {
          low[i] = low[i] == null ? level : min(low[i]!, level);
          high[i] = high[i] == null ? level : max(high[i]!, level);
        }
      }
    }
    final width = size.width / count;
    for (var i = 0; i < count; i++) {
      if (high[i] != null) {
        double y(double value) =>
            35.0 + (-value / 90).clamp(0.0, 1.0).toDouble() * 90.0;
        canvas.drawRect(
          Rect.fromLTWH(
            i * width,
            y(high[i]!),
            width + 0.5,
            max(2.0, y(low[i]!) - y(high[i]!)),
          ),
          Paint()..color = const Color(0xff3e6d88),
        );
      }
    }
  }

  @override
  bool shouldRepaint(covariant AudioTimelinePainter old) =>
      old.rows != rows || old.seconds != seconds;
}
