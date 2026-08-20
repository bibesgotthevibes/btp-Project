import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../services/storage_service.dart';
import '../theme/app_theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _cerebrasCtrl = TextEditingController();
  final _geminiCtrl = TextEditingController();
  final _groqCtrl = TextEditingController();

  bool _showCerebras = false;
  bool _showGemini = false;
  bool _showGroq = false;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    final storage = context.read<StorageService>();
    _cerebrasCtrl.text = storage.cerebrasKey;
    _geminiCtrl.text = storage.geminiKey;
    _groqCtrl.text = storage.groqKey;
  }

  Future<void> _save() async {
    final storage = context.read<StorageService>();
    await storage.setCerebrasKey(_cerebrasCtrl.text.trim());
    await storage.setGeminiKey(_geminiCtrl.text.trim());
    await storage.setGroqKey(_groqCtrl.text.trim());
    setState(() => _saved = true);
    await Future.delayed(const Duration(seconds: 2));
    if (mounted) setState(() => _saved = false);
  }

  @override
  void dispose() {
    _cerebrasCtrl.dispose();
    _geminiCtrl.dispose();
    _groqCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bgColor = isDark ? AppTheme.bgDark : AppTheme.bgLight;
    final textColor =
        isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final borderColor = isDark ? AppTheme.borderDark : AppTheme.borderLight;

    return Scaffold(
      backgroundColor: bgColor,
      appBar: AppBar(
        backgroundColor: isDark ? AppTheme.surfaceDark : AppTheme.surfaceLight,
        title: Text(
          'Settings',
          style: GoogleFonts.inter(
              fontWeight: FontWeight.w700, color: textColor),
        ),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Divider(height: 1, color: borderColor),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 600),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // ── API Keys section ─────────────────────────────────────────
                _SectionHeader(title: 'API Keys', isDark: isDark),
                const SizedBox(height: 4),
                Text(
                  'Keys are stored locally on your device. Get free keys from each provider.',
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    color: isDark
                        ? AppTheme.textSecondaryDark
                        : AppTheme.textSecondaryLight,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 16),

                // Cerebras
                _ApiKeyTile(
                  provider: 'Cerebras',
                  badge: '⚡',
                  color: const Color(0xFFF59E0B),
                  controller: _cerebrasCtrl,
                  visible: _showCerebras,
                  onToggleVisibility: () =>
                      setState(() => _showCerebras = !_showCerebras),
                  isDark: isDark,
                  helpUrl: 'https://cloud.cerebras.ai',
                  helpText: 'Get free key at cloud.cerebras.ai',
                ).animate().fadeIn(duration: 300.ms, delay: 50.ms),
                const SizedBox(height: 12),

                // Gemini
                _ApiKeyTile(
                  provider: 'Google Gemini',
                  badge: '✦',
                  color: const Color(0xFF6C4DF6),
                  controller: _geminiCtrl,
                  visible: _showGemini,
                  onToggleVisibility: () =>
                      setState(() => _showGemini = !_showGemini),
                  isDark: isDark,
                  helpUrl: 'https://aistudio.google.com',
                  helpText: 'Get free key at aistudio.google.com',
                ).animate().fadeIn(duration: 300.ms, delay: 100.ms),
                const SizedBox(height: 12),

                // Groq
                _ApiKeyTile(
                  provider: 'Groq',
                  badge: '🚀',
                  color: const Color(0xFF10B981),
                  controller: _groqCtrl,
                  visible: _showGroq,
                  onToggleVisibility: () =>
                      setState(() => _showGroq = !_showGroq),
                  isDark: isDark,
                  helpUrl: 'https://console.groq.com',
                  helpText: 'Get free key at console.groq.com',
                ).animate().fadeIn(duration: 300.ms, delay: 150.ms),

                const SizedBox(height: 24),

                // Save button
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _save,
                    icon: Icon(
                      _saved ? Icons.check_circle_rounded : Icons.save_rounded,
                      size: 18,
                    ),
                    label: Text(_saved ? 'Saved ✓' : 'Save API Keys'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: _saved
                          ? const Color(0xFF10B981)
                          : AppTheme.primaryIndigo,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
                ),

                const SizedBox(height: 32),
                const Divider(),
                const SizedBox(height: 20),

                // ── About section ─────────────────────────────────────────────
                _SectionHeader(title: 'About', isDark: isDark),
                const SizedBox(height: 12),
                _AboutItem(
                    label: 'App',
                    value: 'MedSimplify Lite v1.0.0',
                    isDark: isDark),
                _AboutItem(
                    label: 'Purpose',
                    value: 'Medical discharge summary simplification',
                    isDark: isDark),
                _AboutItem(
                    label: 'Target',
                    value: 'Indian Lay English for patients & families',
                    isDark: isDark),
                _AboutItem(
                    label: 'Backend',
                    value: 'None — API calls made directly from app',
                    isDark: isDark),
                _AboutItem(
                    label: 'Data storage',
                    value:
                        'Local device only (shared_preferences)',
                    isDark: isDark),

                const SizedBox(height: 20),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: isDark
                        ? const Color(0xFF1A1A2E)
                        : const Color(0xFFFFFBEB),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: isDark
                          ? const Color(0xFF2D2D5E)
                          : const Color(0xFFFDE68A),
                    ),
                  ),
                  child: Row(
                    children: [
                      const Text('⚠️', style: TextStyle(fontSize: 16)),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'API keys are stored in plain text on your device. This is suitable for research use. Do not use production keys.',
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            color: isDark
                                ? const Color(0xFFFDE68A)
                                : const Color(0xFF92400E),
                            height: 1.5,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 60),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ApiKeyTile extends StatelessWidget {
  final String provider;
  final String badge;
  final Color color;
  final TextEditingController controller;
  final bool visible;
  final VoidCallback onToggleVisibility;
  final bool isDark;
  final String helpUrl;
  final String helpText;

  const _ApiKeyTile({
    required this.provider,
    required this.badge,
    required this.color,
    required this.controller,
    required this.visible,
    required this.onToggleVisibility,
    required this.isDark,
    required this.helpUrl,
    required this.helpText,
  });

  @override
  Widget build(BuildContext context) {
    final cardColor = isDark ? AppTheme.cardDark : AppTheme.cardLight;
    final borderColor = isDark ? AppTheme.borderDark : AppTheme.borderLight;
    final textColor =
        isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor =
        isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Center(
                  child: Text(badge, style: const TextStyle(fontSize: 16)),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      provider,
                      style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: textColor),
                    ),
                    Text(
                      helpText,
                      style: GoogleFonts.inter(fontSize: 11, color: color),
                    ),
                  ],
                ),
              ),
              // Status indicator
              Builder(builder: (_) {
                final hasKey = controller.text.trim().isNotEmpty;
                return Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: hasKey
                        ? const Color(0xFF10B981).withValues(alpha: 0.12)
                        : subColor.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    hasKey ? '✓ Set' : 'Not set',
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                      color: hasKey ? const Color(0xFF10B981) : subColor,
                    ),
                  ),
                );
              }),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: controller,
            obscureText: !visible,
            style: GoogleFonts.firaCode(fontSize: 13, color: textColor),
            decoration: InputDecoration(
              hintText: 'Paste your $provider API key here',
              hintStyle:
                  GoogleFonts.inter(fontSize: 13, color: subColor),
              suffixIcon: IconButton(
                icon: Icon(
                  visible ? Icons.visibility_off_rounded : Icons.visibility_rounded,
                  color: subColor,
                  size: 20,
                ),
                onPressed: onToggleVisibility,
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: BorderSide(color: borderColor),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: BorderSide(color: borderColor),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: BorderSide(color: color, width: 2),
              ),
              filled: true,
              fillColor: isDark ? AppTheme.bgDark : AppTheme.bgLight,
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  final bool isDark;

  const _SectionHeader({required this.title, required this.isDark});

  @override
  Widget build(BuildContext context) {
    return Text(
      title.toUpperCase(),
      style: GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w700,
        color: isDark
            ? AppTheme.textSecondaryDark
            : AppTheme.textSecondaryLight,
        letterSpacing: 1.0,
      ),
    );
  }
}

class _AboutItem extends StatelessWidget {
  final String label;
  final String value;
  final bool isDark;

  const _AboutItem(
      {required this.label, required this.value, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final textColor =
        isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor =
        isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: GoogleFonts.inter(
                  fontSize: 13, color: subColor, fontWeight: FontWeight.w500),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: GoogleFonts.inter(fontSize: 13, color: textColor),
            ),
          ),
        ],
      ),
    );
  }
}
