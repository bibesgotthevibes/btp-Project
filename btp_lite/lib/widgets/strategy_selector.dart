import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

const _strategies = [
  (
    id: 'zero-shot',
    label: 'Zero-shot',
    sub: 'Instructions only',
    icon: Icons.flash_on_rounded,
  ),
  (
    id: 'one-shot',
    label: 'One-shot',
    sub: '1 example',
    icon: Icons.looks_one_rounded,
  ),
  (
    id: 'few-shot',
    label: 'Few-shot',
    sub: '4 examples',
    icon: Icons.layers_rounded,
  ),
];

class StrategySelector extends StatelessWidget {
  final String selected;
  final ValueChanged<String> onChanged;

  const StrategySelector({
    super.key,
    required this.selected,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final labelColor =
        isDark ? const Color(0xFF8B949E) : const Color(0xFF6B7280);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'PROMPTING STRATEGY',
          style: GoogleFonts.inter(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: labelColor,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: _strategies.map((s) {
            final isSelected = s.id == selected;
            return Expanded(
              child: GestureDetector(
                onTap: () => onChanged(s.id),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  margin: const EdgeInsets.only(right: 6),
                  padding: const EdgeInsets.symmetric(
                      vertical: 10, horizontal: 8),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? const Color(0xFF6C4DF6)
                        : (isDark
                            ? const Color(0xFF161B22)
                            : Colors.white),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: isSelected
                          ? const Color(0xFF6C4DF6)
                          : (isDark
                              ? const Color(0xFF30363D)
                              : const Color(0xFFE5E7EB)),
                    ),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        s.icon,
                        size: 18,
                        color: isSelected
                            ? Colors.white
                            : const Color(0xFF6C4DF6),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        s.label,
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: isSelected ? Colors.white : labelColor,
                        ),
                        textAlign: TextAlign.center,
                      ),
                      Text(
                        s.sub,
                        style: GoogleFonts.inter(
                          fontSize: 10,
                          color: isSelected
                              ? Colors.white70
                              : labelColor.withValues(alpha: 0.7),
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
}
