// Bounded-memory PCM16 WAV reader; never decode an entire overnight file at once.
import 'dart:io';
import 'dart:typed_data';
import 'dart:math';

Uint8List wrapPcm(Uint8List pcm, int rate, int channels) {
  final result = Uint8List(44 + pcm.length), d = ByteData.sublistView(result);
  void text(int at, String s) => result.setAll(at, s.codeUnits);
  text(0, 'RIFF');
  d.setUint32(4, 36 + pcm.length, Endian.little);
  text(8, 'WAVEfmt ');
  d.setUint32(16, 16, Endian.little);
  d.setUint16(20, 1, Endian.little);
  d.setUint16(22, channels, Endian.little);
  d.setUint32(24, rate, Endian.little);
  d.setUint32(28, rate * channels * 2, Endian.little);
  d.setUint16(32, channels * 2, Endian.little);
  d.setUint16(34, 16, Endian.little);
  text(36, 'data');
  d.setUint32(40, pcm.length, Endian.little);
  result.setAll(44, pcm);
  return result;
}

Stream<Uint8List> wavParts(File file, {int secondsPerPart = 300}) async* {
  if (secondsPerPart <= 0) {
    throw ArgumentError('Part duration must be positive');
  }
  final handle = await file.open();
  try {
    final length = await handle.length(), header = await handle.read(12);
    if (header.length != 12 ||
        String.fromCharCodes(header.sublist(0, 4)) != 'RIFF' ||
        String.fromCharCodes(header.sublist(8, 12)) != 'WAVE') {
      throw const FormatException('ไฟล์ WAV ไม่สมบูรณ์ เก็บไฟล์ต้นฉบับไว้แล้ว');
    }
    int? channels, rate, bits, format, dataAt, dataSize;
    var at = 12;
    while (at + 8 <= length) {
      await handle.setPosition(at);
      final chunk = await handle.read(8),
          tag = String.fromCharCodes(chunk.sublist(0, 4)),
          size = ByteData.sublistView(chunk).getUint32(4, Endian.little);
      final end = at + 8 + size;
      if (end > length) {
        throw const FormatException('ข้อมูลเสียงถูกตัดกลางไฟล์');
      }
      if (tag == 'fmt ') {
        if (size < 16) throw const FormatException('WAV format ไม่ครบ');
        final d = ByteData.sublistView(await handle.read(16));
        format = d.getUint16(0, Endian.little);
        channels = d.getUint16(2, Endian.little);
        rate = d.getUint32(4, Endian.little);
        bits = d.getUint16(14, Endian.little);
      }
      if (tag == 'data') {
        dataAt = at + 8;
        dataSize = size;
      }
      if (dataAt != null && format != null) break;
      at = end + (size % 2);
    }
    if (format != 1 ||
        bits != 16 ||
        rate != 16000 ||
        (channels != 1 && channels != 2) ||
        dataAt == null ||
        dataSize == null ||
        dataSize <= 0 ||
        dataSize % (channels! * 2) != 0) {
      throw const FormatException(
        'ต้องเป็น WAV PCM16 16 kHz ที่มีข้อมูลเสียงครบ',
      );
    }
    await handle.setPosition(dataAt);
    var remaining = dataSize;
    final partBytes = rate! * channels * 2 * secondsPerPart;
    while (remaining > 0) {
      final bytes = await handle.read(min(remaining, partBytes));
      if (bytes.length != min(remaining, partBytes)) {
        throw const FormatException('อ่านไฟล์เสียงได้ไม่ครบ');
      }
      remaining -= bytes.length;
      yield wrapPcm(bytes, rate, channels);
    }
  } finally {
    await handle.close();
  }
}
