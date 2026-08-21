import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import '../models/api_model.dart';
import '../models/discharge_knowledge.dart';
import '../services/extraction_service.dart';
import '../services/storage_service.dart';
import '../theme/app_theme.dart';
import 'knowledge_dashboard_screen.dart';

class DischargeUploadScreen extends StatefulWidget {
  const DischargeUploadScreen({super.key});

  @override
  State<DischargeUploadScreen> createState() => _DischargeUploadScreenState();
}

class _DischargeUploadScreenState extends State<DischargeUploadScreen> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();

  bool _isLoading = false;
  String? _error;
  final List<_ExtractionStep> _steps = [];

  static const _stepDefs = [
    'Reading discharge summary',
    'Extracting clinical facts with AI',
    'Building your knowledge base',
  ];

  @override
  void initState() {
    super.initState();
    _steps.addAll(_stepDefs.map((s) => _ExtractionStep(label: s)));
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _onStepUpdate(String step, bool done) {
    setState(() {
      final idx = _steps.indexWhere((s) => s.label == step);
      if (idx != -1) {
        if (!done) {
          _steps[idx] = _ExtractionStep(label: step, state: _StepState.active);
        } else {
          _steps[idx] = _ExtractionStep(label: step, state: _StepState.done);
          // Activate next step
          if (idx + 1 < _steps.length) {
            _steps[idx + 1] =
                _ExtractionStep(label: _steps[idx + 1].label, state: _StepState.waiting);
          }
        }
      }
    });
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['txt'],
      withData: true,
    );
    if (result != null && result.files.single.bytes != null) {
      final text = String.fromCharCodes(result.files.single.bytes!);
      _controller.text = text;
    }
  }

  Future<void> _analyseText() async {
    final text = _controller.text.trim();
    if (text.length < 50) {
      setState(() => _error =
          'Please paste a discharge summary (at least 50 characters).');
      return;
    }

    final storage = context.read<StorageService>();
    if (storage.groqKey.isEmpty) {
      setState(() => _error =
          'Groq API key not set. Please add it in Settings first.');
      return;
    }

    // Reset steps
    setState(() {
      _isLoading = true;
      _error = null;
      for (int i = 0; i < _steps.length; i++) {
        _steps[i] = _ExtractionStep(
          label: _stepDefs[i],
          state: i == 0 ? _StepState.waiting : _StepState.idle,
        );
      }
    });

    try {
      final service = ExtractionService(storage.groqKey);
      final knowledge = await service.extract(
        text,
        onStep: _onStepUpdate,
      );

      if (!mounted) return;

      // Default to first available Groq model for chatbot
      final model = ApiModel.all.firstWhere(
        (m) => m.provider == 'groq',
        orElse: () => ApiModel.all.first,
      );

      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => KnowledgeDashboardScreen(
            knowledge: knowledge,
            model: model,
          ),
        ),
      );
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = e.toString().replaceFirst('Exception: ', '');
        for (final s in _steps) {
          if (s.state == _StepState.active) {
            final idx = _steps.indexOf(s);
            _steps[idx] = _ExtractionStep(label: s.label, state: _StepState.idle);
          }
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? AppTheme.bgDark : AppTheme.bgLight;
    final cardColor = isDark ? AppTheme.cardDark : AppTheme.cardLight;
    final textColor = isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor = isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;
    final borderColor = isDark ? AppTheme.borderDark : AppTheme.borderLight;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: isDark ? AppTheme.surfaceDark : AppTheme.surfaceLight,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.pop(context),
        ),
        title: Row(
          children: [
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.description_rounded,
                  color: Colors.white, size: 15),
            ),
            const SizedBox(width: 10),
            Text(
              'Chat with Discharge Summary',
              style: GoogleFonts.inter(
                fontSize: 15,
                fontWeight: FontWeight.w700,
                color: textColor,
              ),
            ),
          ],
        ),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Divider(height: 1, color: borderColor),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: _isLoading
                  ? _buildLoadingView(isDark, cardColor, textColor, subColor)
                  : _buildUploadView(
                      isDark, cardColor, textColor, subColor, borderColor),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildUploadView(
    bool isDark,
    Color cardColor,
    Color textColor,
    Color subColor,
    Color borderColor,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // ── Header ────────────────────────────────────────────────────────────
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: isDark
                  ? [const Color(0xFF1E1445), const Color(0xFF0D1117)]
                  : [const Color(0xFFEDE9FE), const Color(0xFFF5F7FA)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: const Color(0xFF6C4DF6).withValues(alpha: 0.3),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.health_and_safety_rounded,
                        color: Colors.white, size: 22),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'MedSimplify Chat',
                          style: GoogleFonts.inter(
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                            color: textColor,
                          ),
                        ),
                        Text(
                          'AI-powered Q&A about your health',
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            color: const Color(0xFF6C4DF6),
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Text(
                'Paste your hospital discharge summary below. Our AI will extract your diagnoses, medications, lab results, and appointments — then you can ask any question in plain language.',
                style: GoogleFonts.inter(
                  fontSize: 13,
                  color: subColor,
                  height: 1.6,
                ),
              ),
            ],
          ),
        )
            .animate()
            .fadeIn(duration: 400.ms)
            .slideY(begin: -0.05, end: 0, duration: 400.ms),

        const SizedBox(height: 20),

        // ── Step Indicator ────────────────────────────────────────────────────
        _buildStepIndicator(textColor, subColor),

        const SizedBox(height: 20),

        // ── Text Area ────────────────────────────────────────────────────────
        Container(
          decoration: BoxDecoration(
            color: cardColor,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: borderColor),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 14, 16, 0),
                child: Row(
                  children: [
                    Icon(Icons.article_outlined,
                        size: 16, color: const Color(0xFF6C4DF6)),
                    const SizedBox(width: 8),
                    Text(
                      'Discharge Summary Text',
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: textColor,
                      ),
                    ),
                    const Spacer(),
                    TextButton.icon(
                      onPressed: _pickFile,
                      icon: const Icon(Icons.upload_file_rounded, size: 15),
                      label: Text(
                        'Upload .txt',
                        style: GoogleFonts.inter(fontSize: 12),
                      ),
                      style: TextButton.styleFrom(
                        foregroundColor: const Color(0xFF6C4DF6),
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                      ),
                    ),
                  ],
                ),
              ),
              const Divider(height: 12),
              TextField(
                controller: _controller,
                focusNode: _focusNode,
                maxLines: 12,
                minLines: 8,
                style: GoogleFonts.inter(
                  fontSize: 13,
                  color: textColor,
                  height: 1.6,
                ),
                decoration: InputDecoration(
                  hintText:
                      'Paste your discharge summary here...\n\nFor example: "Male, 42 years old. Admitted for Crohn\'s disease with abdominal sepsis. Prescribed Ertapenem 1g/day..."',
                  hintStyle: GoogleFonts.inter(
                    fontSize: 13,
                    color: subColor.withValues(alpha: 0.6),
                    height: 1.6,
                  ),
                  border: InputBorder.none,
                  contentPadding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                ),
              ),
            ],
          ),
        )
            .animate()
            .fadeIn(duration: 400.ms, delay: 150.ms)
            .slideY(begin: 0.05, end: 0, duration: 400.ms, delay: 150.ms),

        if (_error != null) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.errorSurface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppTheme.error.withValues(alpha: 0.3)),
            ),
            child: Row(
              children: [
                const Icon(Icons.error_outline_rounded,
                    color: AppTheme.error, size: 16),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _error!,
                    style: GoogleFonts.inter(
                        fontSize: 12, color: AppTheme.error),
                  ),
                ),
              ],
            ),
          ).animate().fadeIn(duration: 300.ms),
        ],

        const SizedBox(height: 20),

        // ── Analyse Button ───────────────────────────────────────────────────
        SizedBox(
          height: 52,
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
              ),
              borderRadius: BorderRadius.circular(14),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF6C4DF6).withValues(alpha: 0.35),
                  blurRadius: 16,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: ElevatedButton.icon(
              onPressed: _analyseText,
              icon: const Icon(Icons.auto_awesome_rounded, size: 18),
              label: Text(
                'Analyse Summary',
                style: GoogleFonts.inter(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                ),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.transparent,
                shadowColor: Colors.transparent,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
            ),
          ),
        )
            .animate()
            .fadeIn(duration: 400.ms, delay: 250.ms)
            .slideY(begin: 0.05, end: 0, duration: 400.ms, delay: 250.ms),

        const SizedBox(height: 12),
        Center(
          child: Text(
            '🔒 Your summary is processed via Groq AI and never stored',
            style: GoogleFonts.inter(
              fontSize: 11,
              color: subColor.withValues(alpha: 0.7),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildLoadingView(
    bool isDark,
    Color cardColor,
    Color textColor,
    Color subColor,
  ) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const SizedBox(height: 40),
        // Animated brain/health icon
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
            ),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF6C4DF6).withValues(alpha: 0.4),
                blurRadius: 24,
                spreadRadius: 2,
              ),
            ],
          ),
          child: const Icon(Icons.health_and_safety_rounded,
              color: Colors.white, size: 40),
        )
            .animate(onPlay: (c) => c.repeat())
            .shimmer(duration: 1500.ms, color: Colors.white.withValues(alpha: 0.3))
            .then()
            .scale(
              begin: const Offset(1.0, 1.0),
              end: const Offset(1.05, 1.05),
              duration: 800.ms,
            )
            .then()
            .scale(
              begin: const Offset(1.05, 1.05),
              end: const Offset(1.0, 1.0),
              duration: 800.ms,
            ),

        const SizedBox(height: 28),
        Text(
          'Analysing Your Summary',
          style: GoogleFonts.inter(
            fontSize: 20,
            fontWeight: FontWeight.w800,
            color: textColor,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'Extracting diagnoses, medications & more...',
          style: GoogleFonts.inter(fontSize: 13, color: subColor),
        ),

        const SizedBox(height: 36),

        // Step progress
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: cardColor,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: const Color(0xFF6C4DF6).withValues(alpha: 0.2),
            ),
          ),
          child: Column(
            children: _steps.asMap().entries.map((entry) {
              final step = entry.value;
              return _buildStepRow(step, textColor, subColor);
            }).toList(),
          ),
        ),
      ],
    );
  }

  Widget _buildStepRow(_ExtractionStep step, Color textColor, Color subColor) {
    Widget leading;
    Color color;

    switch (step.state) {
      case _StepState.done:
        color = AppTheme.success;
        leading = const Icon(Icons.check_circle_rounded,
            color: AppTheme.success, size: 20);
        break;
      case _StepState.active:
        color = const Color(0xFF6C4DF6);
        leading = SizedBox(
          width: 20,
          height: 20,
          child: CircularProgressIndicator(
            strokeWidth: 2,
            color: const Color(0xFF6C4DF6),
          ),
        );
        break;
      case _StepState.waiting:
        color = subColor.withValues(alpha: 0.5);
        leading = Icon(Icons.radio_button_unchecked_rounded,
            color: subColor.withValues(alpha: 0.4), size: 20);
        break;
      case _StepState.idle:
        color = subColor.withValues(alpha: 0.4);
        leading = Icon(Icons.circle_outlined,
            color: subColor.withValues(alpha: 0.3), size: 20);
        break;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        children: [
          leading,
          const SizedBox(width: 14),
          Text(
            step.label,
            style: GoogleFonts.inter(
              fontSize: 14,
              fontWeight: step.state == _StepState.active
                  ? FontWeight.w600
                  : FontWeight.w400,
              color: step.state == _StepState.idle
                  ? subColor.withValues(alpha: 0.4)
                  : textColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStepIndicator(Color textColor, Color subColor) {
    final steps = ['Upload', 'Analyse', 'Chat'];
    return Row(
      children: steps.asMap().entries.map((entry) {
        final i = entry.key;
        final label = entry.value;
        final isActive = i == 0;
        return Expanded(
          child: Row(
            children: [
              Expanded(
                child: Column(
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        color: isActive
                            ? const Color(0xFF6C4DF6)
                            : const Color(0xFF6C4DF6).withValues(alpha: 0.15),
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: Text(
                          '${i + 1}',
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: isActive
                                ? Colors.white
                                : const Color(0xFF6C4DF6),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      label,
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        fontWeight:
                            isActive ? FontWeight.w600 : FontWeight.w400,
                        color: isActive
                            ? const Color(0xFF6C4DF6)
                            : subColor,
                      ),
                    ),
                  ],
                ),
              ),
              if (i < steps.length - 1)
                Expanded(
                  child: Divider(
                    color: const Color(0xFF6C4DF6).withValues(alpha: 0.2),
                    thickness: 1.5,
                  ),
                ),
            ],
          ),
        );
      }).toList(),
    );
  }
}

enum _StepState { idle, waiting, active, done }

class _ExtractionStep {
  final String label;
  final _StepState state;
  const _ExtractionStep({required this.label, this.state = _StepState.idle});
}
