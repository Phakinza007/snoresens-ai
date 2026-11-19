import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart'
    show LicenseRegistry, LicenseEntryWithLineBreaks;
import 'package:material_ui/material_ui.dart';
import 'package:file_picker/file_picker.dart';
import 'package:path_provider/path_provider.dart';

import 'capture_session.dart';
import 'recording_store.dart';
import 'recording_processor.dart';
import 'inference.dart';
import 'result_panel.dart';
import 'web_style.dart';
import 'web_pages.dart';
import 'morning_checklist.dart';

void main() {
  LicenseRegistry.addLicense(() async* {
    for (final item in [
      ('Noto Sans Thai', 'FONT-LICENSE.txt'),
      ('Lucide Static', 'LUCIDE-LICENSE.txt'),
    ]) {
      yield LicenseEntryWithLineBreaks([
        item.$1,
      ], await rootBundle.loadString('assets/ui/${item.$2}'));
    }
  });
  runApp(const SanorApp());
}

class SanorApp extends StatelessWidget {
  const SanorApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Snoresens AI',
    debugShowCheckedModeBanner: false,
    theme: snoresensTheme(),
    home: const HomePage(),
  );
}

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
    this.documents,
    this.engine,
    this.recorder,
    this.enablePlayback = true,
  });
  final Future<Directory> Function()? documents;
  final SnoreEngine? engine;
  final CaptureRecorder? recorder;
  final bool enablePlayback;
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with WidgetsBindingObserver {
  late final SnoreEngine engine;
  RecordingStore? store;
  CaptureSession? capture;
  List<RecordingEntry> entries = [];
  Map<String, dynamic> preferences = {};
  bool ready = false, busy = false, consent = false;
  String page = 'home', message = 'กำลังเตรียมโมเดลเสียง…';
  RecordingEntry? selectedParent, selectedPart;
  SnoreResult? result;
  AppLifecycleState lifecycle = AppLifecycleState.resumed;
  List<RecordingEntry> get records =>
      entries.where((e) => e.parentId == null).toList();
  bool get active => capture?.active == true;
  bool get locked => busy || capture?.changing == true;
  @override
  void initState() {
    super.initState();
    engine = widget.engine ?? SnoreEngine();
    WidgetsBinding.instance.addObserver(this);
    _load();
  }

  Future<void> _load() async {
    try {
      final dir =
          await (widget.documents?.call() ??
              getApplicationDocumentsDirectory());
      final s = RecordingStore(Directory('${dir.path}/Snoresens'));
      await s.root.create(recursive: true);
      store = s;
      await s.recoverInterrupted();
      preferences = await s.readPreferences();
      if (!mounted) return;
      capture = CaptureSession(s, recorder: widget.recorder)
        ..addListener(_changed);
      await _refresh();
      if (!mounted) return;
      await engine.load();
      if (!mounted) {
        engine.close();
        return;
      }
      setState(() {
        ready = true;
        message = '';
      });
    } catch (e) {
      if (mounted) setState(() => message = 'เตรียมแอปไม่สำเร็จ: $e');
    }
  }

  Future<void> _refresh() async {
    final s = store;
    if (s == null) return;
    final list = await s.list();
    if (mounted) setState(() => entries = list);
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  void _go(String target) {
    if (mounted) setState(() => page = target);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    lifecycle = state;
    if (state == AppLifecycleState.resumed) _refresh();
  }

  void _nav(int tab) {
    if (tab == 1) {
      final done = records.where((e) => e.status == 'processed');
      if (done.isEmpty) {
        _go('report');
      } else {
        _openParts(done.first);
      }
    } else {
      _go(const ['home', 'report', 'history', 'profile'][tab]);
    }
  }

  void _beginFlow() {
    if (active) {
      _go('record');
    } else {
      setState(() => consent = false);
      _go('prepare');
    }
  }

  Future<void> _start() async {
    if (!consent || locked || !ready) return;
    await capture?.start();
    await _refresh();
    if (!mounted) return;
    if (active) {
      _go('record');
    } else {
      setState(() => message = capture?.message ?? 'เริ่มอัดไม่ได้');
    }
  }

  Future<void> _stop() async {
    final e = await capture?.stop();
    await _refresh();
    if (!mounted) return;
    if (e != null) {
      if (lifecycle == AppLifecycleState.resumed) {
        await _process(e, afterRecording: true);
      } else {
        setState(() => message = 'เก็บเสียงแล้ว กลับมากดวิเคราะห์ต่อในประวัติ');
      }
    }
  }

  Future<void> _pick() async {
    if (locked || active || !ready) return;
    setState(() => busy = true);
    RecordingEntry? imported;
    try {
      final f = await FilePicker.pickFile(
        type: FileType.custom,
        allowedExtensions: ['wav'],
      );
      if (f == null) return;
      final s = store!,
          id = 'import_${DateTime.now().microsecondsSinceEpoch}',
          path = s.audioPath(id);
      if (f.path != null) {
        await File(f.path!).copy(path);
      } else {
        await File(path).writeAsBytes(await f.readAsBytes(), flush: true);
      }
      imported = RecordingEntry(
        id: id,
        name: f.name,
        createdAt: DateTime.now(),
        status: 'pending',
      );
      await s.save(imported);
      await _refresh();
    } catch (e) {
      if (mounted) setState(() => message = 'เปิดไฟล์ไม่ได้: $e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
    if (imported != null && mounted) await _process(imported);
  }

  Future<void> _sample() async {
    if (locked || active || !ready) return;
    setState(() => busy = true);
    RecordingEntry? e;
    try {
      final bytes = await rootBundle.load('assets/ui/sample.wav');
      final id = 'sample_${DateTime.now().microsecondsSinceEpoch}';
      e = RecordingEntry(
        id: id,
        name: 'เสียงตัวอย่าง · test_snore_16k.wav',
        createdAt: DateTime.now(),
        status: 'pending',
      );
      await File(store!.audioPath(id))
          .writeAsBytes(bytes.buffer.asUint8List(), flush: true);
      await store!.save(e);
      await _refresh();
    } catch (error) {
      if (mounted) setState(() => message = 'เปิดเสียงตัวอย่างไม่ได้: $error');
    } finally {
      if (mounted) setState(() => busy = false);
    }
    if (e != null && mounted) await _process(e);
  }

  Future<void> _process(
    RecordingEntry entry, {
    bool force = false,
    bool afterRecording = false,
  }) async {
    if (locked || !ready || active) return;
    setState(() => busy = true);
    var finished = false;
    try {
      final job = RecordingProcessor(
        store!,
        analyze: (name, bytes, {audioPath, shouldContinue}) => engine.analyze(
          name,
          bytes,
          audioPath: audioPath,
          shouldContinue: shouldContinue,
        ),
        foreground: () => mounted && lifecycle == AppLifecycleState.resumed,
        onProgress: (part) {
          if (mounted) {
            setState(() => message = 'กำลังวิเคราะห์เสียง · ส่วนที่ $part');
          }
        },
      );
      finished = await job.process(entry, force: force);
      if (mounted) {
        setState(
          () => message = finished
              ? ''
              : 'พักการวิเคราะห์ กลับมากดวิเคราะห์ต่อในประวัติได้',
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => message = 'วิเคราะห์ไม่สำเร็จ เก็บไฟล์เสียงไว้แล้ว: $e');
      }
    } finally {
      await _refresh();
      if (mounted) {
        setState(() => busy = false);
      } else {
        engine.close();
      }
    }
    if (!mounted) return;
    if (finished) {
      final root = records.firstWhere((e) => e.id == entry.id);
      if (afterRecording) {
        setState(() {
          selectedParent = root;
          page = 'checklist';
        });
      } else {
        await _openParts(root);
      }
    } else if (!active && page == 'record') {
      _go('history');
    }
  }

  Future<void> _open(RecordingEntry part) async {
    if (locked || active) return;
    setState(() => busy = true);
    try {
      final data = await store!.readAnalysis(part.id);
      final r = SnoreResult.fromJson(
        data,
        audioPath: store!.audioPath(part.id),
      );
      if (mounted) {
        setState(() {
          selectedPart = part;
          result = r;
          page = 'report';
        });
      }
    } catch (e) {
      if (mounted) setState(() => message = 'เปิดรายงานไม่ได้: $e');
    } finally {
      if (mounted) {
        setState(() => busy = false);
      } else {
        engine.close();
      }
    }
  }

  Future<void> _openParts(RecordingEntry parent) async {
    if (locked || active) return;
    setState(() => selectedParent = parent);
    final parts =
        entries
            .where((e) => e.parentId == parent.id && e.status == 'done')
            .toList()
          ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
    if (parts.length == 1) {
      await _open(parts.single);
    } else {
      _go('parts');
    }
  }

  Future<bool> _confirm(String title, String text) async =>
      await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
          title: Text(title),
          content: Text(text),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c, false),
              child: const Text('ยกเลิก'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(c, true),
              child: const Text('ลบ'),
            ),
          ],
        ),
      ) ??
      false;
  Future<void> _delete(RecordingEntry e) async {
    if (locked || active) return;
    if (!await _confirm(
      'ลบเสียงและผลนี้?',
      'ลบการบันทึกต้นฉบับและส่วนย่อยที่เกี่ยวข้อง การลบนี้ย้อนกลับไม่ได้',
    )) {
      return;
    }
    if (!mounted) return;
    setState(() => busy = true);
    try {
      for (final child in entries.where((x) => x.parentId == e.id)) {
        await store!.delete(child.id);
      }
      await store!.delete(e.id);
      final checks = Map<String, dynamic>.from(preferences['checklists'] ?? {});
      checks.remove(e.id);
      preferences = {...preferences, 'checklists': checks};
      await store!.savePreferences(preferences);
      if (mounted) {
        setState(() {
          result = null;
          selectedParent = null;
          selectedPart = null;
          page = 'history';
        });
      }
    } catch (error) {
      if (mounted) setState(() => message = 'ลบไฟล์ไม่ได้: $error');
    } finally {
      await _refresh();
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _clear() async {
    if (locked || active) return;
    if (!await _confirm(
      'ลบข้อมูลทั้งหมด?',
      'ลบเสียง ประวัติ ผลวิเคราะห์ และคำตอบเช็กลิสต์ทั้งหมดบน iPhone นี้ ไฟล์ที่ส่งออกแล้วจะยังอยู่',
    )) {
      return;
    }
    if (!mounted) return;
    setState(() => busy = true);
    try {
      await store!.clearRecordings();
      preferences = {...preferences, 'checklists': <String, dynamic>{}};
      await store!.savePreferences(preferences);
      result = null;
      selectedParent = null;
      selectedPart = null;
      await _refresh();
    } catch (e) {
      if (mounted) setState(() => message = 'ลบข้อมูลไม่ได้: $e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _exportHistory({bool csv = false}) async {
    try {
      final data = csv
          ? timelineCsv(
              records
                  .map(
                    (e) => {
                      'name': e.name,
                      'created_at': e.createdAt.toIso8601String(),
                      'recording_seconds': e.summary?['recording_seconds'],
                      'detected_snore_seconds':
                          e.summary?['detected_snore_seconds'],
                      'snore_percent_of_recording':
                          e.summary?['snore_percent_of_recording'],
                      'model_version': e.summary?['model_version'],
                      'status': e.status,
                    },
                  )
                  .toList(),
            )
          : const JsonEncoder.withIndent('  ').convert({
              'app_version': '0.3.0',
              'records': entries.map((e) => e.toJson()).toList(),
              'checklists': preferences['checklists'] ?? {},
            });
      await FilePicker.saveFile(
        fileName: 'snoresens-history.${csv ? 'csv' : 'json'}',
        mimeType: csv ? 'text/csv' : 'application/json',
        bytes: utf8.encode(data),
      );
    } catch (e) {
      if (mounted) setState(() => message = 'ส่งออกไม่ได้: $e');
    }
  }

  void _info(String title, String text) {
    showDialog<void>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(title),
        content: SingleChildScrollView(
          child: Text(text, style: type(14, height: 1.9)),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c),
            child: const Text('เข้าใจแล้ว'),
          ),
        ],
      ),
    );
  }

  void _privacy() => _info(
    'ความเป็นส่วนตัวและข้อมูล',
    'เสียงและโมเดลประมวลผลบน iPhone นี้ ไม่ส่งเสียงไปบริการวิเคราะห์ภายนอก\n\nประวัติ ผลวิเคราะห์ และเสียงเก็บในพื้นที่ Documents ของแอป และแชร์ WAV ผ่าน Files ได้ ผู้ที่เข้าถึงเครื่องหรือไฟล์เหล่านั้นอาจเปิดฟังได้\n\nลบได้จากรายงานหรือเมนูลบข้อมูลทั้งหมด การถอนแอปจะลบประวัติด้วย ไฟล์ที่เคยส่งออกยังอยู่ในตำแหน่งที่คุณเลือก',
  );
  void _explanation() => _info(
    'เข้าใจผลการวิเคราะห์',
    'โมเดลแยกเสียงคล้ายกรนกับไม่กรนเป็นช่วงสั้น ๆ แล้วรวมช่วงที่ต่อเนื่องกัน จำนวนช่วงไม่เท่ากับจำนวนครั้งที่กรนจริงเสมอไป\n\nสัดส่วนกรน = เวลาที่ตรวจพบกรน ÷ เวลาที่บันทึก ไม่ใช่เวลาที่หลับ ความดัง dBFS เป็นค่าสัมพัทธ์ในไฟล์\n\nมีการตัดช่วงเสียงเบาตามระดับเสียง อาจพลาดกรนเบามาก ควรฟังเสียงประกอบ ผลไม่ใช้วินิจฉัยภาวะหยุดหายใจขณะหลับ',
  );
  void _checkInfo() => _info(
    'เกณฑ์ของเช็กลิสต์',
    'เช็กลิสต์ใช้เกณฑ์เดียวกับเว็บ เป็นการรวมกฎของโครงการที่ยังไม่ผ่านการตรวจสอบทางคลินิก ไม่ใช่การวินิจฉัย\n\nหากมีผู้เห็นว่าหยุดหายใจขณะหลับ หรือสะดุ้งตื่นเพราะสำลัก/หายใจไม่ออก จะแนะนำให้แพทย์ประเมิน\n\nเกณฑ์กรนตั้งแต่ 10% ร่วมกับอาการเจ็บคอ/ปากแห้ง หรืออาการหายใจทางปาก 3 ใน 7 คืนล่าสุด เป็นเกณฑ์ทดลองของโครงการ ไม่นับอาการในคืนที่คัดจมูก เป็นหวัด หรือภูมิแพ้',
  );
  Future<void> _editName() async {
    final value = await showDialog<String>(
      context: context,
      builder: (_) => NameDialog(name: _name),
    );
    if (value == null || !mounted) return;
    try {
      final next = {
        ...preferences,
        'name': value.isEmpty ? 'ผู้ใช้ทั่วไป' : value,
      };
      await store!.savePreferences(next);
      if (mounted) setState(() => preferences = next);
    } catch (e) {
      if (mounted) setState(() => message = 'บันทึกชื่อไม่ได้: $e');
    }
  }

  String get _name {
    final raw = preferences['name'];
    return raw is String && raw.trim().isNotEmpty ? raw.trim() : 'ผู้ใช้ทั่วไป';
  }

  Map<String, dynamic> get _checks {
    final raw = preferences['checklists'];
    return raw is Map ? Map<String, dynamic>.from(raw) : {};
  }

  Map<String, dynamic> _answersFor(String? id) {
    final raw = _checks[id];
    if (raw is! Map || raw['answers'] is! Map) return {};
    return Map<String, dynamic>.from(raw['answers']);
  }

  Map<String, dynamic> get _answers => _answersFor(selectedParent?.id);
  Map<String, dynamic>? _checkResult(RecordingEntry? parent) {
    if (parent == null) return null;
    final answers = _answersFor(parent.id);
    if (!completeMorning(answers)) return null;
    final history = records
        .where(
          (r) =>
              r.id != parent.id &&
              !isSample(r) &&
              !isSample(parent) &&
              r.createdAt.isBefore(parent.createdAt) &&
              completeMorning(_answersFor(r.id)),
        )
        .map((r) => _answersFor(r.id))
        .toList();
    return evaluateMorning(
      answers,
      snorePct: entryPercent(parent),
      history: history,
    );
  }

  Future<void> _saveChecklist(Map<String, dynamic> answers) async {
    if (locked || selectedParent == null || !completeMorning(answers)) return;
    setState(() => busy = true);
    try {
      final checks = {
            ..._checks,
            selectedParent!.id: {
              'answers': answers,
              'saved_at': DateTime.now().toUtc().toIso8601String(),
            },
          },
          next = {...preferences, 'checklists': checks};
      await store!.savePreferences(next);
      if (mounted) setState(() => preferences = next);
    } catch (e) {
      if (mounted) setState(() => message = 'บันทึกคำตอบไม่ได้: $e');
      return;
    } finally {
      if (mounted) setState(() => busy = false);
    }
    if (mounted) await _openParts(selectedParent!);
  }

  void _afterChecklist() {
    if (selectedParent == null) {
      _go('home');
    } else {
      _openParts(selectedParent!);
    }
  }

  Widget _parts() {
    final parent = selectedParent!,
        parts =
            entries
                .where((e) => e.parentId == parent.id && e.status == 'done')
                .toList()
              ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        WebHeader(title: 'รายงานการนอน', onBack: () => _go('home')),
        Text(
          'บันทึกเมื่อ ${thaiDate(parent.createdAt)}',
          style: type(12, color: muted),
        ),
        const SizedBox(height: 20),
        WebSurface(
          color: navy,
          radius: 26,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'ผลประเมินจากเสียงทั้งการบันทึก',
                style: type(12, color: const Color(0xffc0d1ef)),
              ),
              const SizedBox(height: 14),
              BluePill(
                'พบกรน ${entryPercent(parent).toStringAsFixed(1)}%',
                amber: true,
              ),
              const SizedBox(height: 15),
              Text(
                'เสียงทั้งหมด ${durationLabel(parent.summary?['recording_seconds'] ?? 0)}',
                style: type(19, color: Colors.white, weight: FontWeight.w700),
              ),
              const SizedBox(height: 5),
              Text(
                'แบ่งรายงาน ${parts.length} ส่วน เพื่อเปิดฟังและดูกราฟ',
                style: type(12, color: const Color(0xffb9ccec)),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        MorningCard(
          result: _checkResult(parent),
          onOpen: () => _go('checklist'),
          onInfo: _checkInfo,
        ),
        const SizedBox(height: 20),
        Text(
          'เลือกส่วนที่ต้องการฟัง · เวลาในกราฟเริ่มที่ 00:00 ของส่วนนั้น',
          style: type(12, color: muted),
        ),
        const SizedBox(height: 14),
        for (var i = 0; i < parts.length; i++) ...[
          WebSurface(
            onTap: locked || active ? null : () => _open(parts[i]),
            child: Row(
              children: [
                const Glyph('headphones'),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'ส่วน ${i + 1} · เริ่มนาทีที่ ${i * 5}',
                        style: type(14, weight: FontWeight.w600),
                      ),
                      Text(
                        'พบกรน ${entryPercent(parts[i]).toStringAsFixed(1)}%',
                        style: type(12, color: muted),
                      ),
                    ],
                  ),
                ),
                const Glyph('chevron-right', color: muted),
              ],
            ),
          ),
          const SizedBox(height: 14),
        ],
        TextButton.icon(
          onPressed: locked || active ? null : () => _delete(parent),
          icon: const Glyph('trash-2', color: Color(0xffb84155)),
          label: Text(
            'ลบผลการบันทึกนี้',
            style: type(13, color: const Color(0xffb84155)),
          ),
        ),
      ],
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    capture?.removeListener(_changed);
    unawaited(capture?.close() ?? Future.value());
    if (!busy) engine.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = capture,
        flow = ['prepare', 'consent', 'record', 'checklist'].contains(page),
        night = page == 'record';
    final enabled = ready && !locked;
    final Widget body = switch (page) {
      'history' => WebHistory(
        records: records,
        enabled: enabled && !active,
        onBack: () => _go('home'),
        onUpload: _pick,
        onExport: _exportHistory,
        onCsv: () => _exportHistory(csv: true),
        checklists: {
          for (final e in records.where((e) => !isSample(e)))
            if (_checkResult(e) != null) e.id: _checkResult(e)!,
        },
        onOpen: _openParts,
        onRetry: _process,
        onDelete: _delete,
      ),
      'profile' => WebProfile(
        name: _name,
        count: records.length,
        enabled: !locked && !active,
        onBack: () => _go('home'),
        onName: _editName,
        onPrivacy: _privacy,
        onExplanation: _explanation,
        onGuide: () => _go('prepare'),
        onClear: _clear,
        onAbout: () => showLicensePage(
          context: context,
          applicationName: 'Snoresens AI',
          applicationVersion: '0.3.0',
          applicationLegalese: 'เสียงตัวอย่าง: Tongue base snoring โดย Langenbergstefan, Wikimedia Commons — CC BY-SA 3.0\nแปลงเป็น WAV 16 kHz\nhttps://commons.wikimedia.org/wiki/File:Tongue_base_snoring.ogg',
        ),
      ),
      'prepare' => WebPrepare(
        onBack: () => _go('home'),
        onNext: () => _go('consent'),
      ),
      'consent' => WebConsent(
        accepted: consent,
        enabled: enabled && !active,
        error: message.isEmpty ? null : message,
        onAccept: (value) => setState(() => consent = value),
        onBack: () => _go('prepare'),
        onBegin: _start,
      ),
      'record' => WebRecording(
        active: active,
        paused: c?.paused ?? false,
        stopped: c?.stopped ?? false,
        changing: locked,
        elapsed: c?.elapsed ?? Duration.zero,
        message: active
            ? (c?.message ?? 'วิเคราะห์หลังคุณหยุดบันทึก')
            : message,
        levels: c?.levels,
        onPause: () => c?.togglePause(),
        onStop: _stop,
        onHome: () => _go('home'),
      ),
      'checklist' => MorningForm(
        key: ValueKey(selectedParent?.id),
        initial: _answers,
        saving: locked,
        date: thaiDate(selectedParent?.createdAt ?? DateTime.now()),
        onSave: _saveChecklist,
        onBack: _afterChecklist,
        onSkip: _afterChecklist,
      ),
      'parts' => selectedParent == null ? WebEmpty(onUpload: _pick) : _parts(),
      'report' =>
        result == null
            ? Column(
                children: [
                  WebHeader(title: 'รายงานการนอน', onBack: () => _go('home')),
                  WebEmpty(onUpload: enabled && !active ? _pick : null),
                ],
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  WebHeader(title: 'รายงานการนอน', onBack: () => _go('home')),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          'บันทึกเมื่อ ${thaiDate(selectedPart?.createdAt ?? DateTime.now())}',
                          style: type(12, color: muted),
                        ),
                      ),
                      BluePill(
                        selectedParent != null && isSample(selectedParent!)
                            ? 'เสียงตัวอย่าง'
                            : 'ผลวิเคราะห์เสียง',
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  ResultPanel(
                    key: ValueKey(selectedPart?.id),
                    result: result!,
                    enablePlayback: widget.enablePlayback,
                    onDelete: selectedParent == null || active || locked
                        ? null
                        : () => _delete(selectedParent!),
                    onExplanation: _explanation,
                    onReanalyze: selectedParent == null || active || locked
                        ? null
                        : () => _process(selectedParent!, force: true),
                    checklist: MorningCard(
                      result: _checkResult(selectedParent),
                      onOpen: () => _go('checklist'),
                      onInfo: _checkInfo,
                    ),
                  ),
                ],
              ),
      _ => WebHome(
        records: records,
        active: active,
        enabled: enabled,
        onStart: _beginFlow,
        onUpload: _pick,
        onSample: _sample,
        onHistory: () => _go('history'),
        onGuide: () => _go('prepare'),
        onOpen: _openParts,
        onRetry: _process,
        onDelete: _delete,
      ),
    };
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: night ? SystemUiOverlayStyle.light : SystemUiOverlayStyle.dark,
      child: PopScope(
        canPop: page == 'home',
        onPopInvokedWithResult: (didPop, _) {
          if (!didPop) _go(page == 'consent' ? 'prepare' : 'home');
        },
        child: Scaffold(
          backgroundColor: night ? navy : paper,
          bottomNavigationBar: flow
              ? null
              : WebNav(
                  selected: page == 'history'
                      ? 2
                      : page == 'profile'
                      ? 3
                      : ['report', 'parts'].contains(page)
                      ? 1
                      : 0,
                  onSelect: _nav,
                ),
          body: SafeArea(
            bottom: flow,
            child: Column(
              children: [
                if (busy) const LinearProgressIndicator(minHeight: 3),
                Expanded(
                  child: SingleChildScrollView(
                    key: ValueKey(page),
                    padding: EdgeInsets.fromLTRB(
                      MediaQuery.sizeOf(context).width <= 370 ? 18 : 24,
                      24,
                      MediaQuery.sizeOf(context).width <= 370 ? 18 : 24,
                      32,
                    ),
                    child: Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 600),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            if (active && !flow) ...[
                              WebSurface(
                                color: const Color(0xffe4ebff),
                                radius: 12,
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 12,
                                ),
                                onTap: () => _go('record'),
                                child: Row(
                                  children: [
                                    const Glyph('mic', size: 18),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Text(
                                        c?.paused == true
                                            ? 'พักการบันทึก · กลับไปดูการบันทึก'
                                            : 'กำลังบันทึกเสียง · กลับไปดูการบันทึก',
                                        style: type(13, color: blue),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 18),
                            ],
                            if (message.isNotEmpty && page != 'record') ...[
                              WebSurface(
                                color: const Color(0xffe4ebff),
                                radius: 12,
                                padding: const EdgeInsets.all(12),
                                child: Text(
                                  message,
                                  style: type(12, color: ink),
                                ),
                              ),
                              const SizedBox(height: 16),
                            ],
                            body,
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
