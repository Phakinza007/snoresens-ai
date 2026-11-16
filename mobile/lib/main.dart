import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:material_ui/material_ui.dart';
import 'package:file_picker/file_picker.dart';
import 'package:path_provider/path_provider.dart';

import 'capture_session.dart';
import 'recording_store.dart';
import 'recording_processor.dart';
import 'recording_panel.dart';
import 'inference.dart';
import 'result_panel.dart';

void main() => runApp(const SanorApp());

class SanorApp extends StatelessWidget {
  const SanorApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Snoresens AI',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: const Color(0xfff5f7ff),
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff3157f5)),
    ),
    home: const HomePage(),
  );
}

class HomePage extends StatefulWidget {
  const HomePage({super.key, this.documents, this.engine, this.recorder});
  final Future<Directory> Function()? documents;
  final SnoreEngine? engine;
  final CaptureRecorder? recorder;
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with WidgetsBindingObserver {
  late final SnoreEngine engine;
  RecordingStore? store;
  CaptureSession? capture;
  List<RecordingEntry> entries = [];
  bool ready = false, busy = false;
  String message = 'กำลังเตรียมแอป…';
  AppLifecycleState lifecycle = AppLifecycleState.resumed;
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
      if (!mounted) return;
      capture = CaptureSession(s, recorder: widget.recorder)
        ..addListener(_captureChanged);
      await _refresh();
      if (!mounted) return;
      await engine.load();
      if (!mounted) {
        engine.close();
        return;
      }
      setState(() {
        ready = true;
        message = 'พร้อมบันทึก · โมเดลรุ่น 2';
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

  void _captureChanged() {
    if (mounted) setState(() {});
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    lifecycle = state;
    if (state == AppLifecycleState.resumed) _refresh();
  }

  Future<void> _start() async {
    await capture?.start();
    await _refresh();
  }

  Future<void> _stop() async {
    final e = await capture?.stop();
    await _refresh();
    if (e != null && mounted && lifecycle == AppLifecycleState.resumed) {
      await _process(e);
    }
  }

  Future<void> _pick() async {
    if (busy || capture?.active == true) return;
    setState(() => busy = true);
    RecordingEntry? imported;
    try {
      final f = await FilePicker.pickFile(
        type: FileType.custom,
        allowedExtensions: ['wav'],
      );
      if (f == null) return;
      final s = store!;
      final id = 'import_${DateTime.now().microsecondsSinceEpoch}';
      final path = s.audioPath(id);
      if (f.path != null) {
        await File(f.path!).copy(path);
      } else {
        await File(path).writeAsBytes(await f.readAsBytes(), flush: true);
      }
      final e = RecordingEntry(
        id: id,
        name: f.name,
        createdAt: DateTime.now(),
        status: 'pending',
      );
      await s.save(e);
      await _refresh();
      imported = e;
    } catch (e) {
      if (mounted) setState(() => message = 'เปิดไฟล์ไม่ได้: $e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
    if (imported != null && mounted) await _process(imported);
  }

  Future<void> _process(RecordingEntry entry) async {
    if (busy || !ready || capture?.active == true) return;
    setState(() => busy = true);
    final s = store!;
    try {
      final job = RecordingProcessor(
        s,
        analyze: (name, bytes, {audioPath, shouldContinue}) => engine.analyze(
          name,
          bytes,
          audioPath: audioPath,
          shouldContinue: shouldContinue,
        ),
        foreground: () => mounted && lifecycle == AppLifecycleState.resumed,
        onProgress: (part) {
          if (mounted) {
            setState(
              () => message = 'กำลังวิเคราะห์ส่วน $part · ส่วนละไม่เกิน 5 นาที',
            );
          }
        },
      );
      final finished = await job.process(entry);
      if (mounted) {
        setState(
          () => message = finished
              ? 'วิเคราะห์ครบแล้ว เก็บเสียงและผลในเครื่อง'
              : 'พักการวิเคราะห์ กลับมากดวิเคราะห์ต่อจากประวัติได้',
        );
      }
    } catch (error) {
      if (mounted) {
        setState(() => message = 'วิเคราะห์ไม่สำเร็จ เก็บไฟล์ไว้แล้ว: $error');
      }
    } finally {
      await _refresh();
      if (mounted) {
        setState(() => busy = false);
      } else {
        engine.close();
      }
    }
  }

  Future<void> _open(RecordingEntry e) async {
    if (busy || capture?.active == true) return;
    setState(() => busy = true);
    try {
      final data = await store!.readAnalysis(e.id);
      final r = SnoreResult.fromJson(data, audioPath: store!.audioPath(e.id));
      if (!mounted) return;
      await Navigator.of(context).push<void>(
        MaterialPageRoute(
          builder: (context) => Scaffold(
            appBar: AppBar(title: const Text('รายงานเสียง')),
            body: ListView(
              padding: const EdgeInsets.all(24),
              children: [ResultPanel(result: r)],
            ),
          ),
        ),
      );
    } catch (error) {
      if (mounted) setState(() => message = 'เปิดผลไม่ได้: $error');
    } finally {
      if (mounted) {
        setState(() => busy = false);
      } else {
        engine.close();
      }
    }
  }

  Future<void> _openParts(RecordingEntry entry) async {
    final parts =
        entries
            .where((part) => part.parentId == entry.id && part.status == 'done')
            .toList()
          ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
    if (parts.length == 1) {
      await _open(parts.single);
      return;
    }
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (context) => Scaffold(
          appBar: AppBar(title: const Text('รายงานการบันทึก')),
          body: ListView(
            padding: const EdgeInsets.all(24),
            children: [
              Text(
                entry.name,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 12),
              if (entry.summary != null)
                Text(
                  'เสียงทั้งหมด ${audioTime((entry.summary!['recording_seconds'] as num).toDouble())} · กรน ${metric(entry.summary!['snore_percent_of_recording'])}%',
                ),
              const Text(
                'แตะส่วนที่ต้องการฟัง กราฟและเวลาในรายงานเริ่มที่ 00:00 ของส่วนนั้น',
              ),
              for (var i = 0; i < parts.length; i++)
                Card(
                  child: ListTile(
                    title: Text(
                      'ส่วน ${i + 1} · ${audioTime(i * 300.0)} ของเสียงฉบับเต็ม',
                    ),
                    subtitle: Text(
                      'กรน ${metric(parts[i].summary?['snore_percent_of_recording'])}%',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => _open(parts[i]),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _delete(RecordingEntry e) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('ลบเสียงและผลนี้?'),
        content: const Text(
          'การลบการบันทึกต้นฉบับจะลบส่วนย่อยที่เกี่ยวข้องด้วย',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('ยกเลิก'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('ลบ'),
          ),
        ],
      ),
    );
    if (yes != true) return;
    try {
      for (final child in entries.where((x) => x.parentId == e.id)) {
        await store!.delete(child.id);
      }
      await store!.delete(e.id);
      await _refresh();
    } catch (error) {
      if (mounted) setState(() => message = 'ลบไฟล์ไม่ได้: $error');
    }
  }

  Future<void> _exportSummary() async {
    try {
      final rows = entries.map((e) => e.toJson()).toList();
      await FilePicker.saveFile(
        fileName: 'Snoresens-history.json',
        mimeType: 'application/json',
        bytes: utf8.encode(const JsonEncoder.withIndent('  ').convert(rows)),
      );
    } catch (e) {
      if (mounted) setState(() => message = 'ส่งออกไม่ได้: $e');
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    capture?.removeListener(_captureChanged);
    unawaited(capture?.close() ?? Future.value());
    if (!busy) engine.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = capture,
        active = c?.active == true,
        locked = busy || c?.changing == true;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Snoresens AI'),
        actions: [
          IconButton(
            tooltip: 'ส่งออกประวัติ',
            onPressed: entries.isNotEmpty && !active && !locked
                ? _exportSummary
                : null,
            icon: const Icon(Icons.ios_share),
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text(
              active ? 'คืนนี้ เก็บเสียงของคุณ' : 'ฟังคืนของคุณ',
              style: Theme.of(context).textTheme.headlineLarge,
            ),
            const SizedBox(height: 12),
            const Text('อัดเสียงและวิเคราะห์บนอุปกรณ์ · โมเดลรุ่น 2'),
            const SizedBox(height: 24),
            RecordingPanel(
              active: active,
              paused: c?.paused ?? false,
              stopped: c?.stopped ?? false,
              enabled: ready && !locked,
              changing: locked,
              elapsed: c?.elapsed ?? Duration.zero,
              message: c?.message ?? message,
              onStart: _start,
              onPause: () => c?.togglePause(),
              onStop: _stop,
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: ready && !locked && !active ? _pick : null,
              icon: const Icon(Icons.folder_open),
              label: const Text('เลือกไฟล์ WAV'),
            ),
            if (busy) const LinearProgressIndicator(),
            Text(message),
            const SizedBox(height: 24),
            Text(
              'ประวัติบนอุปกรณ์',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            if (entries.isEmpty)
              const Padding(
                padding: EdgeInsets.all(20),
                child: Text(
                  'ยังไม่มีการบันทึก เริ่มอัดหรือเลือกไฟล์เสียงได้เลย',
                ),
              ),
            for (final e in entries.where((e) => e.parentId == null))
              Card(
                child: ListTile(
                  title: Text(e.name),
                  subtitle: Text(
                    e.status == 'processed'
                        ? 'กรน ${(e.summary?['snore_percent_of_recording'] as num?)?.toStringAsFixed(1) ?? '—'}% · ${e.summary?['part_count']} ส่วน · แตะดูรายงาน'
                        : e.status == 'recording'
                        ? 'กำลังอัดเสียง'
                        : 'รอวิเคราะห์${e.error == null ? '' : ' · ${e.error}'}',
                  ),
                  onTap:
                      !active &&
                          !locked &&
                          entries.any(
                            (part) =>
                                part.parentId == e.id && part.status == 'done',
                          )
                      ? () => _openParts(e)
                      : null,
                  trailing: Wrap(
                    children: [
                      if (e.parentId == null && e.status != 'recording')
                        IconButton(
                          tooltip: 'ตรวจผล / วิเคราะห์ต่อ',
                          onPressed: ready && !active && !locked
                              ? () => _process(e)
                              : null,
                          icon: const Icon(Icons.analytics_outlined),
                        ),
                      IconButton(
                        tooltip: 'ลบ',
                        onPressed: !active && !locked ? () => _delete(e) : null,
                        icon: const Icon(Icons.delete_outline),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 20),
            const Text(
              'เสียงฉบับเต็มอยู่ใน Files → On My iPhone → Snoresens AI → Snoresens สามารถแชร์ไฟล์ WAV จากที่นั่นได้\nเวลารายงานคือเสียงที่รับได้จริง ไม่ใช่เวลาที่หลับ การวิเคราะห์ไฟล์ยาวแบ่งทีละ 5 นาทีและทำต่อเมื่อเปิดแอป\nผลเป็นการประมาณเสียงกรน ไม่ใช่การวินิจฉัยโรค',
              style: TextStyle(fontSize: 12, color: Color(0xff7387a6)),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}
