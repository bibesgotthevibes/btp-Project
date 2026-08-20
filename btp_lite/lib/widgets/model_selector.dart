import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/api_model.dart';

class ModelSelector extends StatelessWidget {
  final ApiModel selected;
  final List<ApiModel> models;
  final ValueChanged<ApiModel> onChanged;

  const ModelSelector({
    super.key,
    required this.selected,
    required this.models,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final borderColor =
        isDark ? const Color(0xFF30363D) : const Color(0xFFE5E7EB);
    final bgColor = isDark ? const Color(0xFF161B22) : Colors.white;
    final textColor =
        isDark ? const Color(0xFFE6EDF3) : const Color(0xFF1A1A2E);
    final labelColor =
        isDark ? const Color(0xFF8B949E) : const Color(0xFF6B7280);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'AI MODEL',
          style: GoogleFonts.inter(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            color: labelColor,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: borderColor),
          ),
          child: DropdownButtonHideUnderline(
            child: ButtonTheme(
              alignedDropdown: true,
              child: DropdownButton<ApiModel>(
                value: selected,
                isExpanded: true,
                icon: Icon(Icons.keyboard_arrow_down_rounded,
                    color: labelColor),
                dropdownColor: bgColor,
                borderRadius: BorderRadius.circular(12),
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                style: GoogleFonts.inter(color: textColor, fontSize: 14),
                items: models.map((m) {
                  return DropdownMenuItem<ApiModel>(
                    value: m,
                    child: Row(
                      children: [
                        Container(
                          width: 28,
                          height: 28,
                          decoration: BoxDecoration(
                            color: _providerColor(m.provider).withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Center(
                            child: Text(
                              m.providerBadge,
                              style: const TextStyle(fontSize: 13),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                m.name,
                                style: GoogleFonts.inter(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: textColor,
                                ),
                              ),
                              Text(
                                m.providerLabel,
                                style: GoogleFonts.inter(
                                  fontSize: 11,
                                  color: labelColor,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  );
                }).toList(),
                onChanged: (m) {
                  if (m != null) onChanged(m);
                },
              ),
            ),
          ),
        ),
      ],
    );
  }

  Color _providerColor(String provider) {
    switch (provider) {
      case 'cerebras':
        return const Color(0xFFF59E0B);
      case 'gemini':
        return const Color(0xFF6C4DF6);
      case 'groq':
        return const Color(0xFF10B981);
      default:
        return const Color(0xFF6C4DF6);
    }
  }
}
