import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:share_plus/share_plus.dart';
import '../models/api_model.dart';
import '../models/simplify_result.dart';
import '../screens/chat_screen.dart';
import '../screens/result_screen.dart';

class OutputCard extends StatelessWidget {
  final SimplifyResult result;
  final ApiModel? model;
  final VoidCallback? onOpenChat;

  const OutputCard({
    super.key,
    required this.result,
    this.model,
    this.onOpenChat,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cardColor = isDark ? const Color(0xFF1C2333) : Colors.white;
    final borderColor =
        isDark ? const Color(0xFF30363D) : const Color(0xFFE5E7EB);
    final textColor =
        isDark ? const Color(0xFFE6EDF3) : const Color(0xFF1A1A2E);
    final subColor =
        isDark ? const Color(0xFF8B949E) : const Color(0xFF6B7280);
    final codeBgColor =
        isDark ? const Color(0xFF0D1117) : const Color(0xFFF5F7FA);

    final resolvedModel = model ??
        ApiModel.all.firstWhere(
          (m) => m.name == result.modelName || m.id == result.modelName,
          orElse: () => ApiModel.all.first,
        );

    return Container(
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Meta bar ────────────────────────────────────────────────────────
          Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                // Model chip
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF6C4DF6).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text('🤖', style: TextStyle(fontSize: 12)),
                      const SizedBox(width: 4),
                      Text(
                        result.modelName,
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: const Color(0xFF6C4DF6),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                // Strategy chip
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    result.strategy,
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                      color: const Color(0xFF10B981),
                    ),
                  ),
                ),
                if (result.tokensUsed != null) ...[
                  const SizedBox(width: 8),
                  Text(
                    '${result.tokensUsed} tokens',
                    style: GoogleFonts.inter(
                        fontSize: 11, color: subColor),
                  ),
                ],
                const Spacer(),
                // Chat button
                ElevatedButton.icon(
                  onPressed: onOpenChat ??
                      () => Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => ChatScreen(
                                result: result,
                                model: resolvedModel,
                              ),
                            ),
                          ),
                  icon: const Icon(Icons.forum_rounded, size: 14),
                  label: const Text('Ask Assistant'),
                  style: ElevatedButton.styleFrom(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    textStyle: GoogleFonts.inter(
                        fontSize: 11, fontWeight: FontWeight.w600),
                  ),
                ),
                const SizedBox(width: 6),
                // Action buttons
                _ActionBtn(
                  icon: Icons.open_in_full_rounded,
                  tooltip: 'Full view',
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => ResultScreen(result: result),
                    ),
                  ),
                ),
                const SizedBox(width: 4),
                _ActionBtn(
                  icon: Icons.copy_rounded,
                  tooltip: 'Copy',
                  onTap: () async {
                    await Clipboard.setData(
                        ClipboardData(text: result.simplifiedText));
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                            content: Text('Copied to clipboard ✓')),
                      );
                    }
                  },
                ),
                const SizedBox(width: 4),
                _ActionBtn(
                  icon: Icons.share_rounded,
                  tooltip: 'Share',
                  onTap: () => Share.share(result.simplifiedText,
                      subject: 'Simplified Discharge Summary — MedSimplify'),
                ),
              ],
            ),
          ),
          Divider(height: 1, color: borderColor),
          // ── Result text ─────────────────────────────────────────────────────
          Container(
            constraints: const BoxConstraints(maxHeight: 380),
            child: Scrollbar(
              thumbVisibility: true,
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: MarkdownBody(
                  data: result.simplifiedText,
                  styleSheet: MarkdownStyleSheet(
                    p: GoogleFonts.inter(
                        fontSize: 14, color: textColor, height: 1.7),
                    strong: GoogleFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: textColor),
                    code: GoogleFonts.firaCode(
                        fontSize: 12,
                        backgroundColor: codeBgColor,
                        color: const Color(0xFF6C4DF6)),
                    blockquoteDecoration: BoxDecoration(
                      border: Border(
                        left: BorderSide(
                          color: const Color(0xFF6C4DF6).withValues(alpha: 0.4),
                          width: 3,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    )
        .animate()
        .fadeIn(duration: 400.ms)
        .slideY(begin: 0.06, end: 0, duration: 400.ms, curve: Curves.easeOut);
  }
}

class _ActionBtn extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  const _ActionBtn({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(6),
          child: Icon(
            icon,
            size: 18,
            color: isDark ? const Color(0xFF8B949E) : const Color(0xFF6B7280),
          ),
        ),
      ),
    );
  }
}
