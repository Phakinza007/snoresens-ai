import 'dart:io';
import 'dart:convert';

class RecordingEntry {
  final String id, name, status;
  final DateTime createdAt;
  final String? parentId, error;
  final Map<String, dynamic>? summary;
  RecordingEntry({
    required this.id,
    required this.name,
    required this.createdAt,
    required this.status,
    this.parentId,
    this.error,
    this.summary,
  });
  RecordingEntry copy({
    String? status,
    String? error,
    Map<String, dynamic>? summary,
  }) => RecordingEntry(
    id: id,
    name: name,
    createdAt: createdAt,
    status: status ?? this.status,
    parentId: parentId,
    error: error,
    summary: summary ?? this.summary,
  );
  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'status': status,
    'created_at': createdAt.toIso8601String(),
    'parent_id': parentId,
    'error': error,
    'summary': summary,
  };
  factory RecordingEntry.fromJson(Map<String, dynamic> x) => RecordingEntry(
    id: x['id'],
    name: x['name'],
    status: x['status'],
    createdAt: DateTime.parse(x['created_at']),
    parentId: x['parent_id'],
    error: x['error'],
    summary: (x['summary'] as Map?)?.cast<String, dynamic>(),
  );
}

class RecordingStore {
  final Directory root;
  RecordingStore(this.root);
  String _path(String id, String suffix) {
    if (!RegExp(r'^[a-zA-Z0-9_-]+$').hasMatch(id)) {
      throw ArgumentError('Invalid recording id');
    }
    return '${root.path}/$id$suffix';
  }

  String audioPath(String id) => _path(id, '.wav');
  Future<void> _atomic(String path, Object data) async {
    await root.create(recursive: true);
    final tmp = File('$path.tmp');
    await tmp.writeAsString(jsonEncode(data), flush: true);
    await tmp.rename(path);
  }

  Future<void> save(RecordingEntry e) =>
      _atomic(_path(e.id, '.record.json'), e.toJson());
  Future<void> saveAnalysis(String id, Map<String, dynamic> data) =>
      _atomic(_path(id, '.analysis.json'), data);
  Future<Map<String, dynamic>> readAnalysis(String id) async =>
      jsonDecode(await File(_path(id, '.analysis.json')).readAsString());
  Future<List<RecordingEntry>> list() async {
    await root.create(recursive: true);
    final entries = <RecordingEntry>[];
    await for (final f in root.list()) {
      if (f is! File || !f.path.endsWith('.record.json')) continue;
      try {
        final e = RecordingEntry.fromJson(jsonDecode(await f.readAsString()));
        _path(e.id, '');
        entries.add(e);
      } catch (_) {
        /* Keep damaged metadata on disk for recovery. */
      }
    }
    entries.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return entries;
  }

  Future<void> recoverInterrupted() async {
    for (final entry in await list()) {
      if (entry.status == 'recording' || entry.status == 'processing') {
        await save(
          entry.copy(
            status: 'pending',
            error: 'การทำงานครั้งก่อนยังไม่เสร็จ เก็บไฟล์ที่มีไว้แล้ว',
          ),
        );
      }
    }
  }

  Future<void> delete(String id) async {
    for (final suffix in ['.wav', '.record.json', '.analysis.json']) {
      final f = File(_path(id, suffix));
      if (await f.exists()) await f.delete();
    }
  }
}
