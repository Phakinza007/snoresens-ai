import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'package:audioplayers/audioplayers.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'inference.dart';

String metric(dynamic value,[int digits=1]) => value is num ? value.toStringAsFixed(digits) : '—';
String audioTime(double seconds) => '${(seconds~/3600).toString().padLeft(2,'0')}:${(seconds~/60%60).toString().padLeft(2,'0')}:${(seconds.toInt()%60).toString().padLeft(2,'0')}';

class ResultPanel extends StatefulWidget {
  final SnoreResult result;
  final SnoreResult? baseline;
  final VoidCallback onDelete;
  const ResultPanel({super.key,required this.result,required this.onDelete,this.baseline});
  @override
  State<ResultPanel> createState()=>_ResultPanelState();
}
class _ResultPanelState extends State<ResultPanel> {
  final player=AudioPlayer();
  StreamSubscription<Duration>? positionSubscription;
  StreamSubscription<PlayerState>? stateSubscription;
  double position=0;
  bool playing=false, playerReady=false;
  int page=0;
  String? error;
  @override
  void initState() {
    super.initState();
    positionSubscription=player.onPositionChanged.listen((value) {
      if(mounted) setState(()=>position=value.inMilliseconds/1000);
    });
    stateSubscription=player.onPlayerStateChanged.listen((value) {
      if(mounted) setState(()=>playing=value==PlayerState.playing);
    });
    _prepare();
  }
  Future<void> _prepare() async {
    if(widget.result.audioPath==null) return;
    try { await player.setSourceDeviceFile(widget.result.audioPath!); if(mounted) setState(()=>playerReady=true); }
    catch(e) { if(mounted) setState(()=>error='เปิดเสียงไม่ได้: $e'); }
  }
  Future<void> _seek(double seconds) async {
    if(!playerReady) return;
    try { await player.seek(Duration(milliseconds:(seconds*1000).round())); if(mounted) setState(()=>position=seconds); }
    catch(e) { if(mounted) setState(()=>error='เลื่อนเสียงไม่ได้: $e'); }
  }
  Future<void> _toggle() async {
    try { if(playing) { await player.pause(); } else { await player.resume(); } }
    catch(e) { if(mounted) setState(()=>error='เล่นเสียงไม่ได้: $e'); }
  }
  Future<void> _export(bool csv) async {
    final item=widget.result;
    final content=csv ? timelineCsv(item.timeline) : const JsonEncoder.withIndent('  ').convert(item.toJson());
    try {
      await FilePicker.saveFile(fileName:'sanor-analysis.${csv?'csv':'json'}',bytes:Uint8List.fromList(utf8.encode(content)),
        mimeType:csv?'text/csv':'application/json');
    } catch(e) { if(mounted) setState(()=>error='บันทึกไม่ได้: $e'); }
  }
  @override
  void dispose() { positionSubscription?.cancel(); stateSubscription?.cancel(); player.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) {
    final item=widget.result, patterns=item.audioPatterns;
    final frequency=patterns['frequency_summary'] as Map<String,dynamic>;
    final rhythm=patterns['rhythm_summary'] as Map<String,dynamic>;
    final entries=<Map<String,dynamic>>[
      ...item.snoreEvents.map((e)=>{...e,'kind':'กรน'}),
      ...(patterns['quiet_gaps'] as List).map((e)=><String,dynamic>{...(e as Map<String,dynamic>),'kind':'ช่วงเงียบ'})
    ]..sort((a,b)=>(a['start_seconds'] as num).compareTo(b['start_seconds'] as num));
    final baseline=widget.baseline;
    return ExpansionTile(title:Text(item.name),subtitle:Text('${metric(item.percent)}% · ${metric(item.minutesPerHour)} นาทีกรน/ชม. · ${metric(item.eventsPerHour)} ช่วง/ชม.'),childrenPadding:const EdgeInsets.all(16),children:[
      Text('เวลาที่อัด ${metric(item.seconds/60)} นาที · กรนยาวที่สุด ${metric(item.summary['longest_snore_event_seconds'])} วินาที'),
      Text('ระดับมัธยฐาน / P95: ${metric(item.summary['snore_median_rms_dbfs'])} / ${metric(item.summary['snore_p95_rms_dbfs'])} dBFS'),
      Text('ความถี่เด่น / ศูนย์กลางสเปกตรัม: ${metric(frequency['median_dominant_frequency_hz'],0)} / ${metric(frequency['median_spectral_centroid_hz'],0)} Hz'),
      Text('ระยะเริ่มช่วงกรนเฉลี่ย: ${metric(rhythm['mean_start_interval_seconds'])} วินาที · CV: ${metric(rhythm['interval_cv'],3)}'),
      if(rhythm['interval_cv']==null) const Text('ต้องมีช่วงกรนอย่างน้อย 3 ช่วงเพื่อคำนวณ CV'),
      if(baseline!=null) Text('ค่าต่างจาก ${baseline.name}: ${metric(item.percent-baseline.percent)} จุดเปอร์เซ็นต์'),
      const SizedBox(height:18),const Text('ช่วงกรน · สีเขียว / ระดับเสียง · สีน้ำเงิน (-90 ถึง 0 dBFS)'),
      SizedBox(height:125,width:double.infinity,child:CustomPaint(painter:AudioTimelinePainter(item.timeline,item.seconds))),
      Text('${audioTime(position)} / ${audioTime(item.seconds)}'),
      Slider(value:position.clamp(0,item.seconds).toDouble(),max:item.seconds,onChanged:playerReady?_seek:null,
        semanticFormatterCallback:(value)=>audioTime(value)),
      Wrap(spacing:8,children:[
        FilledButton.icon(onPressed:playerReady?_toggle:null,icon:Icon(playing?Icons.pause:Icons.play_arrow),label:Text(playing?'พัก':'เล่นเสียง')),
        TextButton(onPressed:()=>_export(false),child:const Text('JSON')),
        TextButton(onPressed:()=>_export(true),child:const Text('Timeline CSV')),
        TextButton(onPressed:widget.onDelete,child:const Text('ลบผลนี้')),
      ]),
      if(error!=null) Text(error!,style:TextStyle(color:Theme.of(context).colorScheme.error)),
      Text('ช่วงเงียบ: ไม่เกิน ${patterns['config']['quiet_threshold_dbfs']} dBFS อย่างน้อย ${patterns['config']['min_quiet_gap_seconds']} วินาที'),
      if(entries.isEmpty) const Text('ไม่มีช่วงที่ตรงเกณฑ์'),
      for(final event in entries.skip(page*20).take(20)) ListTile(dense:true,
        title:Text('${event['kind']} · ${audioTime((event['start_seconds'] as num).toDouble())}–${audioTime((event['end_seconds'] as num).toDouble())}'),
        subtitle:Text('${metric(event['duration_seconds'])} วินาที'),
        onTap:playerReady?()=>_seek((event['start_seconds'] as num).toDouble()):null),
      if(entries.isNotEmpty) Row(mainAxisAlignment:MainAxisAlignment.center,children:[
        TextButton(onPressed:page>0?()=>setState(()=>page--):null,child:const Text('ก่อนหน้า')),
        Text('${page+1}/${(entries.length/20).ceil()}'),
        TextButton(onPressed:(page+1)*20<entries.length?()=>setState(()=>page++):null,child:const Text('ถัดไป')),
      ]),
    ]);
  }
}

String timelineCsv(List<Map<String,dynamic>> rows) {
  if(rows.isEmpty) return '';
  final keys=rows.first.keys.toList();
  String cell(dynamic value)=>'"${(value?.toString()??'').replaceAll('"','""')}"';
  return '\uFEFF${[keys.map(cell).join(','),...rows.map((row)=>keys.map((key)=>cell(row[key])).join(','))].join('\r\n')}';
}

class AudioTimelinePainter extends CustomPainter {
  final List<Map<String,dynamic>> rows;
  final double seconds;
  AudioTimelinePainter(this.rows,this.seconds);
  @override
  void paint(Canvas canvas,Size size) {
    canvas.drawRect(Offset.zero & size,Paint()..color=const Color(0xffedf0e9));
    if(rows.isEmpty || seconds<=0) return;
    final count=min(700,rows.length);
    final snore=List<bool>.filled(count,false);
    final low=List<double?>.filled(count,null), high=List<double?>.filled(count,null);
    for(final row in rows) {
      final first=((row['start_seconds'] as num)/seconds*count).floor().clamp(0,count-1).toInt();
      final last=(((row['start_seconds'] as num)+(row['duration_seconds'] as num))/seconds*count).ceil()-1;
      for(var i=first;i<=min(last,count-1);i++) {
        snore[i]=snore[i] || row['prediction']=='snore';
        final level=(row['rms_dbfs'] as num?)?.toDouble();
        if(level!=null) { low[i]=low[i]==null?level:min(low[i]!,level); high[i]=high[i]==null?level:max(high[i]!,level); }
      }
    }
    final width=size.width/count;
    for(var i=0;i<count;i++) {
      if(snore[i]) canvas.drawRect(Rect.fromLTWH(i*width,0,width+0.5,25),Paint()..color=const Color(0xff247f69));
      if(high[i]!=null) {
        double y(double value)=>35.0+(-value/90).clamp(0.0,1.0).toDouble()*90.0;
        canvas.drawRect(Rect.fromLTWH(i*width,y(high[i]!),width+0.5,max(2.0,y(low[i]!)-y(high[i]!))),Paint()..color=const Color(0xff3e6d88));
      }
    }
  }
  @override
  bool shouldRepaint(covariant AudioTimelinePainter old)=>old.rows!=rows || old.seconds!=seconds;
}
