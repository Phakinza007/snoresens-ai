import 'dart:typed_data';

/// Decode standard 16-bit PCM WAV, mono or stereo, at 16 kHz.
Float32List decodeWav(Uint8List bytes) {
  if (bytes.length < 44) throw const FormatException('ไฟล์ WAV สั้นเกินไป');
  final data = ByteData.sublistView(bytes);
  String fourcc(int offset) => String.fromCharCodes(bytes.sublist(offset, offset + 4));
  if (fourcc(0) != 'RIFF' || fourcc(8) != 'WAVE') {
    throw const FormatException('รองรับเฉพาะไฟล์ WAV');
  }
  int? channels, rate, bits, format, dataOffset, dataLength;
  var cursor = 12;
  while (cursor + 8 <= bytes.length) {
    final id = fourcc(cursor);
    final length = data.getUint32(cursor + 4, Endian.little);
    final next = cursor + 8 + length;
    if (next > bytes.length) throw const FormatException('ไฟล์ WAV ไม่สมบูรณ์');
    if (id == 'fmt ' && length >= 16) {
      format = data.getUint16(cursor + 8, Endian.little);
      channels = data.getUint16(cursor + 10, Endian.little);
      rate = data.getUint32(cursor + 12, Endian.little);
      bits = data.getUint16(cursor + 22, Endian.little);
    } else if (id == 'data') {
      dataOffset = cursor + 8;
      dataLength = length;
    }
    cursor = next + (length.isOdd ? 1 : 0);
  }
  if (format != 1 || bits != 16 || channels == null || channels < 1 ||
      channels > 2 || rate != 16000 || dataOffset == null || dataLength == null) {
    throw const FormatException('แอปรองรับ WAV PCM 16-bit, 16 kHz, mono/stereo');
  }
  final sampleCount = dataLength ~/ (2 * channels);
  if (sampleCount == 0) throw const FormatException('ไม่มีข้อมูลเสียง');
  final result = Float32List(sampleCount);
  for (var i = 0; i < sampleCount; i++) {
    var sum = 0.0;
    for (var ch = 0; ch < channels; ch++) {
      sum += data.getInt16(dataOffset + (i * channels + ch) * 2, Endian.little) / 32768.0;
    }
    result[i] = sum / channels;
  }
  return result;
}
