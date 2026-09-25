import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import '../models/medical_artifact.dart';
import '../theme/app_theme.dart';

class ArtifactPanel extends StatefulWidget {
  final List<MedicalArtifact> artifacts;
  final int selectedIndex;
  final ValueChanged<int> onSelectArtifact;
  final VoidCallback onClose;
  final void Function(String prompt)? onAskAboutArtifact;

  const ArtifactPanel({
    super.key,
    required this.artifacts,
    required this.selectedIndex,
    required this.onSelectArtifact,
    required this.onClose,
    this.onAskAboutArtifact,
  });

  @override
  State<ArtifactPanel> createState() => _ArtifactPanelState();
}

class _ArtifactPanelState extends State<ArtifactPanel> {
  bool _rawView = false;
  bool _isCopied = false;

  MedicalArtifact? get _currentArtifact {
    if (widget.artifacts.isEmpty) return null;
    if (widget.selectedIndex >= 0 &&
        widget.selectedIndex < widget.artifacts.length) {
      return widget.artifacts[widget.selectedIndex];
    }
    return widget.artifacts.first;
  }

  Future<void> _copyContent() async {
    final art = _currentArtifact;
    if (art == null) return;
    await Clipboard.setData(ClipboardData(text: art.content));
    setState(() => _isCopied = true);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Copied ${art.title} to clipboard ✓'),
          duration: const Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _isCopied = false);
    });
  }

  Future<void> _exportPdf() async {
    final art = _currentArtifact;
    if (art == null) return;

    final doc = pw.Document();
    final now = DateTime.now();
    final dateStr = '${now.day}/${now.month}/${now.year}';

    doc.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.all(36),
        header: (_) => pw.Container(
          padding: const pw.EdgeInsets.only(bottom: 12),
          decoration: const pw.BoxDecoration(
            border: pw.Border(
              bottom:
                  pw.BorderSide(color: PdfColor.fromInt(0xFF6C4DF6), width: 2),
            ),
          ),
          child: pw.Row(
            mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
            children: [
              pw.Column(
                crossAxisAlignment: pw.CrossAxisAlignment.start,
                children: [
                  pw.Text(
                    art.displayName,
                    style: const pw.TextStyle(
                      fontSize: 18,
                      fontWeight: pw.FontWeight.bold,
                      color: PdfColor.fromInt(0xFF6C4DF6),
                    ),
                  ),
                  pw.SizedBox(height: 2),
                  pw.Text(
                    'MedSimplify Patient Communication · Generated $dateStr',
                    style: const pw.TextStyle(
                      fontSize: 9,
                      color: PdfColor.fromInt(0xFF6B7280),
                    ),
                  ),
                ],
              ),
              pw.Container(
                padding:
                    const pw.EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: const pw.BoxDecoration(
                  color: PdfColor.fromInt(0xFFEDE9FE),
                  borderRadius: pw.BorderRadius.all(pw.Radius.circular(6)),
                ),
                child: pw.Text(
                  art.fileExtension,
                  style: const pw.TextStyle(
                    fontSize: 9,
                    fontWeight: pw.FontWeight.bold,
                    color: PdfColor.fromInt(0xFF6C4DF6),
                  ),
                ),
              ),
            ],
          ),
        ),
        footer: (_) => pw.Container(
          alignment: pw.Alignment.center,
          padding: const pw.EdgeInsets.only(top: 12),
          child: pw.Text(
            'For educational and research use only. Always consult a qualified medical professional for diagnosis and treatment.',
            style: const pw.TextStyle(
              fontSize: 8,
              color: PdfColor.fromInt(0xFF9CA3AF),
            ),
            textAlign: pw.TextAlign.center,
          ),
        ),
        build: (_) => [
          pw.Padding(
            padding: const pw.EdgeInsets.symmetric(vertical: 12),
            child: pw.Text(
              art.content,
              style: const pw.TextStyle(fontSize: 10.5, lineSpacing: 4),
            ),
          ),
        ],
      ),
    );

    await Printing.layoutPdf(
      onLayout: (_) async => doc.save(),
      name: '${art.title.toLowerCase().replaceAll(' ', '_')}.pdf',
    );
  }

  void _showArtifactFullscreen() {
    final art = _currentArtifact;
    if (art == null) return;

    showDialog(
      context: context,
      builder: (ctx) {
        final isDark = Theme.of(ctx).brightness == Brightness.dark;
        return Dialog.fullscreen(
          backgroundColor: isDark ? AppTheme.bgDark : AppTheme.bgLight,
          child: Scaffold(
            appBar: AppBar(
              title: Text(art.displayName),
              leading: IconButton(
                icon: const Icon(Icons.close_rounded),
                onPressed: () => Navigator.pop(ctx),
              ),
              actions: [
                IconButton(
                  icon: const Icon(Icons.copy_rounded),
                  tooltip: 'Copy',
                  onPressed: _copyContent,
                ),
                IconButton(
                  icon: const Icon(Icons.picture_as_pdf_rounded),
                  tooltip: 'Export PDF',
                  onPressed: _exportPdf,
                ),
              ],
            ),
            body: Padding(
              padding: const EdgeInsets.all(24),
              child: SingleChildScrollView(
                child: MarkdownBody(
                  data: art.content,
                  selectable: true,
                  styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(ctx)),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final art = _currentArtifact;

    // Palette mimicking Claude's dark & clean aesthetic
    final panelBg = isDark ? const Color(0xFF13171F) : const Color(0xFFF9FAFB);
    final editorBg = isDark ? const Color(0xFF0D1117) : Colors.white;
    final borderColor = isDark ? const Color(0xFF282E39) : const Color(0xFFE5E7EB);
    final headerBg = isDark ? const Color(0xFF161B22) : Colors.white;
    final textPrimary = isDark ? const Color(0xFFE6EDF3) : const Color(0xFF1F2937);
    final textMuted = isDark ? const Color(0xFF8B949E) : const Color(0xFF6B7280);

    if (art == null) {
      return Container(
        color: panelBg,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.dashboard_customize_rounded,
                  size: 48, color: textMuted.withValues(alpha: 0.4)),
              const SizedBox(height: 12),
              Text(
                'No Artifacts Generated Yet',
                style: GoogleFonts.inter(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: textPrimary,
                ),
              ),
              const SizedBox(height: 6),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: Text(
                  'Paste or simplify a discharge summary in the chat to create interactive clinical artifacts.',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: textMuted,
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }

    final lines = art.content.split('\n');

    return Container(
      decoration: BoxDecoration(
        color: panelBg,
        border: Border(
          left: BorderSide(color: borderColor, width: 1),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // ── Top Claude-style Artifact Header ────────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: headerBg,
              border: Border(
                bottom: BorderSide(color: borderColor, width: 1),
              ),
            ),
            child: Row(
              children: [
                // File/Artifact Type Badge
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: isDark
                        ? const Color(0xFF1E1E2E)
                        : const Color(0xFFEDE9FE),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: isDark
                          ? const Color(0xFF3B3B54)
                          : const Color(0xFFDDD6FE),
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(art.icon,
                          size: 13,
                          color: isDark
                              ? const Color(0xFFA78BFA)
                              : const Color(0xFF6C4DF6)),
                      const SizedBox(width: 5),
                      Text(
                        art.fileExtension,
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: isDark
                              ? const Color(0xFFA78BFA)
                              : const Color(0xFF6C4DF6),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),

                // Artifact Selector (if multiple)
                Expanded(
                  child: widget.artifacts.length > 1
                      ? PopupMenuButton<int>(
                          initialValue: widget.selectedIndex,
                          onSelected: widget.onSelectArtifact,
                          tooltip: 'Switch artifact',
                          child: Row(
                            children: [
                              Flexible(
                                child: Text(
                                  art.displayName,
                                  style: GoogleFonts.inter(
                                    fontSize: 13,
                                    fontWeight: FontWeight.w600,
                                    color: textPrimary,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              const SizedBox(width: 4),
                              Icon(Icons.keyboard_arrow_down_rounded,
                                  size: 16, color: textMuted),
                            ],
                          ),
                          itemBuilder: (ctx) {
                            return widget.artifacts.asMap().entries.map((e) {
                              final index = e.key;
                              final item = e.value;
                              final isSelected = index == widget.selectedIndex;
                              return PopupMenuItem<int>(
                                value: index,
                                child: Row(
                                  children: [
                                    Icon(item.icon,
                                        size: 16,
                                        color: isSelected
                                            ? const Color(0xFF6C4DF6)
                                            : textMuted),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Text(
                                            item.displayName,
                                            style: GoogleFonts.inter(
                                              fontSize: 12.5,
                                              fontWeight: isSelected
                                                  ? FontWeight.w700
                                                  : FontWeight.w500,
                                            ),
                                          ),
                                          Text(
                                            item.subtitle,
                                            style: GoogleFonts.inter(
                                              fontSize: 10.5,
                                              color: textMuted,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    if (isSelected)
                                      const Icon(Icons.check_rounded,
                                          size: 16, color: Color(0xFF6C4DF6)),
                                  ],
                                ),
                              );
                            }).toList();
                          },
                        )
                      : Text(
                          art.displayName,
                          style: GoogleFonts.inter(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: textPrimary,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                ),

                // Claude-style Copy button
                OutlinedButton.icon(
                  onPressed: _copyContent,
                  icon: Icon(
                    _isCopied ? Icons.check_rounded : Icons.copy_rounded,
                    size: 13,
                    color: _isCopied
                        ? const Color(0xFF10B981)
                        : textMuted,
                  ),
                  label: Text(
                    _isCopied ? 'Copied' : 'Copy',
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: _isCopied
                          ? const Color(0xFF10B981)
                          : textPrimary,
                    ),
                  ),
                  style: OutlinedButton.styleFrom(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    minimumSize: Size.zero,
                    side: BorderSide(color: borderColor),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6),
                    ),
                  ),
                ),
                const SizedBox(width: 6),

                // PDF Export button
                IconButton(
                  icon: Icon(Icons.picture_as_pdf_outlined,
                      size: 17, color: textMuted),
                  tooltip: 'Export PDF',
                  padding: const EdgeInsets.all(6),
                  constraints: const BoxConstraints(),
                  onPressed: _exportPdf,
                ),
                const SizedBox(width: 4),

                // Fullscreen button
                IconButton(
                  icon: Icon(Icons.open_in_full_rounded,
                      size: 15, color: textMuted),
                  tooltip: 'Full Screen',
                  padding: const EdgeInsets.all(6),
                  constraints: const BoxConstraints(),
                  onPressed: _showArtifactFullscreen,
                ),
                const SizedBox(width: 4),

                // Close Button (✕)
                IconButton(
                  icon: Icon(Icons.close_rounded, size: 18, color: textMuted),
                  tooltip: 'Close Artifacts Panel',
                  padding: const EdgeInsets.all(6),
                  constraints: const BoxConstraints(),
                  onPressed: widget.onClose,
                ),
              ],
            ),
          ),

          // ── Sub-header: Metadata & View Toggle ──────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            color: isDark ? const Color(0xFF10141C) : const Color(0xFFF3F4F6),
            child: Row(
              children: [
                Text(
                  '${art.lineCount} lines · ${art.wordCount} words',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    color: textMuted,
                  ),
                ),
                const Spacer(),

                // Toggle: Formatted vs Claude Raw Code/Text
                InkWell(
                  onTap: () => setState(() => _rawView = !_rawView),
                  borderRadius: BorderRadius.circular(4),
                  child: Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          _rawView
                              ? Icons.article_outlined
                              : Icons.code_rounded,
                          size: 13,
                          color: const Color(0xFF6C4DF6),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          _rawView ? 'Rendered View' : 'Source View',
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: const Color(0xFF6C4DF6),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),

          // ── Artifact Content Area ───────────────────────────────────────────
          Expanded(
            child: Container(
              color: editorBg,
              child: _rawView
                  // Claude-style Code Editor / Monospace with line numbers
                  ? ListView.builder(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      itemCount: lines.length,
                      itemBuilder: (context, index) {
                        return Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 1.5),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              SizedBox(
                                width: 36,
                                child: Text(
                                  '${index + 1}',
                                  textAlign: TextAlign.right,
                                  style: GoogleFonts.jetBrainsMono(
                                    fontSize: 11.5,
                                    color: textMuted.withValues(alpha: 0.5),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 16),
                              Expanded(
                                child: SelectableText(
                                  lines[index].isEmpty ? ' ' : lines[index],
                                  style: GoogleFonts.jetBrainsMono(
                                    fontSize: 12,
                                    color: textPrimary,
                                    height: 1.45,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    )
                  // Formatted Clinical Document View
                  : Scrollbar(
                      thumbVisibility: true,
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Document Header card
                            Container(
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                color: isDark
                                    ? const Color(0xFF161B22)
                                    : const Color(0xFFF9FAFB),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: borderColor),
                              ),
                              child: Row(
                                children: [
                                  Container(
                                    padding: const EdgeInsets.all(10),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFF6C4DF6)
                                          .withValues(alpha: 0.12),
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: Icon(art.icon,
                                        color: const Color(0xFF6C4DF6),
                                        size: 20),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          art.displayName,
                                          style: GoogleFonts.inter(
                                            fontSize: 14,
                                            fontWeight: FontWeight.w700,
                                            color: textPrimary,
                                          ),
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          art.subtitle,
                                          style: GoogleFonts.inter(
                                            fontSize: 11.5,
                                            color: textMuted,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 16),

                            // Markdown content
                            MarkdownBody(
                              data: art.content,
                              selectable: true,
                              styleSheet: MarkdownStyleSheet(
                                p: GoogleFonts.inter(
                                  fontSize: 13.5,
                                  color: textPrimary,
                                  height: 1.65,
                                ),
                                strong: GoogleFonts.inter(
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w700,
                                  color: textPrimary,
                                ),
                                em: GoogleFonts.inter(
                                  fontSize: 13,
                                  fontStyle: FontStyle.italic,
                                  color: textMuted,
                                ),
                                h1: GoogleFonts.inter(
                                  fontSize: 17,
                                  fontWeight: FontWeight.w800,
                                  color: const Color(0xFF6C4DF6),
                                  height: 1.8,
                                ),
                                h2: GoogleFonts.inter(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w700,
                                  color: textPrimary,
                                  height: 1.6,
                                ),
                                h3: GoogleFonts.inter(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: textPrimary,
                                  height: 1.5,
                                ),
                                listBullet: GoogleFonts.inter(
                                  fontSize: 13.5,
                                  color: const Color(0xFF6C4DF6),
                                ),
                                blockquote: GoogleFonts.inter(
                                  fontSize: 13,
                                  color: textMuted,
                                ),
                                blockquoteDecoration: BoxDecoration(
                                  color: isDark
                                      ? const Color(0xFF1E293B)
                                      : const Color(0xFFF1F5F9),
                                  borderRadius: BorderRadius.circular(8),
                                  border: const Border(
                                    left: BorderSide(
                                      color: Color(0xFF6C4DF6),
                                      width: 4,
                                    ),
                                  ),
                                ),
                                code: GoogleFonts.jetBrainsMono(
                                  fontSize: 12,
                                  backgroundColor: isDark
                                      ? const Color(0xFF1F242C)
                                      : const Color(0xFFE2E8F0),
                                  color: isDark
                                      ? const Color(0xFFA78BFA)
                                      : const Color(0xFF4A2DD4),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
            ),
          ),

          // ── Bottom Action: "Ask AI about this" ──────────────────────────────
          if (widget.onAskAboutArtifact != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              decoration: BoxDecoration(
                color: headerBg,
                border: Border(
                  top: BorderSide(color: borderColor, width: 1),
                ),
              ),
              child: Row(
                children: [
                  const Icon(Icons.forum_outlined,
                      size: 15, color: Color(0xFF6C4DF6)),
                  const SizedBox(width: 8),
                  Text(
                    'Have questions about this artifact?',
                    style: GoogleFonts.inter(fontSize: 11.5, color: textMuted),
                  ),
                  const Spacer(),
                  TextButton(
                    onPressed: () {
                      widget.onAskAboutArtifact!(
                          'Can you explain the key points of the ${art.displayName} in simple words?');
                    },
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 4),
                      minimumSize: Size.zero,
                    ),
                    child: Text(
                      'Ask AI →',
                      style: GoogleFonts.inter(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w700,
                        color: const Color(0xFF6C4DF6),
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
