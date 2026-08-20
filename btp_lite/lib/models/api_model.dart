/// Descriptor for an available AI model
class ApiModel {
  final String id;
  final String name;
  final String provider; // 'cerebras' | 'gemini' | 'groq'
  final String description;

  const ApiModel({
    required this.id,
    required this.name,
    required this.provider,
    required this.description,
  });

  /// All available cloud API models — alphabetical by provider
  static const List<ApiModel> all = [
    // ── Cerebras ──────────────────────────────────────────────────────────────
    ApiModel(
      id: 'llama3.1-8b',
      name: 'Llama 3.1 8B',
      provider: 'cerebras',
      description: 'Fast inference via Cerebras Cloud',
    ),
    // ── Gemini ────────────────────────────────────────────────────────────────
    ApiModel(
      id: 'gemini-2.5-flash',
      name: 'Gemini 2.5 Flash',
      provider: 'gemini',
      description: 'Google\'s fast multimodal model',
    ),
    // ── Groq ──────────────────────────────────────────────────────────────────
    ApiModel(
      id: 'llama-3.3-70b-versatile',
      name: 'Llama 3.3 70B',
      provider: 'groq',
      description: 'High-quality 70B model via Groq',
    ),
    ApiModel(
      id: 'llama-3.1-8b-instant',
      name: 'Llama 3.1 8B Instant',
      provider: 'groq',
      description: 'Ultra-fast 8B model via Groq',
    ),
  ];

  /// Provider display name
  String get providerLabel {
    switch (provider) {
      case 'cerebras':
        return 'Cerebras';
      case 'gemini':
        return 'Google Gemini';
      case 'groq':
        return 'Groq';
      default:
        return provider;
    }
  }

  /// Provider emoji badge
  String get providerBadge {
    switch (provider) {
      case 'cerebras':
        return '⚡';
      case 'gemini':
        return '✦';
      case 'groq':
        return '🚀';
      default:
        return '🤖';
    }
  }
}
