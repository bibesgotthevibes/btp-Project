import 'package:flutter/material.dart';

enum MedicalArtifactType {
  summary,
  medications,
  warnings,
  original,
  custom,
}

/// Represents a pinned document or clinical data artifact in the Claude-style Artifact panel
class MedicalArtifact {
  final String id;
  final String title; // e.g. "SIMPLIFIED_SUMMARY.MD", "MEDICINE_SCHEDULE.MD"
  final String displayName; // e.g. "Simplified Discharge Summary"
  final String subtitle;
  final MedicalArtifactType type;
  final String content; // Markdown content
  final IconData icon;
  final Color accentColor;
  final DateTime createdAt;
  final Map<String, dynamic>? metadata;

  const MedicalArtifact({
    required this.id,
    required this.title,
    required this.displayName,
    required this.subtitle,
    required this.type,
    required this.content,
    required this.icon,
    required this.accentColor,
    required this.createdAt,
    this.metadata,
  });

  /// Human-friendly file badge
  String get fileExtension {
    switch (type) {
      case MedicalArtifactType.summary:
        return 'SUMMARY.MD';
      case MedicalArtifactType.medications:
        return 'MEDS.TABLE';
      case MedicalArtifactType.warnings:
        return 'WARNINGS.ALERT';
      case MedicalArtifactType.original:
        return 'RECORD.TXT';
      case MedicalArtifactType.custom:
        return 'CAREPLAN.MD';
    }
  }

  /// Line count for Claude-style editor header
  int get lineCount => content.split('\n').length;
  
  /// Word count
  int get wordCount => content
      .trim()
      .split(RegExp(r'\s+'))
      .where((w) => w.isNotEmpty)
      .length;
}
