import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/api_model.dart';
import '../models/simplify_result.dart';
import '../services/simplify_service.dart';
import '../services/storage_service.dart';
import '../theme/app_theme.dart';
import '../widgets/app_drawer.dart';
import '../widgets/loading_overlay.dart';
import '../widgets/model_selector.dart';
import '../widgets/output_card.dart';
import '../widgets/strategy_selector.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  final VoidCallback onToggleTheme;
  final bool isDark;

  const HomeScreen({
    super.key,
    required this.onToggleTheme,
    required this.isDark,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _textController = TextEditingController();
  final _scrollController = ScrollController();

  ApiModel _selectedModel = ApiModel.all.first;
  String _strategy = 'zero-shot';
  bool _loading = false;
  String? _error;
  SimplifyResult? _result;

  @override
  void initState() {
    super.initState();
    _loadPreferences();
  }

  Future<void> _loadPreferences() async {
    final storage = context.read<StorageService>();
    final savedModelId = storage.lastModelId;
    final savedStrategy = storage.lastStrategy;
    final model = ApiModel.all.firstWhere(
      (m) => m.id == savedModelId,
      orElse: () => ApiModel.all.first,
    );
    setState(() {
      _selectedModel = model;
      _strategy = savedStrategy;
    });
  }

  Future<void> _simplify() async {
    final text = _textController.text.trim();
    if (text.isEmpty) {
      setState(() => _error = 'Please paste a discharge summary first.');
      return;
    }

    final storage = context.read<StorageService>();

    // Check API key exists for selected model
    final hasKey = switch (_selectedModel.provider) {
      'cerebras' => storage.cerebrasKey.isNotEmpty,
      'gemini' => storage.geminiKey.isNotEmpty,
      'groq' => storage.groqKey.isNotEmpty,
      _ => false,
    };

    if (!hasKey) {
      setState(() => _error =
          'No API key configured for ${_selectedModel.providerLabel}. Add it in Settings.');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });

    // Save preferences
    await storage.setLastModelId(_selectedModel.id);
    await storage.setLastStrategy(_strategy);

    try {
      final svc = SimplifyService(storage);
      final result = await svc.simplify(
        rawText: text,
        model: _selectedModel,
        strategy: _strategy,
      );
      setState(() => _result = result);
      // Scroll to result
      await Future.delayed(const Duration(milliseconds: 100));
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 400),
          curve: Curves.easeOut,
        );
      }
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      setState(() => _loading = false);
    }
  }

  void _clearAll() {
    _textController.clear();
    setState(() {
      _result = null;
      _error = null;
    });
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = widget.isDark;
    final bgColor = isDark ? AppTheme.bgDark : AppTheme.bgLight;
    final cardColor = isDark ? AppTheme.cardDark : AppTheme.cardLight;
    final borderColor = isDark ? AppTheme.borderDark : AppTheme.borderLight;
    final textColor =
        isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor =
        isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;

    final isWide = MediaQuery.of(context).size.width >= 800;

    return Scaffold(
      backgroundColor: bgColor,
      drawer: AppDrawer(
        isDark: isDark,
        onToggleTheme: widget.onToggleTheme,
      ),
      appBar: AppBar(
        backgroundColor: isDark ? AppTheme.surfaceDark : AppTheme.surfaceLight,
        title: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.medical_services_rounded,
                  color: Colors.white, size: 18),
            ),
            const SizedBox(width: 10),
            Text(
              'MedSimplify',
              style: GoogleFonts.inter(
                fontWeight: FontWeight.w800,
                fontSize: 18,
                color: textColor,
              ),
            ),
            const SizedBox(width: 6),
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFF6C4DF6).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                'Lite',
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: const Color(0xFF6C4DF6),
                ),
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(
              isDark ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
              color: subColor,
            ),
            tooltip: isDark ? 'Light mode' : 'Dark mode',
            onPressed: widget.onToggleTheme,
          ),
          IconButton(
            icon: Icon(Icons.settings_rounded, color: subColor),
            tooltip: 'Settings',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const SettingsScreen()),
            ),
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Divider(height: 1, color: borderColor),
        ),
      ),
      body: SingleChildScrollView(
        controller: _scrollController,
        padding: EdgeInsets.symmetric(
          horizontal: isWide ? 40 : 16,
          vertical: 20,
        ),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1100),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // ── Page header ───────────────────────────────────────────────
                Text(
                  'Discharge Summary Simplifier',
                  style: GoogleFonts.inter(
                    fontSize: isWide ? 26 : 20,
                    fontWeight: FontWeight.w800,
                    color: textColor,
                  ),
                ).animate().fadeIn(duration: 300.ms).slideX(begin: -0.03),
                const SizedBox(height: 6),
                Text(
                  'Paste a clinical discharge summary and get a patient-friendly explanation in Indian Lay English, powered by Cloud AI.',
                  style: GoogleFonts.inter(
                      fontSize: 14, color: subColor, height: 1.5),
                ).animate().fadeIn(delay: 100.ms, duration: 300.ms),
                const SizedBox(height: 24),

                // ── Main layout ───────────────────────────────────────────────
                if (isWide)
                  IntrinsicHeight(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(child: _buildInputCard(cardColor, borderColor,
                            textColor, subColor, isDark)),
                        const SizedBox(width: 20),
                        Expanded(
                            child: _buildOutputSection(
                                cardColor, borderColor, textColor, subColor)),
                      ],
                    ),
                  )
                else ...[
                  _buildInputCard(
                      cardColor, borderColor, textColor, subColor, isDark),
                  const SizedBox(height: 20),
                  _buildOutputSection(
                      cardColor, borderColor, textColor, subColor),
                ],

                const SizedBox(height: 20),
                // ── Disclaimer ────────────────────────────────────────────────
                _buildDisclaimer(isDark),
                const SizedBox(height: 40),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInputCard(Color cardColor, Color borderColor, Color textColor,
      Color subColor, bool isDark) {
    final wordCount = _textController.text
        .trim()
        .split(RegExp(r'\s+'))
        .where((w) => w.isNotEmpty)
        .length;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Text(
                'INPUT',
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: subColor,
                  letterSpacing: 0.8,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Model selector
          ModelSelector(
            selected: _selectedModel,
            models: ApiModel.all,
            onChanged: (m) => setState(() => _selectedModel = m),
          ),
          const SizedBox(height: 16),

          // Strategy selector
          StrategySelector(
            selected: _strategy,
            onChanged: (s) => setState(() => _strategy = s),
          ),
          const SizedBox(height: 16),

          // Text area
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'DISCHARGE SUMMARY',
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: subColor,
                  letterSpacing: 0.8,
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _textController,
                maxLines: 12,
                onChanged: (_) => setState(() {}),
                style: GoogleFonts.inter(
                    fontSize: 13, color: textColor, height: 1.6),
                decoration: InputDecoration(
                  hintText:
                      'Paste the patient\'s discharge summary here…\n\nExample: The patient was admitted with fever, chills, and productive cough…',
                  hintStyle: GoogleFonts.inter(
                      fontSize: 13,
                      color: subColor.withValues(alpha: 0.7),
                      height: 1.6),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: borderColor),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: borderColor),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(
                        color: AppTheme.primaryIndigo, width: 2),
                  ),
                  filled: true,
                  fillColor: isDark
                      ? AppTheme.bgDark
                      : AppTheme.bgLight,
                  contentPadding: const EdgeInsets.all(14),
                ),
              ),
              const SizedBox(height: 4),
              Align(
                alignment: Alignment.centerRight,
                child: Text(
                  '$wordCount words',
                  style: GoogleFonts.inter(
                      fontSize: 11, color: subColor.withValues(alpha: 0.7)),
                ),
              ),
            ],
          ),

          // Error
          if (_error != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFFECACA)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline_rounded,
                      color: Color(0xFFEF4444), size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _error!,
                      style: GoogleFonts.inter(
                          fontSize: 13, color: const Color(0xFFDC2626)),
                    ),
                  ),
                ],
              ),
            ),
          ],

          const SizedBox(height: 16),
          // Buttons
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _loading ? null : _simplify,
                  icon: _loading
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.auto_fix_high_rounded, size: 18),
                  label: Text(_loading ? 'Simplifying…' : '✨ Simplify Summary'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ),
              if (_textController.text.isNotEmpty || _result != null) ...[
                const SizedBox(width: 10),
                OutlinedButton(
                  onPressed: _clearAll,
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                        vertical: 14, horizontal: 16),
                  ),
                  child: const Text('Clear'),
                ),
              ],
            ],
          ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms, delay: 150.ms);
  }

  Widget _buildOutputSection(
      Color cardColor, Color borderColor, Color textColor, Color subColor) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'OUTPUT',
          style: GoogleFonts.inter(
            fontSize: 11,
            fontWeight: FontWeight.w700,
            color: subColor,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 8),
        if (_loading)
          LoadingOverlay(
            message: 'Simplifying using ${_selectedModel.name}…',
          )
        else if (_result != null)
          OutputCard(result: _result!)
        else
          _buildEmptyState(cardColor, borderColor, subColor),
      ],
    ).animate().fadeIn(duration: 300.ms, delay: 200.ms);
  }

  Widget _buildEmptyState(
      Color cardColor, Color borderColor, Color subColor) {
    return Container(
      height: 240,
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
            color: borderColor, style: BorderStyle.solid, width: 1.5),
      ),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.description_outlined,
                size: 40, color: subColor.withValues(alpha: 0.4)),
            const SizedBox(height: 12),
            Text(
              'Your simplified summary will appear here…',
              style: GoogleFonts.inter(fontSize: 13, color: subColor),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDisclaimer(bool isDark) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark
            ? const Color(0xFF1E2A4A)
            : const Color(0xFFEFF6FF),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isDark
              ? const Color(0xFF2D4080)
              : const Color(0xFFBFDBFE),
        ),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline_rounded,
              color: Color(0xFF3B82F6), size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              '⚕ Research use only. Simplified summaries are generated by AI and may contain errors. Always consult a qualified healthcare professional for medical advice.',
              style: GoogleFonts.inter(
                fontSize: 12,
                color: isDark
                    ? const Color(0xFF93C5FD)
                    : const Color(0xFF1E40AF),
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
