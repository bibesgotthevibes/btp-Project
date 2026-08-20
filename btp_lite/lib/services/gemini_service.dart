import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/chat_message.dart';

/// Calls Google Gemini via the REST generateContent endpoint
class GeminiService {
  static const _baseUrl =
      'https://generativelanguage.googleapis.com/v1beta/models';

  final String apiKey;

  GeminiService(this.apiKey);

  Future<({String text, int? tokens})> complete({
    required String modelId,
    required String prompt,
  }) async {
    final uri = Uri.parse('$_baseUrl/$modelId:generateContent?key=$apiKey');

    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'contents': [
          {
            'parts': [
              {'text': prompt},
            ],
          }
        ],
        'generationConfig': {
          'maxOutputTokens': 8192,
          'temperature': 0.3,
        },
      }),
    );

    if (response.statusCode != 200) {
      final body = jsonDecode(response.body);
      final msg = body['error']?['message'] ?? response.body;
      throw Exception('Gemini API error ${response.statusCode}: $msg');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final text =
        data['candidates']?[0]?['content']?['parts']?[0]?['text'] as String? ??
            '';
    final tokens =
        data['usageMetadata']?['totalTokenCount'] as int?;
    return (text: text.trim(), tokens: tokens);
  }

  /// Multi-turn chat completion with system instructions
  Future<({String text, int? tokens})> chat({
    required String modelId,
    required List<ChatMessage> messages,
    required String systemPrompt,
  }) async {
    final uri = Uri.parse('$_baseUrl/$modelId:generateContent?key=$apiKey');

    final formattedContents = messages.map((m) {
      return {
        'role': m.role == 'assistant' ? 'model' : 'user',
        'parts': [
          {'text': m.text}
        ],
      };
    }).toList();

    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'systemInstruction': {
          'parts': [
            {'text': systemPrompt}
          ]
        },
        'contents': formattedContents,
        'generationConfig': {
          'maxOutputTokens': 4096,
          'temperature': 0.4,
        },
      }),
    );

    if (response.statusCode != 200) {
      final body = jsonDecode(response.body);
      final msg = body['error']?['message'] ?? response.body;
      throw Exception('Gemini Chat API error ${response.statusCode}: $msg');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final text =
        data['candidates']?[0]?['content']?['parts']?[0]?['text'] as String? ??
            '';
    final tokens =
        data['usageMetadata']?['totalTokenCount'] as int?;
    return (text: text.trim(), tokens: tokens);
  }
}
