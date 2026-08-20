import '../models/api_model.dart';
import '../models/simplify_result.dart';
import '../services/cerebras_service.dart';
import '../services/gemini_service.dart';
import '../services/groq_service.dart';
import '../services/prompt_service.dart';
import '../services/storage_service.dart';

/// Orchestrates: preprocess → build prompt → call correct API → return result
class SimplifyService {
  final StorageService storage;

  SimplifyService(this.storage);

  Future<SimplifyResult> simplify({
    required String rawText,
    required ApiModel model,
    required String strategy,
  }) async {
    // 1. Preprocess input
    final processedText = preprocessMedicalText(rawText);

    // 2. Build prompt
    final prompt = buildPromptString(strategy, processedText);

    // 3. Call the correct API
    late final ({String text, int? tokens}) apiResult;

    switch (model.provider) {
      case 'cerebras':
        final key = storage.cerebrasKey;
        if (key.isEmpty) {
          throw Exception(
              'Cerebras API key not set. Please add it in Settings.');
        }
        apiResult = await CerebrasService(key)
            .complete(modelId: model.id, prompt: prompt);
        break;

      case 'gemini':
        final key = storage.geminiKey;
        if (key.isEmpty) {
          throw Exception(
              'Gemini API key not set. Please add it in Settings.');
        }
        apiResult = await GeminiService(key)
            .complete(modelId: model.id, prompt: prompt);
        break;

      case 'groq':
        final key = storage.groqKey;
        if (key.isEmpty) {
          throw Exception(
              'Groq API key not set. Please add it in Settings.');
        }
        apiResult =
            await GroqService(key).complete(modelId: model.id, prompt: prompt);
        break;

      default:
        throw Exception('Unknown provider: ${model.provider}');
    }

    // 4. Build result
    final snippet = rawText.length > 120
        ? '${rawText.substring(0, 120).trim()}…'
        : rawText.trim();

    final result = SimplifyResult(
      simplifiedText: apiResult.text,
      originalText: rawText,
      modelName: model.name,
      provider: model.provider,
      tokensUsed: apiResult.tokens,
      timestamp: DateTime.now(),
      strategy: strategy,
      originalSnippet: snippet,
    );

    // 5. Persist to history
    await storage.addToHistory(result);

    return result;
  }
}
