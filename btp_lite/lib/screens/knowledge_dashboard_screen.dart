import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/api_model.dart';
import '../models/discharge_knowledge.dart';
import '../screens/chat_screen.dart';
import '../models/simplify_result.dart';
import '../theme/app_theme.dart';
import '../widgets/knowledge_flash_card.dart';

class KnowledgeDashboardScreen extends StatefulWidget {
  final DischargeKnowledge knowledge;
  final ApiModel model;

  const KnowledgeDashboardScreen({
    super.key,
    required this.knowledge,
    required this.model,
  });

  @override
  State<KnowledgeDashboardScreen> createState() =>
      _KnowledgeDashboardScreenState();
}

class _KnowledgeDashboardScreenState extends State<KnowledgeDashboardScreen> {
  final _pageController = PageController(viewportFraction: 0.92);
  int _currentPage = 0;

  late final List<KnowledgeFlashCard> _cards;
  late final List<String> _smartChips;

  @override
  void initState() {
    super.initState();
    _buildCards();
    _buildChips();
  }

  void _buildCards() {
    final k = widget.knowledge;
    _cards = [
      KnowledgeFlashCard.diagnosis(k),
      if (k.anomalies.isNotEmpty) KnowledgeFlashCard.anomalies(k),
      if (k.medications.isNotEmpty) KnowledgeFlashCard.medications(k),
      if (k.hasAppointments) KnowledgeFlashCard.appointments(k),
      if (k.warningSignals.isNotEmpty) KnowledgeFlashCard.warnings(k),
    ];
  }

  void _buildChips() {
    final k = widget.knowledge;
    _smartChips = [];

    // Diagnosis chip — always present
    _smartChips.add('🩺 Explain my diagnosis in simple words');

    // Medication chip
    if (k.medications.isNotEmpty) {
      final firstName = k.medications.first.name;
      _smartChips.add('💊 Why do I need $firstName?');
    }

    // Anomaly chip
    final criticals =
        k.anomalies.where((a) => a.severity == 'critical').toList();
    if (criticals.isNotEmpty) {
      _smartChips.add('🔬 Explain my critical test results');
    } else if (k.anomalies.isNotEmpty) {
      _smartChips.add('🔬 Explain my lab and test findings');
    }

    // Appointment chip
    if (k.hasAppointments) {
      _smartChips.add('📅 When is my next doctor appointment?');
    }

    // Warning chip
    if (k.warningSignals.isNotEmpty) {
      _smartChips.add('🚨 What are my emergency warning signs?');
    }

    // Diet chip
    _smartChips.add('🥗 What diet should I follow at home?');

    // Activity chip
    _smartChips.add('🏃 What activities can I do during recovery?');
  }

  void _openChat(BuildContext context, {String? initialMessage}) {
    final k = widget.knowledge;

    // Build a SimplifyResult-like object for ChatService compatibility
    // We embed the knowledge as both the originalText (as JSON) and simplifiedText
    final syntheticResult = SimplifyResult(
      originalText: k.toSystemPromptContext(),
      simplifiedText: _buildPatientFriendlySummary(k),
      modelName: widget.model.name,
      provider: widget.model.provider,
      timestamp: DateTime.now(),
      strategy: 'knowledge-extraction',
      originalSnippet: k.primaryDiagnosis,
    );

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ChatScreen(
          result: syntheticResult,
          model: widget.model,
          knowledge: widget.knowledge,
          initialMessage: initialMessage,
        ),
      ),
    );
  }

  String _buildPatientFriendlySummary(DischargeKnowledge k) {
    final sb = StringBuffer();
    sb.writeln('**Your Discharge Summary — Key Points**\n');
    sb.writeln('**Diagnosis:** ${k.primaryDiagnosis}');
    if (k.primaryLayExplanation.isNotEmpty) {
      sb.writeln('_(${k.primaryLayExplanation})_\n');
    }
    if (k.medications.isNotEmpty) {
      sb.writeln('**Your Medicines:**');
      for (final m in k.medications) {
        sb.writeln('• **${m.name}**: ${m.purposeLay} — ${m.timingDosage}');
      }
      sb.writeln();
    }
    if (k.warningSignals.isNotEmpty) {
      sb.writeln('**Emergency Warning Signs:**');
      for (final w in k.warningSignals) {
        sb.writeln('• $w');
      }
    }
    return sb.toString();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? AppTheme.bgDark : AppTheme.bgLight;
    final textColor =
        isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor =
        isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;
    final borderColor = isDark ? AppTheme.borderDark : AppTheme.borderLight;
    final k = widget.knowledge;

    return Scaffold(
      backgroundColor: bgColor,
      body: CustomScrollView(
        slivers: [
          // ── Gradient App Bar ───────────────────────────────────────────────
          SliverAppBar(
            expandedHeight: 180,
            pinned: true,
            backgroundColor: isDark ? AppTheme.surfaceDark : AppTheme.surfaceLight,
            leading: IconButton(
              icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
              onPressed: () => Navigator.pop(context),
            ),
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    colors: [Color(0xFF4A2DD4), Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 48, 20, 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: const Icon(Icons.health_and_safety_rounded,
                                  color: Colors.white, size: 18),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                'Your Health Summary',
                                style: GoogleFonts.inter(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.white.withValues(alpha: 0.9),
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        Text(
                          k.primaryDiagnosis,
                          style: GoogleFonts.inter(
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                            height: 1.3,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            if (k.stayDuration != null) ...[
                              _HeaderChip(
                                icon: Icons.hotel_rounded,
                                label: k.stayDuration!,
                              ),
                              const SizedBox(width: 8),
                            ],
                            if (k.outcome != null)
                              _HeaderChip(
                                icon: k.outcome == 'alive'
                                    ? Icons.favorite_rounded
                                    : Icons.do_not_disturb_rounded,
                                label: k.outcome!,
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),

          SliverToBoxAdapter(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 20),

                // ── Flash Card Carousel ────────────────────────────────────
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    children: [
                      Text(
                        'Health Cards',
                        style: GoogleFonts.inter(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: textColor,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${_currentPage + 1} / ${_cards.length}',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: subColor,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                SizedBox(
                  height: 340,
                  child: PageView.builder(
                    controller: _pageController,
                    onPageChanged: (i) => setState(() => _currentPage = i),
                    itemCount: _cards.length,
                    itemBuilder: (context, index) {
                      return _cards[index]
                          .animate()
                          .fadeIn(duration: 300.ms)
                          .slideX(begin: 0.03, end: 0, duration: 300.ms);
                    },
                  ),
                ),

                // ── Page Dots ──────────────────────────────────────────────
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(_cards.length, (i) {
                    final isActive = i == _currentPage;
                    return AnimatedContainer(
                      duration: const Duration(milliseconds: 250),
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      width: isActive ? 20 : 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: isActive
                            ? const Color(0xFF6C4DF6)
                            : borderColor,
                        borderRadius: BorderRadius.circular(3),
                      ),
                    );
                  }),
                ),

                const SizedBox(height: 24),

                // ── Smart Question Chips ───────────────────────────────────
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Text(
                    'Common Questions',
                    style: GoogleFonts.inter(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: textColor,
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Text(
                    'Tap a question to ask your AI assistant',
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: subColor,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _smartChips.asMap().entries.map((entry) {
                      final chip = entry.value;
                      return Material(
                        color: Colors.transparent,
                        child: InkWell(
                          borderRadius: BorderRadius.circular(22),
                          onTap: () => _openChat(context, initialMessage: chip),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 14, vertical: 9),
                            decoration: BoxDecoration(
                              color: isDark
                                  ? const Color(0xFF2D1F5E)
                                  : const Color(0xFFEDE9FE),
                              borderRadius: BorderRadius.circular(22),
                              border: Border.all(
                                color: const Color(0xFF6C4DF6).withValues(alpha: 0.3),
                              ),
                            ),
                            child: Text(
                              chip,
                              style: GoogleFonts.inter(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: isDark
                                    ? const Color(0xFFA78BFA)
                                    : const Color(0xFF6C4DF6),
                              ),
                            ),
                          ),
                        ),
                      )
                          .animate()
                          .fadeIn(
                              duration: 250.ms,
                              delay: Duration(milliseconds: 50 * entry.key))
                          .slideX(
                              begin: 0.05,
                              end: 0,
                              duration: 250.ms,
                              delay: Duration(milliseconds: 50 * entry.key));
                    }).toList(),
                  ),
                ),

                const SizedBox(height: 100), // space for FAB
              ],
            ),
          ),
        ],
      ),

      // ── Start Chat FAB ─────────────────────────────────────────────────────
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openChat(context),
        backgroundColor: const Color(0xFF6C4DF6),
        foregroundColor: Colors.white,
        elevation: 4,
        icon: const Icon(Icons.forum_rounded),
        label: Text(
          'Start Chat',
          style: GoogleFonts.inter(
            fontSize: 14,
            fontWeight: FontWeight.w700,
          ),
        ),
      )
          .animate()
          .fadeIn(duration: 400.ms, delay: 500.ms)
          .slideY(begin: 0.2, end: 0, duration: 400.ms, delay: 500.ms),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }
}

class _HeaderChip extends StatelessWidget {
  final IconData icon;
  final String label;
  const _HeaderChip({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: Colors.white),
          const SizedBox(width: 4),
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: Colors.white,
            ),
          ),
        ],
      ),
    );
  }
}
