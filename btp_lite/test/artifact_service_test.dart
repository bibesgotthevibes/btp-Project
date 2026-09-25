import 'package:flutter_test/flutter_test.dart';
import 'package:btp_lite/models/medical_artifact.dart';
import 'package:btp_lite/services/artifact_service.dart';

void main() {
  group('ArtifactService Gated Generation Tests', () {
    test(
        'Case 1: No medications and no red flags -> Generates ONLY 2 mandatory artifacts',
        () {
      const rawText =
          'Patient 24M presented with acute mild viral pharyngitis. Throat examination showed mild erythema, no tonsillar exudate. Afebrile, vitals normal. Rapid strep test negative. Advised warm salt water gargles and adequate oral hydration. Discharged home in good condition.';
      const simplifiedText =
          'A 24-year-old man came in with a mild viral throat infection (pharyngitis). His throat was mildly red with no pus. He had no fever and normal vitals. Strep throat test was negative. He was advised warm salt water gargles and plenty of water, and was sent home in good condition.';

      final artifacts = ArtifactService.generateArtifacts(
        rawText: rawText,
        simplifiedText: simplifiedText,
      );

      // Verify only 2 artifacts
      expect(artifacts.length, equals(2));
      expect(artifacts[0].title, equals('PATIENT_SUMMARY.MD'));
      expect(artifacts[0].type, equals(MedicalArtifactType.summary));
      expect(artifacts[1].title, equals('CLINICAL_RECORD.TXT'));
      expect(artifacts[1].type, equals(MedicalArtifactType.original));

      // Verify NO meds or warnings
      expect(
          artifacts.any((a) => a.type == MedicalArtifactType.medications),
          isFalse);
      expect(
          artifacts.any((a) => a.type == MedicalArtifactType.warnings),
          isFalse);
    });

    test(
        'Case 2: Contains medications but NO red flags -> Generates 3 artifacts',
        () {
      const rawText = '''
Patient 65M admitted with uncomplicated hypertension. Blood pressure 160/95 mmHg.
Discharge Medications:
1. Tab Amlodipine 5mg once daily morning
2. Tab Telmisartan 40mg once daily morning
Follow-up in general clinic in 4 weeks.
''';
      const simplifiedText = '''
A 65-year-old man was admitted with high BP (hypertension). Blood pressure was 160/95 mmHg.
### Prescribed Medicines
• Amlodipine 5mg — blood pressure medicine taken once daily in the morning
• Telmisartan 40mg — blood pressure medicine taken once daily in the morning
Follow-up in general clinic in 4 weeks.
''';

      final artifacts = ArtifactService.generateArtifacts(
        rawText: rawText,
        simplifiedText: simplifiedText,
      );

      expect(artifacts.length, equals(3));
      expect(artifacts.map((a) => a.title).toList(),
          containsAll(['PATIENT_SUMMARY.MD', 'MEDICINE_SCHEDULE.TABLE', 'CLINICAL_RECORD.TXT']));
      expect(
          artifacts.any((a) => a.type == MedicalArtifactType.warnings),
          isFalse);
    });

    test(
        'Case 3: Contains BOTH medications and red flags -> Generates 4 artifacts',
        () {
      const rawText = '''
Patient 56M admitted with acute anterior STEMI, primary PCI to LAD.
Prescribed Medications:
1. Tab Aspirin 75mg OD
2. Tab Ticagrelor 90mg BD
3. Tab Atorvastatin 80mg OD
Emergency Warning Signs:
- Recurrent chest pain or pressure
- Difficulty breathing at rest
- Syncope or severe dizziness
Review in Cardiology OPD in 2 weeks.
''';
      const simplifiedText = '''
A 56-year-old man had a heart attack (acute anterior STEMI) and underwent stent placement.
### Prescribed Medicines
• Aspirin 75mg — blood thinner once daily
• Ticagrelor 90mg — blood thinner twice daily
• Atorvastatin 80mg — cholesterol medicine
### Emergency Warning Signs / Red Flags
• Recurrent chest pain
• Difficulty breathing at rest
• Fainting or dizziness
''';

      final artifacts = ArtifactService.generateArtifacts(
        rawText: rawText,
        simplifiedText: simplifiedText,
      );

      expect(artifacts.length, equals(4));
      expect(artifacts[0].title, equals('PATIENT_SUMMARY.MD'));
      expect(artifacts[1].title, equals('MEDICINE_SCHEDULE.TABLE'));
      expect(artifacts[2].title, equals('EMERGENCY_WARNINGS.ALERT'));
      expect(artifacts[3].title, equals('CLINICAL_RECORD.TXT'));
    });

    test(
        'Case 4: Explicit "Medications: Nil" -> Does NOT generate medicine schedule',
        () {
      const rawText = '''
Patient 30F admitted for observation after mild head trauma. CT brain normal.
Medications: Nil.
Emergency Red Flags: Return to ER immediately if persistent vomiting, severe headache, or confusion occurs.
''';
      const simplifiedText = '''
A 30-year-old woman was observed after a mild bump to the head. Brain CT scan was normal.
No medicines were prescribed.
### Emergency Warning Signs
Go to the emergency department immediately if you have repeated vomiting, severe headache, or confusion.
''';

      final artifacts = ArtifactService.generateArtifacts(
        rawText: rawText,
        simplifiedText: simplifiedText,
      );

      expect(artifacts.length, equals(3));
      expect(
          artifacts.any((a) => a.type == MedicalArtifactType.medications),
          isFalse);
      expect(
          artifacts.any((a) => a.type == MedicalArtifactType.warnings),
          isTrue);
      expect(
          artifacts.any((a) => a.type == MedicalArtifactType.summary),
          isTrue);
      expect(
          artifacts.any((a) => a.type == MedicalArtifactType.original),
          isTrue);
    });
  });
}
