import 'package:material_ui/material_ui.dart';

String recordingTime(Duration d) =>
    '${d.inHours.toString().padLeft(2, '0')}:${(d.inMinutes % 60).toString().padLeft(2, '0')}:${(d.inSeconds % 60).toString().padLeft(2, '0')}';

class RecordingPanel extends StatelessWidget {
  final bool active, paused, stopped, enabled, changing;
  final Duration elapsed;
  final String message;
  final VoidCallback onStart, onPause, onStop;
  const RecordingPanel({
    super.key,
    required this.active,
    required this.paused,
    required this.stopped,
    required this.enabled,
    required this.changing,
    required this.elapsed,
    required this.message,
    required this.onStart,
    required this.onPause,
    required this.onStop,
  });
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (active) ...[
            Icon(
              paused ? Icons.pause_circle_outline : Icons.mic,
              color: paused
                  ? Theme.of(context).colorScheme.secondary
                  : Theme.of(context).colorScheme.primary,
              size: 32,
            ),
            const SizedBox(height: 12),
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(
                recordingTime(elapsed),
                style: const TextStyle(
                  fontSize: 42,
                  fontFeatures: [FontFeature.tabularFigures()],
                ),
              ),
            ),
          ] else
            Text(
              'พร้อมเมื่อคุณเริ่ม',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
          const SizedBox(height: 12),
          Text(
            message,
            textAlign: TextAlign.center,
            semanticsLabel: 'สถานะการบันทึก $message',
          ),
          const SizedBox(height: 20),
          if (active) ...[
            FilledButton.icon(
              onPressed: changing || stopped ? null : onPause,
              icon: Icon(paused ? Icons.play_arrow : Icons.pause),
              label: Text(paused ? 'บันทึกต่อ' : 'พักการบันทึก'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: changing ? null : onStop,
              icon: const Icon(Icons.stop_circle),
              label: const Text('จบและวิเคราะห์'),
            ),
          ] else
            FilledButton.icon(
              onPressed: enabled && !changing ? onStart : null,
              icon: const Icon(Icons.mic),
              label: const Text('เริ่มบันทึกคืนนี้'),
            ),
          const SizedBox(height: 12),
          const Text(
            'ล็อกจอระหว่างอัดได้ หากมีสายโทรเข้าหรือเปลี่ยนอุปกรณ์เสียง ให้กลับมาตรวจสถานะการอัด',
            style: TextStyle(fontSize: 13),
          ),
        ],
      ),
    ),
  );
}
