import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/discharge_knowledge.dart';

/// Calls Groq GPT-OSS 20B to extract structured medical knowledge
/// from a raw discharge summary text.
class ExtractionService {
  static const _endpoint =
      'https://api.groq.com/openai/v1/chat/completions';
  static const _model = 'openai/gpt-oss-20b';

  final String groqApiKey;
  ExtractionService(this.groqApiKey);

  static const _systemPrompt = r'''
You are a medical information extractor. Extract structured information from hospital discharge summaries into a strict JSON format.

RULES:
1. Output ONLY valid JSON. No markdown, no explanation, no code fences.
2. Use simple, clear English explanations (6th-grade level) in all *_lay_explanation fields.
3. Severity must be exactly one of: "normal", "borderline", "abnormal", "critical"
4. If information is missing, use null for strings/numbers, [] for arrays.
5. Follow the schema EXACTLY.

OUTPUT SCHEMA:
{
  "patient_demographics": {
    "gender": "male" | "female" | null,
    "age": <number> | null
  },
  "diagnoses": {
    "primary": "<main diagnosis>",
    "primary_lay_explanation": "<simple explanation>",
    "secondary": ["<condition>", ...],
    "icd_codes_mentioned": []
  },
  "symptoms_at_admission": ["<symptom>", ...],
  "anomalies_detected": [
    {
      "type": "Vital Sign" | "Lab Result" | "Imaging Finding" | "Clinical Finding",
      "finding": "<what was found>",
      "lay_explanation": "<simple explanation>",
      "severity": "normal" | "borderline" | "abnormal" | "critical"
    }
  ],
  "procedures_performed": [
    {
      "name": "<procedure name>",
      "lay_explanation": "<simple explanation>",
      "date": "<date string>" | null
    }
  ],
  "medications": [
    {
      "name": "<medicine name>",
      "purpose_lay": "<what it does in simple words>",
      "timing_dosage": "<when and how much>"
    }
  ],
  "warning_signs_red_flags": ["<warning sign>", ...],
  "follow_up_care": {
    "appointments": ["<appointment details>", ...],
    "ongoing_treatments": ["<treatment>", ...],
    "lifestyle_diet_advice": ["<advice>", ...]
  },
  "stay_duration": "<duration string>" | null,
  "outcome": "alive" | "death" | null
}

EXAMPLE INPUT:
"Male, 58 years old. Admitted for chest pain radiating to left arm. ECG showed ST elevation. Troponin elevated at 2.4. Diagnosed with STEMI (heart attack). Given aspirin 300mg, clopidogrel, atorvastatin. Underwent primary PCI (balloon procedure to open blocked artery). Discharged after 5 days. Follow-up with cardiologist in 2 weeks. Warning: call emergency if chest pain returns."

EXAMPLE OUTPUT:
{"patient_demographics":{"gender":"male","age":58},"diagnoses":{"primary":"ST-elevation myocardial infarction (STEMI — heart attack)","primary_lay_explanation":"A serious heart attack where the main heart artery was blocked, cutting off blood supply to part of the heart muscle.","secondary":[],"icd_codes_mentioned":[]},"symptoms_at_admission":["Chest pain radiating to left arm"],"anomalies_detected":[{"type":"Lab Result","finding":"Elevated Troponin at 2.4","lay_explanation":"Troponin is a protein released when heart muscle is damaged. A high level confirms a heart attack.","severity":"critical"},{"type":"Vital Sign","finding":"ST elevation on ECG","lay_explanation":"The heart's electrical tracing showed a pattern that means a major heart artery is blocked.","severity":"critical"}],"procedures_performed":[{"name":"Primary PCI (Percutaneous Coronary Intervention)","lay_explanation":"A procedure where doctors insert a thin tube into the blocked heart artery and inflate a small balloon to open it up, then place a stent to keep it open.","date":null}],"medications":[{"name":"Aspirin","purpose_lay":"Blood thinner to prevent new clots from forming in the heart arteries.","timing_dosage":"300mg initial dose, then daily as prescribed"},{"name":"Clopidogrel","purpose_lay":"Another blood thinner to work alongside aspirin to prevent clots.","timing_dosage":"As prescribed"},{"name":"Atorvastatin","purpose_lay":"Cholesterol-lowering medicine to prevent future blockages in heart arteries.","timing_dosage":"As prescribed"}],"warning_signs_red_flags":["Return of chest pain or pressure — call emergency immediately","Shortness of breath or sudden difficulty breathing","Sweating, nausea, or feeling faint","Swelling in legs or sudden weight gain"],"follow_up_care":{"appointments":["Cardiologist follow-up in 2 weeks"],"ongoing_treatments":["Continue aspirin, clopidogrel, and atorvastatin as prescribed"],"lifestyle_diet_advice":["Low-fat, low-salt diet","Avoid strenuous physical activity until cleared by cardiologist","No smoking"]},"stay_duration":"5 days","outcome":"alive"}
''';

  /// Extract structured medical knowledge from raw discharge summary text.
  /// Reports progress via [onStep] callback.
  Future<DischargeKnowledge> extract(
    String summaryText, {
    void Function(String step, bool done)? onStep,
  }) async {
    if (groqApiKey.isEmpty) {
      throw Exception(
          'Groq API key is not set. Please add it in Settings.');
    }

    onStep?.call('Reading discharge summary', false);
    await Future.delayed(const Duration(milliseconds: 400));
    onStep?.call('Reading discharge summary', true);

    onStep?.call('Extracting clinical facts with AI', false);

    final response = await http.post(
      Uri.parse(_endpoint),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $groqApiKey',
      },
      body: jsonEncode({
        'model': _model,
        'messages': [
          {'role': 'system', 'content': _systemPrompt},
          {
            'role': 'user',
            'content':
                'Extract structured medical information from this discharge summary:\n\n$summaryText',
          },
        ],
        'temperature': 0.1,
        'max_tokens': 4096,
      }),
    );

    if (response.statusCode != 200) {
      final body = jsonDecode(response.body);
      final msg = body['error']?['message'] ?? response.body;
      throw Exception('Extraction API error ${response.statusCode}: $msg');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final rawText =
        data['choices'][0]['message']['content'] as String? ?? '';

    onStep?.call('Extracting clinical facts with AI', true);
    onStep?.call('Building your knowledge base', false);

    final parsed = _parseJson(rawText);
    if (parsed == null) {
      throw Exception(
          'Could not parse structured data from LLM response. Please try again.');
    }

    final knowledge = DischargeKnowledge.fromJson(parsed);

    await Future.delayed(const Duration(milliseconds: 300));
    onStep?.call('Building your knowledge base', true);

    return knowledge;
  }

  /// Parse JSON from LLM response, stripping <think> blocks and code fences.
  Map<String, dynamic>? _parseJson(String raw) {
    // Strip <think>...</think> reasoning blocks
    var cleaned =
        raw.replaceAll(RegExp(r'<think>[\s\S]*?</think>'), '').trim();
    // Strip unclosed think blocks
    cleaned =
        cleaned.replaceAll(RegExp(r'^<think>[\s\S]*'), '').trim();

    // Try direct parse on cleaned text
    try {
      return jsonDecode(cleaned) as Map<String, dynamic>;
    } catch (_) {}

    // Try extracting from markdown code fences
    final patterns = [
      RegExp(r'```json\s*\n([\s\S]*?)\n\s*```'),
      RegExp(r'```\s*\n([\s\S]*?)\n\s*```'),
      RegExp(r'(\{[\s\S]*\})'),
    ];

    for (final pattern in patterns) {
      final match = pattern.firstMatch(cleaned);
      if (match != null) {
        try {
          final candidate =
              match.groupCount >= 1 ? match.group(1)! : match.group(0)!;
          return jsonDecode(candidate) as Map<String, dynamic>;
        } catch (_) {}
      }
    }

    // Last resort: try on original raw
    for (final pattern in patterns) {
      final match = pattern.firstMatch(raw);
      if (match != null) {
        try {
          final candidate =
              match.groupCount >= 1 ? match.group(1)! : match.group(0)!;
          return jsonDecode(candidate) as Map<String, dynamic>;
        } catch (_) {}
      }
    }

    return null;
  }
}
