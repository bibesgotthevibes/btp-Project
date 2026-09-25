import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/medical_artifact.dart';

/// Clickable card embedded inside chat messages to open an artifact in the pinned right panel
class ArtifactCardPill extends StatelessWidget {
  final MedicalArtifact artifact;
  final VoidCallback onTap;
  final bool isPanelOpen;

  const ArtifactCardPill({
    super.key,
    required this.artifact,
    required this.onTap,
    this.isPanelOpen = false,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final bgColor = isDark
        ? const Color(0xFF1F2430)
        : const Color(0xFFF3F0FF);
    final borderColor = isDark
        ? const Color(0xFF374151)
        : const Color(0xFFDDD6FE);
    final titleColor = isDark
        ? const Color(0xFFF3F4F6)
        : const Color(0xFF1E1B4B);
    final subColor = isDark
        ? const Color(0xFF9CA3AF)
        : const Color(0xFF6B7280);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 6),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isPanelOpen
                  ? const Color(0xFF6C4DF6)
                  : borderColor,
              width: isPanelOpen ? 1.5 : 1,
            ),
            boxShadow: [
              if (isPanelOpen)
                BoxShadow(
                  color: const Color(0xFF6C4DF6).withValues(alpha: 0.15),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: artifact.accentColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(artifact.icon,
                    size: 20, color: artifact.accentColor),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            artifact.displayName,
                            style: GoogleFonts.inter(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: titleColor,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: isDark
                                ? const Color(0xFF2A2D3D)
                                : const Color(0xFFEDE9FE),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            artifact.fileExtension,
                            style: GoogleFonts.jetBrainsMono(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: const Color(0xFF6C4DF6),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '${artifact.subtitle} · ${artifact.wordCount} words',
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        color: subColor,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: isPanelOpen
                      ? const Color(0xFF6C4DF6)
                      : const Color(0xFF6C4DF6).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      isPanelOpen ? 'Viewing' : 'Open',
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: isPanelOpen
                            ? Colors.white
                            : const Color(0xFF6C4DF6),
                      ),
                    ),
                    const SizedBox(width: 4),
                    Icon(
                      isPanelOpen
                          ? Icons.check_rounded
                          : Icons.arrow_forward_rounded,
                      size: 13,
                      color: isPanelOpen
                          ? Colors.white
                          : const Color(0xFF6C4DF6),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
