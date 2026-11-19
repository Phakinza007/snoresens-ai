import 'dart:math' as math;

import 'package:material_ui/material_ui.dart';
import 'package:flutter_svg/flutter_svg.dart';

const blue = Color(0xff3157f5),
    navy = Color(0xff152d59),
    ink = Color(0xff182f58),
    muted = Color(0xff7387a6),
    paper = Color(0xfff5f7ff),
    line = Color(0xffe2e9f5);
ThemeData snoresensTheme() => ThemeData(
  useMaterial3: true,
  fontFamily: 'SnoresensThai',
  scaffoldBackgroundColor: paper,
  colorScheme: const ColorScheme.light(
    primary: blue,
    onPrimary: Colors.white,
    secondary: blue,
    surface: Colors.white,
    onSurface: ink,
    error: Color(0xffb84155),
    outline: line,
  ),
  textTheme: const TextTheme(
    bodyMedium: TextStyle(fontSize: 14, height: 1.75, color: ink),
    bodySmall: TextStyle(fontSize: 12, height: 1.75, color: muted),
  ),
  dividerColor: line,
  splashFactory: InkRipple.splashFactory,
  filledButtonTheme: FilledButtonThemeData(
    style: FilledButton.styleFrom(
      backgroundColor: blue,
      foregroundColor: Colors.white,
      disabledBackgroundColor: const Color(0xffdbe3f1),
      disabledForegroundColor: const Color(0xff8194b4),
      minimumSize: const Size(0, 54),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      textStyle: const TextStyle(
        fontFamily: 'SnoresensThai',
        fontSize: 16,
        fontWeight: FontWeight.w600,
        height: 1.5,
      ),
    ),
  ),
  textButtonTheme: TextButtonThemeData(
    style: TextButton.styleFrom(
      foregroundColor: blue,
      minimumSize: const Size(44, 44),
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 0),
      textStyle: const TextStyle(
        fontFamily: 'SnoresensThai',
        fontSize: 13,
        fontWeight: FontWeight.w600,
        height: 1.6,
      ),
    ),
  ),
  outlinedButtonTheme: OutlinedButtonThemeData(
    style: OutlinedButton.styleFrom(
      foregroundColor: ink,
      backgroundColor: Colors.white,
      side: const BorderSide(color: line),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      minimumSize: const Size(44, 44),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13)),
      textStyle: const TextStyle(
        fontFamily: 'SnoresensThai',
        fontSize: 12,
        fontWeight: FontWeight.w600,
      ),
    ),
  ),
  dialogTheme: DialogThemeData(
    backgroundColor: paper,
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
  ),
);
TextStyle type(
  double size, {
  Color color = ink,
  FontWeight weight = FontWeight.w400,
  double height = 1.5,
}) => TextStyle(
  fontFamily: 'SnoresensThai',
  fontVariations: [FontVariation('wght', weight.value.toDouble())],
  fontSize: size,
  color: color,
  fontWeight: weight,
  height: height,
);

class Glyph extends StatelessWidget {
  final String name;
  final double size;
  final Color color;
  const Glyph(this.name, {super.key, this.size = 24, this.color = blue});
  @override
  Widget build(BuildContext context) => SvgPicture.asset(
    'assets/ui/icons/$name.svg',
    width: size,
    height: size,
    colorFilter: ColorFilter.mode(color, BlendMode.srcIn),
    excludeFromSemantics: true,
  );
}

class WebSurface extends StatelessWidget {
  final Widget child;
  final double radius;
  final Color color;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  const WebSurface({
    super.key,
    required this.child,
    this.radius = 22,
    this.color = Colors.white,
    this.padding = const EdgeInsets.all(20),
    this.onTap,
  });
  @override
  Widget build(BuildContext context) => Material(
    color: color,
    borderRadius: BorderRadius.circular(radius),
    clipBehavior: Clip.antiAlias,
    child: InkWell(
      onTap: onTap,
      child: Padding(padding: padding, child: child),
    ),
  );
}

class WebHeader extends StatelessWidget {
  final String? title;
  final VoidCallback? onBack, onGuide;
  const WebHeader({super.key, this.title, this.onBack, this.onGuide});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 36),
      child: Row(
        children: [
          if (title == null) ...[
            const Glyph('moon', size: 28),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                'Snoresens AI',
                style: type(23, weight: FontWeight.w500).copyWith(
                  letterSpacing: -.6,
                  fontVariations: const [FontVariation('wght', 550)],
                ),
              ),
            ),
            IconButton(
              tooltip: 'คำแนะนำก่อนบันทึก',
              constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
              style: IconButton.styleFrom(
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              padding: const EdgeInsets.all(6),
              onPressed: onGuide,
              icon: const Glyph('bell', color: ink),
            ),
          ] else ...[
            IconButton(
              tooltip: 'กลับหน้าหลัก',
              constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
              style: IconButton.styleFrom(
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              padding: const EdgeInsets.all(6),
              onPressed: onBack,
              icon: const Glyph('chevron-left', color: ink),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                title!,
                style: type(
                  21,
                  weight: FontWeight.w700,
                ).copyWith(letterSpacing: -.5),
              ),
            ),
          ],
        ],
      ),
    ),
  );
}

class WebNav extends StatelessWidget {
  final int selected;
  final ValueChanged<int> onSelect;
  const WebNav({super.key, required this.selected, required this.onSelect});
  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: const BoxDecoration(
      color: Colors.white,
      border: Border(top: BorderSide(color: line)),
    ),
    child: SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.only(top: 10, bottom: 12, left: 4, right: 4),
        child: Row(
          children: [
            for (var i = 0; i < 4; i++)
              Expanded(
                child: Semantics(
                  selected: selected == i,
                  button: true,
                  label: const ['หน้าหลัก', 'รายงาน', 'ประวัติ', 'โปรไฟล์'][i],
                  child: InkWell(
                    key: ValueKey('nav-$i'),
                    onTap: () => onSelect(i),
                    borderRadius: BorderRadius.circular(13),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 3),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Glyph(
                            const [
                              'house',
                              'chart-no-axes-column',
                              'history',
                              'user-round',
                            ][i],
                            size: 23,
                            color: selected == i ? blue : muted,
                          ),
                          const SizedBox(height: 5),
                          Text(
                            const [
                              'หน้าหลัก',
                              'รายงาน',
                              'ประวัติ',
                              'โปรไฟล์',
                            ][i],
                            style: type(
                              11,
                              color: selected == i ? blue : muted,
                            ),
                          ),
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
  );
}

class BluePill extends StatelessWidget {
  final String text;
  final bool amber;
  const BluePill(this.text, {super.key, this.amber = false});
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 5),
    decoration: BoxDecoration(
      color: amber ? const Color(0xfffff2d9) : const Color(0xffe3ebff),
      borderRadius: BorderRadius.circular(30),
    ),
    child: Text(
      text,
      style: type(
        11,
        color: amber ? const Color(0xff996414) : blue,
        weight: FontWeight.w600,
      ),
    ),
  );
}

class InfoPanel extends StatelessWidget {
  final String title, text;
  const InfoPanel({super.key, required this.title, required this.text});
  @override
  Widget build(BuildContext context) => WebSurface(
    color: const Color(0xffdfe8ff),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Glyph('info', size: 20),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: type(13, weight: FontWeight.w600)),
              const SizedBox(height: 10),
              Text(text, style: type(12, color: muted, height: 1.9)),
            ],
          ),
        ),
      ],
    ),
  );
}

class MoonArt extends StatelessWidget {
  final double size;
  const MoonArt({super.key, this.size = 66});
  @override
  Widget build(BuildContext context) => SizedBox(
    width: size,
    height: size,
    child: CustomPaint(painter: _MoonPainter()),
  );
}

class _MoonPainter extends CustomPainter {
  @override
  void paint(Canvas c, Size s) {
    final big = s.width >= 90,
        border = big ? 9.0 : 8.0,
        center = Offset(s.width / 2, s.height / 2);
    final light = Paint()..color = const Color(0xffa8c3ff);
    c.drawCircle(center, s.width / 2, light);
    c.save();
    c.clipPath(
      Path()..addOval(
        Rect.fromCircle(center: center, radius: s.width / 2 - border),
      ),
    );
    c.drawCircle(
      center,
      s.width / 2 - border,
      Paint()..color = const Color(0xff5c86e9),
    );
    c.drawOval(
      Rect.fromLTWH(
        border + (big ? 48 : 31),
        border + (big ? -12 : -10),
        big ? 68 : 50,
        big ? 70 : 52,
      ),
      light,
    );
    c.restore();
    final star = big ? 5.0 : 4.0,
        point = Offset(
          s.width - border - (big ? 12 : 9) - star / 2,
          border + (big ? 17 : 14) + star / 2,
        );
    c.drawCircle(point, star / 2, Paint()..color = Colors.white);
    c.drawCircle(
      point + Offset(big ? 12 : 9, big ? 17 : 13),
      star / 2 - 1,
      Paint()..color = Colors.white,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter old) => false;
}

const waveHeights = [
  13,
  30,
  8,
  26,
  39,
  10,
  43,
  32,
  13,
  24,
  15,
  9,
  28,
  11,
  10,
  7,
  18,
  24,
  10,
  10,
  38,
  16,
  26,
  48,
  20,
  11,
  31,
  39,
  14,
  11,
  26,
  12,
  8,
  18,
  32,
  20,
  9,
  15,
  43,
  26,
  12,
  36,
  13,
  18,
  26,
  11,
  12,
  20,
  12,
  9,
  17,
  29,
  10,
  32,
  26,
];

class DecorativeWave extends StatelessWidget {
  final bool flat;
  final double height;
  final List<double>? levels;
  const DecorativeWave({
    super.key,
    this.flat = false,
    this.height = 58,
    this.levels,
  });
  @override
  Widget build(BuildContext context) => ExcludeSemantics(
    child: SizedBox(
      height: height,
      width: double.infinity,
      child: CustomPaint(painter: _WavePainter(flat, levels)),
    ),
  );
}

class _WavePainter extends CustomPainter {
  final bool flat;
  final List<double>? levels;
  _WavePainter(this.flat, this.levels);
  @override
  void paint(Canvas c, Size s) {
    final live = levels;
    final count = live != null && live.isNotEmpty
        ? live.length
        : flat
        ? 46
        : waveHeights.length;
    final gap = flat ? 4.0 : 3.0;
    final w = math.max(
          1.0,
          math.min(4.0, (s.width - gap * (count - 1)) / count),
        ),
        p = Paint()..color = const Color(0xffa6c4ff);
    for (var i = 0; i < count; i++) {
      final double h;
      if (live != null && live.isNotEmpty) {
        h = 3.0 + live[i].clamp(0.0, 1.0) * math.max(0.0, s.height - 6.0);
      } else {
        h = flat ? 3.0 : waveHeights[i].toDouble();
      }
      c.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(i * (w + gap), (s.height - h) / 2, w, h),
          const Radius.circular(5),
        ),
        p,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _WavePainter old) =>
      old.flat != flat || old.levels != levels;
}

class BedArt extends StatelessWidget {
  const BedArt({super.key});
  @override
  Widget build(BuildContext context) => Container(
    height: 181,
    decoration: BoxDecoration(
      color: const Color(0xffdfe8ff),
      borderRadius: BorderRadius.circular(26),
    ),
    child: LayoutBuilder(
      builder: (context, c) => Stack(
        children: [
          const Positioned(
            top: 22,
            left: 0,
            right: 0,
            child: Center(child: Glyph('moon', size: 30)),
          ),
          Positioned(
            left: c.maxWidth * .2,
            top: 57,
            width: c.maxWidth * .52,
            height: 36,
            child: Container(
              decoration: const BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(14)),
              ),
            ),
          ),
          Positioned(
            left: c.maxWidth * .2,
            top: 81,
            width: c.maxWidth * .52,
            height: 15,
            child: Container(
              decoration: BoxDecoration(
                color: const Color(0xffb9cbe9),
                borderRadius: BorderRadius.circular(5),
              ),
            ),
          ),
          Positioned(
            left: c.maxWidth * .14,
            top: 95,
            width: c.maxWidth * .68,
            height: 10,
            child: Container(
              decoration: BoxDecoration(
                color: const Color(0xffa4bddf),
                borderRadius: BorderRadius.circular(9),
              ),
            ),
          ),
          Positioned(
            right: c.maxWidth * .16,
            top: 34,
            width: 28,
            height: 58,
            child: Container(
              decoration: BoxDecoration(
                color: const Color(0xff9ebfff),
                border: Border.all(color: navy, width: 5),
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
          Positioned(
            bottom: 27,
            left: 0,
            right: 0,
            child: Text(
              'วางบนโต๊ะข้างเตียง ใกล้ศีรษะ',
              textAlign: TextAlign.center,
              style: type(12),
            ),
          ),
        ],
      ),
    ),
  );
}
