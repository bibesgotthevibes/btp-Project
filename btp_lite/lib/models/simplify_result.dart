/// The result of a successful simplification
class SimplifyResult {
  final String simplifiedText;
  final String originalText;
  final String modelName;
  final String provider;
  final int? tokensUsed;
  final DateTime timestamp;
  final String strategy;
  final String originalSnippet; // first 120 chars of input for history display

  SimplifyResult({
    required this.simplifiedText,
    required this.originalText,
    required this.modelName,
    required this.provider,
    this.tokensUsed,
    required this.timestamp,
    required this.strategy,
    required this.originalSnippet,
  });

  /// Serialise to a JSON-safe map for shared_preferences storage
  Map<String, dynamic> toJson() => {
        'simplifiedText': simplifiedText,
        'originalText': originalText,
        'modelName': modelName,
        'provider': provider,
        'tokensUsed': tokensUsed,
        'timestamp': timestamp.toIso8601String(),
        'strategy': strategy,
        'originalSnippet': originalSnippet,
      };

  factory SimplifyResult.fromJson(Map<String, dynamic> json) => SimplifyResult(
        simplifiedText: json['simplifiedText'] as String,
        originalText: (json['originalText'] as String?) ?? (json['originalSnippet'] as String? ?? ''),
        modelName: json['modelName'] as String,
        provider: json['provider'] as String,
        tokensUsed: json['tokensUsed'] as int?,
        timestamp: DateTime.parse(json['timestamp'] as String),
        strategy: json['strategy'] as String,
        originalSnippet: json['originalSnippet'] as String,
      );
}
