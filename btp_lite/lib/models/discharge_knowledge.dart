import 'dart:convert';

/// Structured medical knowledge extracted from a discharge summary.
class DischargeKnowledge {
  final PatientDemographics demographics;
  final String primaryDiagnosis;
  final String primaryLayExplanation;
  final List<String> secondaryDiagnoses;
  final List<String> symptomsAtAdmission;
  final List<Anomaly> anomalies;
  final List<MedicalProcedure> procedures;
  final List<Medication> medications;
  final List<String> warningSignals;
  final FollowUpCare followUpCare;
  final String? stayDuration;
  final String? outcome;

  const DischargeKnowledge({
    required this.demographics,
    required this.primaryDiagnosis,
    required this.primaryLayExplanation,
    required this.secondaryDiagnoses,
    required this.symptomsAtAdmission,
    required this.anomalies,
    required this.procedures,
    required this.medications,
    required this.warningSignals,
    required this.followUpCare,
    this.stayDuration,
    this.outcome,
  });

  bool get hasCriticalAnomalies =>
      anomalies.any((a) => a.severity == 'critical');

  bool get hasAppointments => followUpCare.appointments.isNotEmpty;

  factory DischargeKnowledge.fromJson(Map<String, dynamic> json) {
    final demos = json['patient_demographics'] as Map<String, dynamic>? ?? {};
    final diagnoses = json['diagnoses'] as Map<String, dynamic>? ?? {};
    final followUp = json['follow_up_care'] as Map<String, dynamic>? ?? {};

    return DischargeKnowledge(
      demographics: PatientDemographics(
        gender: demos['gender'] as String?,
        age: demos['age'] as int?,
      ),
      primaryDiagnosis: diagnoses['primary'] as String? ?? 'Not specified',
      primaryLayExplanation:
          diagnoses['primary_lay_explanation'] as String? ?? '',
      secondaryDiagnoses: List<String>.from(
          diagnoses['secondary'] as List? ?? []),
      symptomsAtAdmission: List<String>.from(
          json['symptoms_at_admission'] as List? ?? []),
      anomalies: (json['anomalies_detected'] as List? ?? [])
          .map((e) => Anomaly.fromJson(e as Map<String, dynamic>))
          .toList(),
      procedures: (json['procedures_performed'] as List? ?? [])
          .map((e) => MedicalProcedure.fromJson(e as Map<String, dynamic>))
          .toList(),
      medications: (json['medications'] as List? ?? [])
          .map((e) => Medication.fromJson(e as Map<String, dynamic>))
          .toList(),
      warningSignals: List<String>.from(
          json['warning_signs_red_flags'] as List? ?? []),
      followUpCare: FollowUpCare(
        appointments: List<String>.from(
            followUp['appointments'] as List? ?? []),
        ongoingTreatments: List<String>.from(
            followUp['ongoing_treatments'] as List? ?? []),
        lifestyleDietAdvice: List<String>.from(
            followUp['lifestyle_diet_advice'] as List? ?? []),
      ),
      stayDuration: json['stay_duration'] as String?,
      outcome: json['outcome'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'patient_demographics': {
          'gender': demographics.gender,
          'age': demographics.age,
        },
        'diagnoses': {
          'primary': primaryDiagnosis,
          'primary_lay_explanation': primaryLayExplanation,
          'secondary': secondaryDiagnoses,
          'icd_codes_mentioned': [],
        },
        'symptoms_at_admission': symptomsAtAdmission,
        'anomalies_detected':
            anomalies.map((a) => a.toJson()).toList(),
        'procedures_performed':
            procedures.map((p) => p.toJson()).toList(),
        'medications': medications.map((m) => m.toJson()).toList(),
        'warning_signs_red_flags': warningSignals,
        'follow_up_care': {
          'appointments': followUpCare.appointments,
          'ongoing_treatments': followUpCare.ongoingTreatments,
          'lifestyle_diet_advice': followUpCare.lifestyleDietAdvice,
        },
        'stay_duration': stayDuration,
        'outcome': outcome,
      };

  /// Serialise to JSON string for storage
  String toJsonString() => jsonEncode(toJson());

  factory DischargeKnowledge.fromJsonString(String s) =>
      DischargeKnowledge.fromJson(
          jsonDecode(s) as Map<String, dynamic>);

  /// Build a compact grounded system prompt section for the chatbot
  String toSystemPromptContext() {
    final buffer = StringBuffer();
    buffer.writeln('=== VERIFIED PATIENT CLINICAL FACTS ===');
    buffer.writeln('Primary Diagnosis: $primaryDiagnosis');
    if (primaryLayExplanation.isNotEmpty) {
      buffer.writeln('  (Lay meaning: $primaryLayExplanation)');
    }
    if (secondaryDiagnoses.isNotEmpty) {
      buffer.writeln('Secondary Conditions:');
      for (final d in secondaryDiagnoses) {
        buffer.writeln('  • $d');
      }
    }
    if (symptomsAtAdmission.isNotEmpty) {
      buffer.writeln('Symptoms at Admission:');
      for (final s in symptomsAtAdmission) {
        buffer.writeln('  • $s');
      }
    }
    if (anomalies.isNotEmpty) {
      buffer.writeln('Detected Anomalies:');
      for (final a in anomalies) {
        buffer.writeln(
            '  • [${a.severity.toUpperCase()}] ${a.finding}: ${a.layExplanation}');
      }
    }
    if (medications.isNotEmpty) {
      buffer.writeln('Medications:');
      for (final m in medications) {
        buffer.writeln(
            '  • ${m.name}: ${m.purposeLay} — Timing: ${m.timingDosage}');
      }
    }
    if (warningSignals.isNotEmpty) {
      buffer.writeln('EMERGENCY WARNING SIGNS:');
      for (final w in warningSignals) {
        buffer.writeln('  ⚠ $w');
      }
    }
    if (followUpCare.appointments.isNotEmpty) {
      buffer.writeln('Follow-up Appointments:');
      for (final apt in followUpCare.appointments) {
        buffer.writeln('  • $apt');
      }
    }
    if (outcome != null) {
      buffer.writeln('Patient Outcome: $outcome');
    }
    return buffer.toString();
  }
}

class PatientDemographics {
  final String? gender;
  final int? age;
  const PatientDemographics({this.gender, this.age});
}

class Anomaly {
  final String type;
  final String finding;
  final String layExplanation;
  final String severity; // 'normal' | 'borderline' | 'abnormal' | 'critical'

  const Anomaly({
    required this.type,
    required this.finding,
    required this.layExplanation,
    required this.severity,
  });

  factory Anomaly.fromJson(Map<String, dynamic> json) => Anomaly(
        type: json['type'] as String? ?? '',
        finding: json['finding'] as String? ?? '',
        layExplanation: json['lay_explanation'] as String? ?? '',
        severity: json['severity'] as String? ?? 'normal',
      );

  Map<String, dynamic> toJson() => {
        'type': type,
        'finding': finding,
        'lay_explanation': layExplanation,
        'severity': severity,
      };
}

class Medication {
  final String name;
  final String purposeLay;
  final String timingDosage;

  const Medication({
    required this.name,
    required this.purposeLay,
    required this.timingDosage,
  });

  factory Medication.fromJson(Map<String, dynamic> json) => Medication(
        name: json['name'] as String? ?? '',
        purposeLay: json['purpose_lay'] as String? ?? '',
        timingDosage: json['timing_dosage'] as String? ?? '',
      );

  Map<String, dynamic> toJson() => {
        'name': name,
        'purpose_lay': purposeLay,
        'timing_dosage': timingDosage,
      };
}

class MedicalProcedure {
  final String name;
  final String layExplanation;
  final String? date;

  const MedicalProcedure({
    required this.name,
    required this.layExplanation,
    this.date,
  });

  factory MedicalProcedure.fromJson(Map<String, dynamic> json) =>
      MedicalProcedure(
        name: json['name'] as String? ?? '',
        layExplanation: json['lay_explanation'] as String? ?? '',
        date: json['date'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'name': name,
        'lay_explanation': layExplanation,
        'date': date,
      };
}

class FollowUpCare {
  final List<String> appointments;
  final List<String> ongoingTreatments;
  final List<String> lifestyleDietAdvice;

  const FollowUpCare({
    required this.appointments,
    required this.ongoingTreatments,
    required this.lifestyleDietAdvice,
  });
}
