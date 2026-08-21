import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:google_fonts/google_fonts.dart';
import '../models/discharge_knowledge.dart';
import '../theme/app_theme.dart';

/// A single flash card in the horizontal knowledge carousel.
class KnowledgeFlashCard extends StatelessWidget {
  final _CardType type;
  final DischargeKnowledge knowledge;

  const KnowledgeFlashCard._({
    required this.type,
    required this.knowledge,
  });

  static KnowledgeFlashCard diagnosis(DischargeKnowledge k) =>
      KnowledgeFlashCard._(type: _CardType.diagnosis, knowledge: k);

  static KnowledgeFlashCard anomalies(DischargeKnowledge k) =>
      KnowledgeFlashCard._(type: _CardType.anomalies, knowledge: k);

  static KnowledgeFlashCard medications(DischargeKnowledge k) =>
      KnowledgeFlashCard._(type: _CardType.medications, knowledge: k);

  static KnowledgeFlashCard appointments(DischargeKnowledge k) =>
      KnowledgeFlashCard._(type: _CardType.appointments, knowledge: k);

  static KnowledgeFlashCard warnings(DischargeKnowledge k) =>
      KnowledgeFlashCard._(type: _CardType.warnings, knowledge: k);

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    switch (type) {
      case _CardType.diagnosis:
        return _DiagnosisCard(knowledge: knowledge, isDark: isDark);
      case _CardType.anomalies:
        return _AnomaliesCard(knowledge: knowledge, isDark: isDark);
      case _CardType.medications:
        return _MedicationsCard(knowledge: knowledge, isDark: isDark);
      case _CardType.appointments:
        return _AppointmentsCard(knowledge: knowledge, isDark: isDark);
      case _CardType.warnings:
        return _WarningsCard(knowledge: knowledge, isDark: isDark);
    }
  }
}

enum _CardType { diagnosis, anomalies, medications, appointments, warnings }

// ── Shared card scaffold ─────────────────────────────────────────────────────
class _CardScaffold extends StatelessWidget {
  final List<Color> gradientColors;
  final IconData icon;
  final String title;
  final String subtitle;
  final Widget body;
  final bool isDark;

  const _CardScaffold({
    required this.gradientColors,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.body,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    final cardBg = isDark ? const Color(0xFF1C2333) : Colors.white;
    final borderColor = gradientColors.first.withValues(alpha: 0.25);

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: borderColor, width: 1.5),
        boxShadow: [
          BoxShadow(
            color: gradientColors.first.withValues(alpha: isDark ? 0.15 : 0.08),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // ── Card Header ──────────────────────────────────────────────────
          Container(
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 14),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: gradientColors.map((c) => c.withValues(alpha: isDark ? 0.25 : 0.12)).toList(),
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: gradientColors,
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, color: Colors.white, size: 18),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                          color: gradientColors.first,
                        ),
                      ),
                      Text(
                        subtitle,
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          color: gradientColors.first.withValues(alpha: 0.7),
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          // ── Card Body ────────────────────────────────────────────────────
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 18),
              child: body,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Diagnosis Card ───────────────────────────────────────────────────────────
class _DiagnosisCard extends StatelessWidget {
  final DischargeKnowledge knowledge;
  final bool isDark;
  const _DiagnosisCard({required this.knowledge, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final textColor = isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor = isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;

    return _CardScaffold(
      gradientColors: const [Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
      icon: Icons.local_hospital_rounded,
      title: 'Diagnosis',
      subtitle: 'What you were treated for',
      isDark: isDark,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Primary diagnosis
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFF6C4DF6).withValues(alpha: isDark ? 0.15 : 0.07),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                  color: const Color(0xFF6C4DF6).withValues(alpha: 0.2)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Primary Diagnosis',
                  style: GoogleFonts.inter(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: const Color(0xFF6C4DF6),
                    letterSpacing: 0.8,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  knowledge.primaryDiagnosis,
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: textColor,
                  ),
                ),
                if (knowledge.primaryLayExplanation.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    knowledge.primaryLayExplanation,
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: subColor,
                      height: 1.5,
                    ),
                  ),
                ],
              ],
            ),
          ),

          if (knowledge.secondaryDiagnoses.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              'Secondary Conditions',
              style: GoogleFonts.inter(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: subColor,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: 8),
            ...knowledge.secondaryDiagnoses.map((d) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.only(top: 5),
                    child: CircleAvatar(
                      radius: 3,
                      backgroundColor: Color(0xFF6C4DF6),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      d,
                      style: GoogleFonts.inter(
                          fontSize: 12, color: textColor, height: 1.4),
                    ),
                  ),
                ],
              ),
            )),
          ],

          if (knowledge.demographics.age != null ||
              knowledge.demographics.gender != null) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              children: [
                if (knowledge.demographics.gender != null)
                  _InfoChip(
                    label: knowledge.demographics.gender!,
                    icon: knowledge.demographics.gender == 'male'
                        ? Icons.male_rounded
                        : Icons.female_rounded,
                    color: const Color(0xFF6C4DF6),
                  ),
                if (knowledge.demographics.age != null)
                  _InfoChip(
                    label: '${knowledge.demographics.age} years',
                    icon: Icons.person_outline_rounded,
                    color: const Color(0xFF6C4DF6),
                  ),
                if (knowledge.outcome != null)
                  _InfoChip(
                    label: knowledge.outcome!,
                    icon: knowledge.outcome == 'alive'
                        ? Icons.favorite_rounded
                        : Icons.do_not_disturb_rounded,
                    color: knowledge.outcome == 'alive'
                        ? AppTheme.success
                        : AppTheme.error,
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

// ── Anomalies Card ───────────────────────────────────────────────────────────
class _AnomaliesCard extends StatelessWidget {
  final DischargeKnowledge knowledge;
  final bool isDark;
  const _AnomaliesCard({required this.knowledge, required this.isDark});

  Color _severityColor(String severity) {
    switch (severity) {
      case 'critical':
        return AppTheme.error;
      case 'abnormal':
        return AppTheme.warning;
      case 'borderline':
        return const Color(0xFF3B82F6);
      default:
        return AppTheme.success;
    }
  }

  IconData _severityIcon(String severity) {
    switch (severity) {
      case 'critical':
        return Icons.dangerous_rounded;
      case 'abnormal':
        return Icons.warning_amber_rounded;
      case 'borderline':
        return Icons.info_outline_rounded;
      default:
        return Icons.check_circle_outline_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    final textColor = isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor = isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;
    final anomalies = knowledge.anomalies;

    return _CardScaffold(
      gradientColors: const [Color(0xFFF59E0B), Color(0xFFEF4444)],
      icon: Icons.monitor_heart_rounded,
      title: 'Anomalies Detected',
      subtitle: '${anomalies.length} findings from your tests',
      isDark: isDark,
      body: anomalies.isEmpty
          ? Center(
              child: Text('No anomalies recorded.',
                  style: GoogleFonts.inter(fontSize: 13, color: subColor)))
          : Column(
              children: anomalies.map((a) {
                final color = _severityColor(a.severity);
                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: isDark ? 0.12 : 0.06),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: color.withValues(alpha: 0.25)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(_severityIcon(a.severity), color: color, size: 16),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    a.finding,
                                    style: GoogleFonts.inter(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                      color: textColor,
                                    ),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: color.withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    a.severity,
                                    style: GoogleFonts.inter(
                                      fontSize: 9,
                                      fontWeight: FontWeight.w700,
                                      color: color,
                                      letterSpacing: 0.5,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            if (a.layExplanation.isNotEmpty) ...[
                              const SizedBox(height: 3),
                              Text(
                                a.layExplanation,
                                style: GoogleFonts.inter(
                                  fontSize: 11,
                                  color: subColor,
                                  height: 1.4,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
    );
  }
}

// ── Medications Card ─────────────────────────────────────────────────────────
class _MedicationsCard extends StatelessWidget {
  final DischargeKnowledge knowledge;
  final bool isDark;
  const _MedicationsCard({required this.knowledge, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final textColor = isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor = isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;
    final meds = knowledge.medications;

    return _CardScaffold(
      gradientColors: const [Color(0xFF10B981), Color(0xFF34D399)],
      icon: Icons.medication_rounded,
      title: 'Medications',
      subtitle: '${meds.length} medicines prescribed',
      isDark: isDark,
      body: meds.isEmpty
          ? Center(
              child: Text('No medications listed.',
                  style: GoogleFonts.inter(fontSize: 13, color: subColor)))
          : Column(
              children: meds.asMap().entries.map((entry) {
                final i = entry.key;
                final m = entry.value;
                return Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF10B981).withValues(alpha: isDark ? 0.12 : 0.06),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                        color: const Color(0xFF10B981).withValues(alpha: 0.2)),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 24,
                        height: 24,
                        decoration: BoxDecoration(
                          color: const Color(0xFF10B981),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Center(
                          child: Text(
                            '${i + 1}',
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              m.name,
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: textColor,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              m.purposeLay,
                              style: GoogleFonts.inter(
                                fontSize: 11,
                                color: subColor,
                                height: 1.4,
                              ),
                            ),
                            if (m.timingDosage.isNotEmpty) ...[
                              const SizedBox(height: 4),
                              Row(
                                children: [
                                  const Icon(Icons.schedule_rounded,
                                      size: 12,
                                      color: Color(0xFF10B981)),
                                  const SizedBox(width: 4),
                                  Expanded(
                                    child: Text(
                                      m.timingDosage,
                                      style: GoogleFonts.inter(
                                        fontSize: 11,
                                        color: const Color(0xFF10B981),
                                        fontWeight: FontWeight.w500,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
    );
  }
}

// ── Appointments Card ────────────────────────────────────────────────────────
class _AppointmentsCard extends StatelessWidget {
  final DischargeKnowledge knowledge;
  final bool isDark;
  const _AppointmentsCard({required this.knowledge, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final textColor = isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor = isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;
    final followUp = knowledge.followUpCare;
    final allItems = [
      ...followUp.appointments.map((a) => _FollowUpItem(text: a, isAppointment: true)),
      ...followUp.ongoingTreatments.map((t) => _FollowUpItem(text: t, isAppointment: false)),
    ];

    return _CardScaffold(
      gradientColors: const [Color(0xFF3B82F6), Color(0xFF60A5FA)],
      icon: Icons.calendar_month_rounded,
      title: 'Follow-up Care',
      subtitle: '${followUp.appointments.length} appointments',
      isDark: isDark,
      body: allItems.isEmpty
          ? Center(
              child: Text('No follow-up appointments listed.',
                  style: GoogleFonts.inter(fontSize: 13, color: subColor)))
          : Column(
              children: [
                if (followUp.appointments.isNotEmpty) ...[
                  _SectionHeader(label: 'APPOINTMENTS', color: const Color(0xFF3B82F6)),
                  const SizedBox(height: 6),
                  ...followUp.appointments.map((apt) => _FollowUpRow(
                    text: apt,
                    icon: Icons.event_rounded,
                    color: const Color(0xFF3B82F6),
                    isDark: isDark,
                    textColor: textColor,
                  )),
                ],
                if (followUp.ongoingTreatments.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _SectionHeader(label: 'ONGOING TREATMENTS', color: const Color(0xFF3B82F6)),
                  const SizedBox(height: 6),
                  ...followUp.ongoingTreatments.map((t) => _FollowUpRow(
                    text: t,
                    icon: Icons.loop_rounded,
                    color: const Color(0xFF60A5FA),
                    isDark: isDark,
                    textColor: textColor,
                  )),
                ],
                if (followUp.lifestyleDietAdvice.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  _SectionHeader(label: 'LIFESTYLE ADVICE', color: const Color(0xFF3B82F6)),
                  const SizedBox(height: 6),
                  ...followUp.lifestyleDietAdvice.map((a) => _FollowUpRow(
                    text: a,
                    icon: Icons.spa_rounded,
                    color: AppTheme.success,
                    isDark: isDark,
                    textColor: textColor,
                  )),
                ],
              ],
            ),
    );
  }
}

// ── Warnings Card ────────────────────────────────────────────────────────────
class _WarningsCard extends StatelessWidget {
  final DischargeKnowledge knowledge;
  final bool isDark;
  const _WarningsCard({required this.knowledge, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final textColor = isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor = isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;
    final warnings = knowledge.warningSignals;

    return _CardScaffold(
      gradientColors: const [Color(0xFFEF4444), Color(0xFFFB7185)],
      icon: Icons.warning_amber_rounded,
      title: 'Warning Signs',
      subtitle: 'Go to emergency if you notice these',
      isDark: isDark,
      body: warnings.isEmpty
          ? Center(
              child: Text('No warning signs listed.',
                  style: GoogleFonts.inter(fontSize: 13, color: subColor)))
          : Column(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppTheme.error.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                        color: AppTheme.error.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.emergency_rounded,
                          color: AppTheme.error, size: 16),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Call emergency services immediately if you experience any of these:',
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.error,
                            height: 1.4,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                ...warnings.map((w) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Padding(
                        padding: EdgeInsets.only(top: 4),
                        child: Icon(Icons.circle, size: 6, color: AppTheme.error),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          w,
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            color: textColor,
                            height: 1.5,
                          ),
                        ),
                      ),
                    ],
                  ),
                )),
              ],
            ),
    );
  }
}

// ── Helper Widgets ───────────────────────────────────────────────────────────
class _InfoChip extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  const _InfoChip({required this.label, required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String label;
  final Color color;
  const _SectionHeader({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: GoogleFonts.inter(
        fontSize: 10,
        fontWeight: FontWeight.w700,
        color: color,
        letterSpacing: 0.8,
      ),
    );
  }
}

class _FollowUpRow extends StatelessWidget {
  final String text;
  final IconData icon;
  final Color color;
  final bool isDark;
  final Color textColor;
  const _FollowUpRow({
    required this.text,
    required this.icon,
    required this.color,
    required this.isDark,
    required this.textColor,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: GoogleFonts.inter(
                  fontSize: 12, color: textColor, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }
}

class _FollowUpItem {
  final String text;
  final bool isAppointment;
  const _FollowUpItem({required this.text, required this.isAppointment});
}
