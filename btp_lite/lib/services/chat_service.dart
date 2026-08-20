import 'dart:convert';
import '../models/api_model.dart';
import '../models/chat_message.dart';
import '../services/cerebras_service.dart';
import '../services/gemini_service.dart';
import '../services/groq_service.dart';
import '../services/storage_service.dart';

class ChatService {
  final StorageService storage;

  ChatService(this.storage);

  /// Strict medical system prompt for the main conversational turn
  String _buildSystemPrompt({
    required String originalText,
    required String simplifiedText,
  }) {
    return '''
You are MedSimplify Assistant, an empathetic, clear, and reliable medical communication assistant. You help the patient and their family members understand their hospital discharge summary, diagnoses, medications, and recovery care in simple Indian Lay English.

GROUNDING CONTEXT:
--- ORIGINAL CLINICAL SUMMARY ---
$originalText

--- SIMPLIFIED SUMMARY ---
$simplifiedText

CLINICAL & SAFETY GUARDRAIL RULES:
1. DOMAIN LIMITATION: You are strictly a medical communication assistant. ONLY answer questions related to medical health, conditions, symptoms, medications, discharge instructions, diet, physical precautions, and recovery care. If the user asks about unrelated topics (e.g. computer programming, politics, general math, movie trivia, finance), politely decline and state that you are only designed to answer healthcare and discharge questions.
2. CONTEXTUAL RELEVANCE: Activities (like "football", "swimming", "driving", "climbing stairs") and food items are VALID medical questions when asked in the context of recovery, injury prevention, or dietary restrictions. Answer them clearly in relation to the patient's diagnosed health conditions.
3. INDIAN LAY ENGLISH: Use simple, warm, and respectful Indian Lay English (6th-grade reading level). Whenever a medical term is mentioned, immediately explain it simply in parentheses (e.g., 'hypertension (high BP)', 'diabetes (blood sugar problem)', 'creatinine (kidney function marker)', 'edema (swelling)').
4. MEDICATIONS: Clearly state the medicine name, what it does in plain words, and the importance of taking it exactly as prescribed.
5. WARNING SIGNS / RED FLAGS: Clearly highlight symptoms that require immediate hospital/emergency care.
6. FORMATTING: Use clear bullet points and bold highlights for readability.
7. DISCLAIMER: Always remind the family to consult their treating doctor for emergency symptoms or dosage changes.
''';
  }

  /// Fast Pre-Flight Intent Classifier (Dual-Call Guardrail)
  /// Checks if the query is medical/health-related or completely off-topic.
  Future<bool> _isMedicallyRelevant({
    required String query,
    required String summarySnippet,
    required ApiModel model,
  }) async {
    final classifierPrompt = '''
You are a Medical Intent Guardrail Classifier.
Determine if the following user query is related to:
- Medical conditions, illnesses, symptoms, anatomy, or hospital discharge
- Medications, prescriptions, dosages, side effects, or treatments
- Health precautions, physical activities (e.g., sports/football injuries, post-op mobility), or diet/nutrition related to health
- Follow-up care, emotional recovery from illness, or medical emergencies.

User Query: "$query"
Summary Context Snippet: "$summarySnippet"

Respond ONLY with valid JSON:
{"allowed": true}
or
{"allowed": false}
''';

    try {
      String rawResponse = '';
      switch (model.provider) {
        case 'cerebras':
          final key = storage.cerebrasKey;
          if (key.isNotEmpty) {
            final res = await CerebrasService(key).complete(
              modelId: model.id,
              prompt: classifierPrompt,
            );
            rawResponse = res.text;
          }
          break;

        case 'gemini':
          final key = storage.geminiKey;
          if (key.isNotEmpty) {
            final res = await GeminiService(key).complete(
              modelId: model.id,
              prompt: classifierPrompt,
            );
            rawResponse = res.text;
          }
          break;

        case 'groq':
          final key = storage.groqKey;
          if (key.isNotEmpty) {
            final res = await GroqService(key).complete(
              modelId: model.id,
              prompt: classifierPrompt,
            );
            rawResponse = res.text;
          }
          break;
      }

      if (rawResponse.isNotEmpty) {
        // Extract JSON from response
        final jsonMatch = RegExp(r'\{[\s\S]*?\}').firstMatch(rawResponse);
        if (jsonMatch != null) {
          final parsed = jsonDecode(jsonMatch.group(0)!);
          if (parsed is Map && parsed.containsKey('allowed')) {
            return parsed['allowed'] == true;
          }
        }
      }
    } catch (_) {
      // In case of network timeout on classifier, fallback safely to allowing main LLM guardrails
      return true;
    }

    return true;
  }

  Future<ChatMessage> sendMessage({
    required List<ChatMessage> conversationHistory,
    required String originalText,
    required String simplifiedText,
    required ApiModel model,
  }) async {
    final latestUserQuery = conversationHistory.isNotEmpty &&
            conversationHistory.last.role == 'user'
        ? conversationHistory.last.text
        : '';

    // ── STAGE 1: Fast Pre-Flight Classifier Call ──────────────────────────
    if (latestUserQuery.isNotEmpty) {
      final summarySnippet = originalText.length > 200
          ? '${originalText.substring(0, 200)}...'
          : originalText;

      final isAllowed = await _isMedicallyRelevant(
        query: latestUserQuery,
        summarySnippet: summarySnippet,
        model: model,
      );

      if (!isAllowed) {
        return ChatMessage(
          role: 'assistant',
          text:
              'I am a specialized **Medical Health Assistant** designed to help you understand your hospital discharge summary, medications, diet, and recovery care.\n\n'
              'I can only assist with **medical and health-related questions**. Please feel free to ask about your symptoms, prescribed medicines, foods to avoid, or recovery precautions!',
          timestamp: DateTime.now(),
        );
      }
    }

    // ── STAGE 2: Main Grounded Clinical Chat Turn ─────────────────────────
    final systemPrompt = _buildSystemPrompt(
      originalText: originalText,
      simplifiedText: simplifiedText,
    );

    late final ({String text, int? tokens}) apiResult;

    switch (model.provider) {
      case 'cerebras':
        final key = storage.cerebrasKey;
        if (key.isEmpty) {
          throw Exception(
              'Cerebras API key not set. Please add it in Settings.');
        }
        apiResult = await CerebrasService(key).chat(
          modelId: model.id,
          messages: conversationHistory,
          systemPrompt: systemPrompt,
        );
        break;

      case 'gemini':
        final key = storage.geminiKey;
        if (key.isEmpty) {
          throw Exception(
              'Gemini API key not set. Please add it in Settings.');
        }
        apiResult = await GeminiService(key).chat(
          modelId: model.id,
          messages: conversationHistory,
          systemPrompt: systemPrompt,
        );
        break;

      case 'groq':
        final key = storage.groqKey;
        if (key.isEmpty) {
          throw Exception(
              'Groq API key not set. Please add it in Settings.');
        }
        apiResult = await GroqService(key).chat(
          modelId: model.id,
          messages: conversationHistory,
          systemPrompt: systemPrompt,
        );
        break;

      default:
        throw Exception('Unknown provider: ${model.provider}');
    }

    return ChatMessage(
      role: 'assistant',
      text: apiResult.text,
      timestamp: DateTime.now(),
    );
  }
}
