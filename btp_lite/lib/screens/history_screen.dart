import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/simplify_result.dart';
import '../services/storage_service.dart';
import '../theme/app_theme.dart';

class HistoryScreen extends StatefulWidget {
  final ValueChanged<SimplifyResult>? onSelect;
  const HistoryScreen({super.key, this.onSelect});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<SimplifyResult> _history = [];

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  void _loadHistory() {
    final storage = context.read<StorageService>();
    setState(() => _history = storage.getHistory());
  }

  Future<void> _clearHistory() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Clear History'),
        content: const Text(
            'Are you sure you want to delete all history? This cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Clear'),
          ),
        ],
      ),
    );
    if (confirm == true && mounted) {
      await context.read<StorageService>().clearHistory();
      _loadHistory();
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? AppTheme.bgDark : AppTheme.bgLight;
    final textColor =
        isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final borderColor = isDark ? AppTheme.borderDark : AppTheme.borderLight;
    final subColor =
        isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: isDark ? AppTheme.surfaceDark : AppTheme.surfaceLight,
        title: Text('History',
            style: GoogleFonts.inter(
                fontWeight: FontWeight.w700, color: textColor)),
        actions: [
          if (_history.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete_outline_rounded),
              tooltip: 'Clear history',
              onPressed: _clearHistory,
            ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Divider(height: 1, color: borderColor),
        ),
      ),
      body: _history.isEmpty
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.history_rounded,
                       size: 48, color: subColor.withValues(alpha: 0.3)),
                  const SizedBox(height: 16),
                  Text(
                    'No history yet',
                    style: GoogleFonts.inter(
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                        color: textColor),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Your past simplifications will appear here.',
                    style: GoogleFonts.inter(
                        fontSize: 13, color: subColor),
                  ),
                ],
              ),
            )
          : ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: _history.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final item = _history[index];
                return _HistoryCard(
                  result: item,
                  isDark: isDark,
                  index: index,
                  onSelect: widget.onSelect,
                );
              },
            ),
    );
  }
}

class _HistoryCard extends StatelessWidget {
  final SimplifyResult result;
  final bool isDark;
  final int index;
  final ValueChanged<SimplifyResult>? onSelect;

  const _HistoryCard({
    required this.result,
    required this.isDark,
    required this.index,
    this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    final cardColor = isDark ? AppTheme.cardDark : AppTheme.cardLight;
    final borderColor = isDark ? AppTheme.borderDark : AppTheme.borderLight;
    final textColor =
        isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor =
        isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;

    final dateStr =
        '${result.timestamp.day}/${result.timestamp.month}/${result.timestamp.year}  '
        '${result.timestamp.hour.toString().padLeft(2, '0')}:'
        '${result.timestamp.minute.toString().padLeft(2, '0')}';

    return InkWell(
      onTap: () {
        if (onSelect != null) {
          onSelect!(result);
        }
        Navigator.pop(context, result);
      },
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: cardColor,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: borderColor),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top row: model chip + date
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0xFF6C4DF6).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '🤖 ${result.modelName}',
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: const Color(0xFF6C4DF6),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    result.strategy,
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      color: const Color(0xFF10B981),
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
                const Spacer(),
                Text(
                  dateStr,
                  style: GoogleFonts.inter(fontSize: 11, color: subColor),
                ),
              ],
            ),
            const SizedBox(height: 10),
            // Snippet
            Text(
              result.originalSnippet,
              style:
                  GoogleFonts.inter(fontSize: 13, color: subColor, height: 1.4),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 10),
            // Preview of output
            Text(
              result.simplifiedText.length > 180
                  ? '${result.simplifiedText.substring(0, 180).trim()}…'
                  : result.simplifiedText,
              style: GoogleFonts.inter(
                  fontSize: 13, color: textColor, height: 1.5),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'Load into Card View & Chat',
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: const Color(0xFF6C4DF6),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(width: 4),
                  const Icon(Icons.arrow_forward_rounded,
                      size: 14, color: Color(0xFF6C4DF6)),
                ],
              ),
            ),
          ],
        ),
      ),
    )
        .animate()
        .fadeIn(duration: 300.ms, delay: Duration(milliseconds: index * 40))
        .slideY(begin: 0.04, end: 0, duration: 300.ms, curve: Curves.easeOut);
  }
}
