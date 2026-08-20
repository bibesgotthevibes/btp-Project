/// Represents a message in the medical follow-up chatbot session
class ChatMessage {
  final String role; // 'user' | 'assistant' | 'system'
  final String text;
  final DateTime timestamp;
  final bool isTyping;

  const ChatMessage({
    required this.role,
    required this.text,
    required this.timestamp,
    this.isTyping = false,
  });

  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';

  Map<String, dynamic> toJson() => {
        'role': role,
        'text': text,
        'timestamp': timestamp.toIso8601String(),
      };

  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
        role: json['role'] as String,
        text: json['text'] as String,
        timestamp: DateTime.parse(json['timestamp'] as String),
      );

  ChatMessage copyWith({
    String? role,
    String? text,
    DateTime? timestamp,
    bool? isTyping,
  }) {
    return ChatMessage(
      role: role ?? this.role,
      text: text ?? this.text,
      timestamp: timestamp ?? this.timestamp,
      isTyping: isTyping ?? this.isTyping,
    );
  }
}
