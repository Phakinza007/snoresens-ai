import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'inference.dart';
import 'result_panel.dart';

void main() => runApp(const SanorApp());

class SanorApp extends StatelessWidget {
  const SanorApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Sanor', debugShowCheckedModeBanner: false,
    theme: ThemeData(useMaterial3: true, scaffoldBackgroundColor: const Color(0xfff7f7f1),
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff247f69))),
    home: const HomePage(),
  );
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final engine = SnoreEngine();
  final recorder = AudioRecorder();
  final results = <SnoreResult>[];
  bool ready = false, busy = false, recording = false;
  SnoreResult? baseline;
  final quietThreshold = TextEditingController(text:'-45');
  final minimumGap = TextEditingController(text:'10');
  String message = 'กำลังโหลดโมเดล...';

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try { await engine.load(); if (!mounted) { engine.close(); return; } setState(() { ready = true; message = 'พร้อมวิเคราะห์เสียงบนเครื่อง'; }); }
    catch (error) { if (mounted) setState(() => message = 'โหลดโมเดลไม่ได้: $error'); }
  }

  Future<void> _analyze(String name, Uint8List bytes) async {
    if (!mounted) return;
    setState(() { busy = true; message = 'กำลังวิเคราะห์ $name'; });
    try {
      final quiet=double.tryParse(quietThreshold.text), gap=double.tryParse(minimumGap.text);
      if(quiet==null || !quiet.isFinite || quiet>0 || gap==null || !gap.isFinite || gap<=0) {
        throw const FormatException('ตั้งค่าช่วงเงียบ: dBFS ไม่เกิน 0 และระยะมากกว่า 0');
      }
      final directory=await getTemporaryDirectory();
      final path='${directory.path}/sanor_review_${DateTime.now().microsecondsSinceEpoch}.wav';
      await File(path).writeAsBytes(bytes);
      SnoreResult result;
      try { result=await engine.analyze(name, bytes,audioPath:path,quietThresholdDbfs:quiet,minGapSeconds:gap); }
      catch (_) { await File(path).delete(); rethrow; }
      if (mounted) setState(() { results.add(result); message = 'วิเคราะห์ $name แล้ว'; });
    } catch (error) { if (mounted) setState(() => message = '$name: $error'); }
    finally { if (mounted) setState(() => busy = false); }
  }

  Future<void> _pick() async {
    final file = await FilePicker.pickFile(type: FileType.custom, allowedExtensions: ['wav']);
    if (file == null) return;
    await _analyze(file.name, await file.readAsBytes());
  }

  Future<void> _toggleRecord() async {
    try {
      if (recording) {
        final path = await recorder.stop();
        setState(() => recording = false);
        if (path != null) await _analyze('เสียงที่อัด ${DateTime.now().toLocal()}', await File(path).readAsBytes());
      } else {
        if (!await recorder.hasPermission()) { setState(() => message = 'ต้องอนุญาตใช้ไมโครโฟน'); return; }
        final directory = await getTemporaryDirectory();
        final path = '${directory.path}/sanor_${DateTime.now().millisecondsSinceEpoch}.wav';
        await recorder.start(const RecordConfig(encoder: AudioEncoder.wav, sampleRate: 16000, numChannels: 1), path: path);
        setState(() { recording = true; message = 'กำลังอัดเสียง... แตะหยุดเพื่อวิเคราะห์'; });
      }
    } catch (error) { setState(() => message = 'อัดเสียงไม่ได้: $error'); }
  }

  Future<void> _deleteResult(SnoreResult item) async {
    setState(() { results.remove(item); if(baseline==item) baseline=null; });
    if(item.audioPath!=null) {
      try { await File(item.audioPath!).delete(); } catch (_) { /* OS may have cleared temporary files. */ }
    }
  }

  Future<void> _exportComparison() async {
    try {
      await FilePicker.saveFile(fileName:'sanor-comparison.json',mimeType:'application/json',
        bytes:Uint8List.fromList(utf8.encode(const JsonEncoder.withIndent('  ').convert(results.map((r)=>r.toJson()).toList()))));
    } catch(error) { if(mounted) setState(()=>message='บันทึกไม่ได้: $error'); }
  }

  @override
  void dispose() { engine.close(); recorder.dispose(); quietThreshold.dispose(); minimumGap.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    final green = const Color(0xff247f69);
    return Scaffold(appBar: AppBar(title: const Text('◐  SANOR.'), backgroundColor: const Color(0xfff7f7f1)),
      body: SafeArea(child: ListView(padding: const EdgeInsets.all(24), children: [
        const SizedBox(height: 24), Text('SLEEP SOUND / 01', style: TextStyle(fontSize: 11, letterSpacing: 2, fontWeight: FontWeight.bold, color: green)),
        const SizedBox(height: 14), const Text('ฟังคืนของคุณ\nผ่านข้อมูลเสียง', style: TextStyle(fontSize: 37, height: 1.25, fontWeight: FontWeight.w600)),
        const SizedBox(height: 14), const Text('วิเคราะห์เสียงกรนบนมือถือโดยไม่ส่งไฟล์เสียงออกจากเครื่อง', style: TextStyle(color: Color(0xff708077))),
        const SizedBox(height: 32), Wrap(spacing: 12, runSpacing: 12, children: [
          FilledButton.icon(onPressed: ready && !busy && !recording ? _pick : null, icon: const Icon(Icons.folder_open), label: const Text('เลือก WAV 16 kHz')),
          OutlinedButton.icon(onPressed: ready && !busy ? _toggleRecord : null, icon: Icon(recording ? Icons.stop_circle : Icons.mic), label: Text(recording ? 'หยุดและวิเคราะห์' : 'อัดเสียง')),
        ]),
        const SizedBox(height:20), ExpansionTile(title:const Text('ตั้งค่าช่วงเงียบ'),children:[
          TextField(controller:quietThreshold,enabled:!busy && !recording,keyboardType:const TextInputType.numberWithOptions(signed:true,decimal:true),decoration:const InputDecoration(labelText:'ระดับไม่เกิน (dBFS)')),
          TextField(controller:minimumGap,enabled:!busy && !recording,keyboardType:const TextInputType.numberWithOptions(decimal:true),decoration:const InputDecoration(labelText:'ระยะขั้นต่ำ (วินาที)')),
        ]),
        const SizedBox(height: 14), if (busy) const LinearProgressIndicator(), Text(message, style: TextStyle(color: green)),
        const SizedBox(height: 36), Text('ผลเปรียบเทียบ', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 14), if (results.isEmpty) const Text('ยังไม่มีไฟล์ที่วิเคราะห์', style: TextStyle(color: Color(0xff708077))),
        if(results.isNotEmpty) Wrap(spacing:12,runSpacing:12,children:[
          DropdownButton<SnoreResult>(value:baseline,hint:const Text('เลือกไฟล์อ้างอิง'),
            items:[for(final item in results) DropdownMenuItem(value:item,child:SizedBox(width:180,child:Text(item.name,overflow:TextOverflow.ellipsis)))],
            onChanged:(item)=>setState(()=>baseline=item)),
          TextButton(onPressed:()=>setState(()=>baseline=null),child:const Text('ล้างไฟล์อ้างอิง')),
          TextButton(onPressed:_exportComparison,child:const Text('ส่งออกผลทั้งหมด JSON')),
        ]),
        for(final item in results) ResultPanel(key:ValueKey(item),result:item,baseline:baseline,onDelete:()=>_deleteResult(item)),
        const SizedBox(height: 28), const Text('ผลเป็นการประมาณเสียงกรน ไม่ใช่คะแนนสุขภาพหรือการวินิจฉัยโรค ชั่วโมงที่แสดงคือเวลาที่อัดเสียง ไม่ใช่เวลาที่หลับจริง', style: TextStyle(fontSize: 12, color: Color(0xff708077))),
      ])),
    );
  }
}
