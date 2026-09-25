import 'package:flutter/material.dart';
import '../models/medical_artifact.dart';

/// Service responsible for extracting and managing bounded clinical artifacts
/// based strictly on available information in the discharge summary.
class ArtifactService {
  /// Generates a bounded list of clinical artifacts.
  /// Guarantees:
  /// 1. PATIENT_SUMMARY.MD is ALWAYS created.
  /// 2. CLINICAL_RECORD.TXT is ALWAYS created.
  /// 3. MEDICINE_SCHEDULE.TABLE is ONLY created if medication details actually exist.
  /// 4. EMERGENCY_WARNINGS.ALERT is ONLY created if danger/red-flag signs actually exist.
  static List<MedicalArtifact> generateArtifacts({
    required String rawText,
    required String simplifiedText,
  }) {
    final artifacts = <MedicalArtifact>[];

    // 1. Simplified Summary — ALWAYS GENERATED
    artifacts.add(
      MedicalArtifact(
        id: 'art-summary',
        title: 'PATIENT_SUMMARY.MD',
        displayName: 'Simplified Discharge Summary',
        subtitle: 'Plain-language explanation & recovery guide',
        type: MedicalArtifactType.summary,
        content: simplifiedText,
        icon: Icons.description_rounded,
        accentColor: const Color(0xFF6C4DF6),
        createdAt: DateTime.now(),
      ),
    );

    // 2. Prescribed Medications — ONLY IF PRESENT
    final medsContent = detectMedicationsSection(rawText, simplifiedText);
    if (medsContent != null && medsContent.trim().isNotEmpty) {
      artifacts.add(
        MedicalArtifact(
          id: 'art-meds',
          title: 'MEDICINE_SCHEDULE.TABLE',
          displayName: 'Medication Schedule & Instructions',
          subtitle: 'Active prescriptions, dosages & timing',
          type: MedicalArtifactType.medications,
          content: medsContent,
          icon: Icons.medication_rounded,
          accentColor: const Color(0xFF10B981),
          createdAt: DateTime.now(),
        ),
      );
    }

    // 3. Emergency Warnings — ONLY IF PRESENT
    final warningsContent = detectWarningsSection(rawText, simplifiedText);
    if (warningsContent != null && warningsContent.trim().isNotEmpty) {
      artifacts.add(
        MedicalArtifact(
          id: 'art-warnings',
          title: 'EMERGENCY_WARNINGS.ALERT',
          displayName: 'Emergency Red Flags',
          subtitle: 'Critical symptoms requiring urgent care',
          type: MedicalArtifactType.warnings,
          content: warningsContent,
          icon: Icons.warning_amber_rounded,
          accentColor: const Color(0xFFEF4444),
          createdAt: DateTime.now(),
        ),
      );
    }

    // 4. Original Clinical Record — ALWAYS GENERATED
    artifacts.add(
      MedicalArtifact(
        id: 'art-record',
        title: 'CLINICAL_RECORD.TXT',
        displayName: 'Original Hospital Record',
        subtitle: 'Raw discharge summary text from hospital',
        type: MedicalArtifactType.original,
        content: rawText,
        icon: Icons.receipt_long_rounded,
        accentColor: const Color(0xFF64748B),
        createdAt: DateTime.now(),
      ),
    );

    return artifacts;
  }

  /// Detects if the document contains genuine medication details
  static String? detectMedicationsSection(String rawText, String simplifiedText) {
    final textToSearch = '$rawText\n\n$simplifiedText';
    final lower = textToSearch.toLowerCase();

    // Check if explicitly none/nil
    final isExplicitlyNone = lower.contains('no medications') ||
        lower.contains('medications: nil') ||
        lower.contains('medications: none') ||
        lower.contains('medicines: nil') ||
        lower.contains('medicines: none') ||
        lower.contains('no discharge medicines') ||
        lower.contains('no active medicines') ||
        lower.contains('no home medicines');

    // Check for dosage / prescription keywords (e.g. 50mg, tab, injection, etc.)
    final hasDoseKeywords = RegExp(
      r'(\d+\s*(mg|mcg|ml|iu|units|g|gm)\b)|(\b(tab|tablet|capsule|inj|injection|syrup|nebulization)\b)|(once daily|twice daily|thrice daily|\b[1-3]\s*times\s*a\s*day|\bod\b|\bbd\b|\btds\b|\bqid\b)',
      caseSensitive: false,
    ).hasMatch(textToSearch);

    final hasMedHeader = lower.contains('medication') ||
        lower.contains('medicine') ||
        lower.contains('prescribed') ||
        lower.contains('discharge drug') ||
        lower.contains('rx:');

    if (!hasMedHeader && !hasDoseKeywords) return null;
    if (isExplicitlyNone && !hasDoseKeywords) return null;

    // Try extracting section from simplifiedText first
    final fromSimplified = extractSection(
      simplifiedText,
      ['Prescribed Medicines', 'Your Medicines', 'Medications', 'Medicines', 'Prescriptions'],
    );
    if (fromSimplified.isNotEmpty && fromSimplified.length > 20) {
      return fromSimplified;
    }

    // Try extracting section from rawText
    final fromRaw = extractSection(
      rawText,
      ['Medications', 'Medicines', 'Prescription', 'Discharge Medications', 'Rx', 'Treatment at Discharge'],
    );
    if (fromRaw.isNotEmpty && fromRaw.length > 20) {
      return fromRaw;
    }

    // Extract individual medication lines if dose patterns matched
    final medLines = rawText
        .split('\n')
        .where((l) => RegExp(r'(\d+\s*(mg|mcg|ml|iu))|(\b(tab|tablet|inj|capsule)\b)', caseSensitive: false).hasMatch(l))
        .join('\n');
    if (medLines.trim().isNotEmpty) {
      return '### Prescribed Medications\n\n$medLines';
    }

    return null;
  }

  /// Detects if the document contains genuine warning signs / red flags
  static String? detectWarningsSection(String rawText, String simplifiedText) {
    final textToSearch = '$rawText\n\n$simplifiedText';
    final lower = textToSearch.toLowerCase();

    final hasWarningKeywords = lower.contains('warning sign') ||
        lower.contains('red flag') ||
        lower.contains('danger sign') ||
        lower.contains('emergency') ||
        lower.contains('seek immediate medical') ||
        lower.contains('rush to hospital') ||
        lower.contains('contact emergency') ||
        lower.contains('call 108') ||
        lower.contains('call 911');

    if (!hasWarningKeywords) return null;

    final fromSimplified = extractSection(
      simplifiedText,
      ['Warning Signs', 'Red Flags', 'Emergency', 'Danger Signs', 'When to Seek Immediate Care'],
    );
    if (fromSimplified.isNotEmpty && fromSimplified.length > 20) {
      return fromSimplified;
    }

    final fromRaw = extractSection(
      rawText,
      ['Warning Signs', 'Red Flags', 'Emergency Warnings', 'Precautions & Red Flags', 'Danger Signs'],
    );
    if (fromRaw.isNotEmpty && fromRaw.length > 20) {
      return fromRaw;
    }

    return null;
  }

  /// Extracts a section matching any of the specified keywords
  static String extractSection(String fullText, List<String> keywords) {
    final lines = fullText.split('\n');
    final buffer = StringBuffer();
    bool capturing = false;

    for (int i = 0; i < lines.length; i++) {
      final line = lines[i];
      final isHeader = line.startsWith('#') ||
          (line.startsWith('**') && line.endsWith('**')) ||
          (line.toUpperCase() == line && line.trim().isNotEmpty && line.length < 40);

      if (isHeader) {
        final matches = keywords.any((k) =>
            line.toLowerCase().contains(k.toLowerCase()));
        if (matches) {
          capturing = true;
          buffer.writeln(line);
          continue;
        } else if (capturing) {
          // Reached next section
          break;
        }
      } else if (capturing) {
        buffer.writeln(line);
      }
    }

    final result = buffer.toString().trim();
    if (result.isNotEmpty) return result;

    // Fallback: search for keyword paragraphs
    for (final kw in keywords) {
      final idx = fullText.toLowerCase().indexOf(kw.toLowerCase());
      if (idx != -1) {
        final snippet = fullText.substring(idx);
        final endIdx = snippet.indexOf('\n\n\n');
        return endIdx != -1 ? snippet.substring(0, endIdx).trim() : snippet.trim();
      }
    }
    return '';
  }
}
