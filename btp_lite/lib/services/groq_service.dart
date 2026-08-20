import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/chat_message.dart';

/// Calls Groq Cloud (OpenAI-compatible chat completions endpoint)
class GroqService {
  static const _baseUrl =
      'https://api.groq.com/openai/v1/chat/completions';

  final String apiKey;

  GroqService(this.apiKey);

  Future<({String text, int? tokens})> complete({
    required String modelId,
    required String prompt,
  }) async {
    final response = await http.post(
      Uri.parse(_baseUrl),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $apiKey',
      },
      body: jsonEncode({
        'model': modelId,
        'messages': [
          {'role': 'user', 'content': prompt},
        ],
        'max_tokens': 2048,
        'temperature': 0.3,
      }),
    );

    if (response.statusCode != 200) {
      final body = jsonDecode(response.body);
      final msg = body['error']?['message'] ?? response.body;
      throw Exception('Groq API error ${response.statusCode}: $msg');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final text =
        data['choices'][0]['message']['content'] as String? ?? '';
    final tokens = data['usage']?['total_tokens'] as int?;
    return (text: text.trim(), tokens: tokens);
  }

  /// Multi-turn chat completion
  Future<({String text, int? tokens})> chat({
    required String modelId,
    required List<ChatMessage> messages,
    required String systemPrompt,
  }) async {
    final formattedMessages = <Map<String, String>>[
      {'role': 'system', 'content': systemPrompt},
      ...messages.map((m) => {
            'role': m.role,
            'content': m.text,
          }),
    ];

    final response = await http.post(
      Uri.parse(_baseUrl),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $apiKey',
      },
      body: jsonEncode({
        'model': modelId,
        'messages': formattedMessages,
        'max_tokens': 2048,
        'temperature': 0.4,
      }),
    );

    if (response.statusCode != 200) {
      final body = jsonDecode(response.body);
      final msg = body['error']?['message'] ?? response.body;
      throw Exception('Groq Chat API error ${response.statusCode}: $msg');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final text =
        data['choices'][0]['message']['content'] as String? ?? '';
    final tokens = data['usage']?['total_tokens'] as int?;
    return (text: text.trim(), tokens: tokens);
  }
}
