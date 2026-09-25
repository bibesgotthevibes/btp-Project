/// Represents a message in the medical follow-up chatbot session
class ChatMessage {
  final String role; // 'user' | 'assistant' | 'system'
  final String text;
  final DateTime timestamp;
  final bool isTyping;

  /// Optional attached document (e.g. uploaded/pasted discharge summary)
  final String? attachmentName;
  final String? attachmentSnippet;
  final int? attachmentWordCount;

  /// Optional clinical reasoning or thought process (Claude-style dropdown)
  final String? thoughtSummary;

  /// Optional linked artifact IDs for this message
  final List<String> artifactIds;

  const ChatMessage({
    required this.role,
    required this.text,
    required this.timestamp,
    this.isTyping = false,
    this.attachmentName,
    this.attachmentSnippet,
    this.attachmentWordCount,
    this.thoughtSummary,
    this.artifactIds = const [],
  });

  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';
  bool get hasAttachment => attachmentName != null;
  bool get hasArtifacts => artifactIds.isNotEmpty;

  Map<String, dynamic> toJson() => {
        'role': role,
        'text': text,
        'timestamp': timestamp.toIso8601String(),
        if (attachmentName != null) 'attachmentName': attachmentName,
        if (attachmentSnippet != null) 'attachmentSnippet': attachmentSnippet,
        if (attachmentWordCount != null)
          'attachmentWordCount': attachmentWordCount,
        if (thoughtSummary != null) 'thoughtSummary': thoughtSummary,
        if (artifactIds.isNotEmpty) 'artifactIds': artifactIds,
      };

  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
        role: json['role'] as String,
        text: json['text'] as String,
        timestamp: DateTime.parse(json['timestamp'] as String),
        attachmentName: json['attachmentName'] as String?,
        attachmentSnippet: json['attachmentSnippet'] as String?,
        attachmentWordCount: json['attachmentWordCount'] as int?,
        thoughtSummary: json['thoughtSummary'] as String?,
        artifactIds: List<String>.from(json['artifactIds'] as List? ?? []),
      );

  ChatMessage copyWith({
    String? role,
    String? text,
    DateTime? timestamp,
    bool? isTyping,
    String? attachmentName,
    String? attachmentSnippet,
    int? attachmentWordCount,
    String? thoughtSummary,
    List<String>? artifactIds,
  }) {
    return ChatMessage(
      role: role ?? this.role,
      text: text ?? this.text,
      timestamp: timestamp ?? this.timestamp,
      isTyping: isTyping ?? this.isTyping,
      attachmentName: attachmentName ?? this.attachmentName,
      attachmentSnippet: attachmentSnippet ?? this.attachmentSnippet,
      attachmentWordCount: attachmentWordCount ?? this.attachmentWordCount,
      thoughtSummary: thoughtSummary ?? this.thoughtSummary,
      artifactIds: artifactIds ?? this.artifactIds,
    );
  }
}
