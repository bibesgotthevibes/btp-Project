import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/simplify_result.dart';

/// Wrapper around shared_preferences for all persistent state:
///   - API keys (cerebras, gemini, groq)
///   - Last used model + strategy
///   - History (list of SimplifyResult)
class StorageService {
  static const _keyCerebras = 'api_key_cerebras';
  static const _keyGemini = 'api_key_gemini';
  static const _keyGroq = 'api_key_groq';
  static const _keyLastModel = 'last_model_id';
  static const _keyLastStrategy = 'last_strategy';
  static const _keyHistory = 'history_v1';
  static const _keyThemeMode = 'theme_mode'; // 'light' | 'dark' | 'system'

  late final SharedPreferences _prefs;

  StorageService._(this._prefs);

  static Future<StorageService> create() async {
    final prefs = await SharedPreferences.getInstance();
    return StorageService._(prefs);
  }

  // ── API Keys ───────────────────────────────────────────────────────────────

  String get cerebrasKey => _prefs.getString(_keyCerebras) ?? '';
  String get geminiKey => _prefs.getString(_keyGemini) ?? '';
  String get groqKey => _prefs.getString(_keyGroq) ?? '';

  Future<void> setCerebrasKey(String v) => _prefs.setString(_keyCerebras, v);
  Future<void> setGeminiKey(String v) => _prefs.setString(_keyGemini, v);
  Future<void> setGroqKey(String v) => _prefs.setString(_keyGroq, v);

  /// Returns true if at least one API key is configured
  bool get hasAnyKey =>
      cerebrasKey.isNotEmpty || geminiKey.isNotEmpty || groqKey.isNotEmpty;

  // ── Last Selections ────────────────────────────────────────────────────────

  String get lastModelId =>
      _prefs.getString(_keyLastModel) ?? 'gemini-2.5-flash';
  String get lastStrategy =>
      _prefs.getString(_keyLastStrategy) ?? 'zero-shot';

  Future<void> setLastModelId(String v) => _prefs.setString(_keyLastModel, v);
  Future<void> setLastStrategy(String v) =>
      _prefs.setString(_keyLastStrategy, v);

  // ── Theme ──────────────────────────────────────────────────────────────────

  String get themeMode => _prefs.getString(_keyThemeMode) ?? 'system';
  Future<void> setThemeMode(String v) => _prefs.setString(_keyThemeMode, v);

  // ── History ────────────────────────────────────────────────────────────────

  List<SimplifyResult> getHistory() {
    final raw = _prefs.getStringList(_keyHistory) ?? [];
    return raw
        .map((s) {
          try {
            return SimplifyResult.fromJson(
                jsonDecode(s) as Map<String, dynamic>);
          } catch (_) {
            return null;
          }
        })
        .whereType<SimplifyResult>()
        .toList()
        .reversed
        .toList(); // newest first
  }

  Future<void> addToHistory(SimplifyResult result) async {
    final raw = _prefs.getStringList(_keyHistory) ?? [];
    raw.add(jsonEncode(result.toJson()));
    // Keep at most 50 entries
    final trimmed = raw.length > 50 ? raw.sublist(raw.length - 50) : raw;
    await _prefs.setStringList(_keyHistory, trimmed);
  }

  Future<void> clearHistory() => _prefs.remove(_keyHistory);
}
