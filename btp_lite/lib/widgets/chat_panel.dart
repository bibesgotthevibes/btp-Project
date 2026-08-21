import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/api_model.dart';
import '../models/chat_message.dart';
import '../models/discharge_knowledge.dart';
import '../models/simplify_result.dart';
import '../services/chat_service.dart';
import '../services/storage_service.dart';
import '../theme/app_theme.dart';

class ChatPanel extends StatefulWidget {
  final SimplifyResult? result;
  final String? rawClinicalText;
  final ApiModel model;
  final bool isCompact;
  final DischargeKnowledge? knowledge;
  final String? initialMessage;

  const ChatPanel({
    super.key,
    this.result,
    this.rawClinicalText,
    required this.model,
    this.isCompact = false,
    this.knowledge,
    this.initialMessage,
  });

  @override
  State<ChatPanel> createState() => _ChatPanelState();
}

class _ChatPanelState extends State<ChatPanel> {
  final _inputController = TextEditingController();
  final _scrollController = ScrollController();
  final _focusNode = FocusNode();
  final List<ChatMessage> _messages = [];
  bool _isSending = false;
  String? _chatError;

  final List<String> _starterPrompts = [];

  List<String> _buildStarterPrompts() {
    final k = widget.knowledge;
    if (k != null) {
      // Personalized chips from extracted knowledge
      final chips = <String>[];
      chips.add('🩺 Explain my diagnosis in simple words');
      if (k.medications.isNotEmpty) {
        chips.add('💊 Why do I need ${k.medications.first.name}?');
      }
      if (k.anomalies.any((a) => a.severity == 'critical')) {
        chips.add('🔬 Explain my critical test results');
      } else if (k.anomalies.isNotEmpty) {
        chips.add('🔬 Explain my lab and test findings');
      }
      if (k.hasAppointments) {
        chips.add('📅 When is my next appointment?');
      }
      if (k.warningSignals.isNotEmpty) {
        chips.add('🚨 What are my emergency warning signs?');
      }
      return chips;
    }
    // Default chips for non-grounded mode
    return [
      '💊 Explain my medicines & timings',
      '⚠️ What warning signs should we watch for?',
      '🥗 What food & diet should I follow?',
      '🩺 When is the doctor follow-up?',
    ];
  }

  @override
  void initState() {
    super.initState();
    _starterPrompts.addAll(_buildStarterPrompts());
    _initGreeting();
    // Auto-send initialMessage if provided (from smart chip tap on dashboard)
    if (widget.initialMessage != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _sendMessage(widget.initialMessage);
      });
    }
  }

  void _initGreeting() {
    _messages.add(
      ChatMessage(
        role: 'assistant',
        text:
            '**Namaste!** I am your **MedSimplify Assistant**.\n\n'
            'Feel free to ask me anything about your medicines, diet, precautions, warning signs, or recovery instructions in plain English or Hindi medical terms.',
        timestamp: DateTime.now(),
      ),
    );
  }

  Future<void> _sendMessage([String? customText]) async {
    final text = (customText ?? _inputController.text).trim();
    if (text.isEmpty || _isSending) return;

    if (customText == null) {
      _inputController.clear();
    }

    final userMsg = ChatMessage(
      role: 'user',
      text: text,
      timestamp: DateTime.now(),
    );

    setState(() {
      _messages.add(userMsg);
      _isSending = true;
      _chatError = null;
    });

    _scrollToBottom();

    try {
      final storage = context.read<StorageService>();
      final chatService = ChatService(storage);

      final originalText = widget.knowledge != null
          ? widget.knowledge!.toSystemPromptContext()
          : (widget.result?.originalText ?? widget.rawClinicalText ?? '');
      final simplifiedText = widget.result?.simplifiedText ?? '';

      final assistantMsg = await chatService.sendMessage(
        conversationHistory: _messages,
        originalText: originalText,
        simplifiedText: simplifiedText,
        model: widget.model,
      );

      setState(() {
        _messages.add(assistantMsg);
      });
    } catch (e) {
      setState(() {
        _chatError = e.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      setState(() {
        _isSending = false;
      });
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent + 80,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _resetChat() {
    setState(() {
      _messages.clear();
      _chatError = null;
      _initGreeting();
    });
  }

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cardColor = isDark ? AppTheme.cardDark : AppTheme.cardLight;
    final borderColor = isDark ? AppTheme.borderDark : AppTheme.borderLight;
    final textColor =
        isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor =
        isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;
    final bgInputColor = isDark ? AppTheme.bgDark : AppTheme.bgLight;

    return Container(
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // ── Chat Header ─────────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.forum_rounded,
                      color: Colors.white, size: 18),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'MedSimplify Medical Assistant',
                        style: GoogleFonts.inter(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                          color: textColor,
                        ),
                      ),
                      Text(
                        'Powered by ${widget.model.name} · Ask any question',
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          color: subColor,
                        ),
                      ),
                    ],
                  ),
                ),
                Tooltip(
                  message: 'Reset chat',
                  child: IconButton(
                    icon: Icon(Icons.refresh_rounded,
                        size: 18, color: subColor),
                    onPressed: _resetChat,
                  ),
                ),
              ],
            ),
          ),
          Divider(height: 1, color: borderColor),

          // ── Messages List ───────────────────────────────────────────────────
          Container(
            constraints: BoxConstraints(
              maxHeight: widget.isCompact ? 360 : 420,
              minHeight: 220,
            ),
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length + (_isSending ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == _messages.length && _isSending) {
                  return _buildTypingIndicator(isDark);
                }
                final msg = _messages[index];
                return _buildMessageBubble(msg, isDark, textColor, subColor);
              },
            ),
          ),

          // ── Starter Prompts (if only greeting message) ──────────────────────
          if (_messages.length <= 1) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _starterPrompts.map((prompt) {
                  return Material(
                    color: Colors.transparent,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(20),
                      onTap: _isSending ? null : () => _sendMessage(prompt),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF6C4DF6).withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: const Color(0xFF6C4DF6).withValues(alpha: 0.3),
                          ),
                        ),
                        child: Text(
                          prompt,
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: isDark
                                ? const Color(0xFFA78BFA)
                                : const Color(0xFF6C4DF6),
                          ),
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),
          ],

          // ── Error Alert ─────────────────────────────────────────────────────
          if (_chatError != null) ...[
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFFECACA)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.error_outline_rounded,
                      color: Color(0xFFEF4444), size: 16),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _chatError!,
                      style: GoogleFonts.inter(
                          fontSize: 12, color: const Color(0xFFDC2626)),
                    ),
                  ),
                ],
              ),
            ),
          ],

          Divider(height: 1, color: borderColor),

          // ── Input Bar ───────────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Expanded(
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: () => _focusNode.requestFocus(),
                    child: TextField(
                      controller: _inputController,
                      focusNode: _focusNode,
                      minLines: 1,
                      maxLines: 4,
                      textAlignVertical: TextAlignVertical.center,
                      style: GoogleFonts.inter(fontSize: 13, color: textColor),
                      onSubmitted: (_) => _sendMessage(),
                      textInputAction: TextInputAction.send,
                      decoration: InputDecoration(
                        isDense: true,
                        hintText: 'Ask follow-up question (e.g. "What to eat?")...',
                        hintStyle: GoogleFonts.inter(
                          fontSize: 13,
                          color: subColor.withValues(alpha: 0.7),
                        ),
                        filled: true,
                        fillColor: bgInputColor,
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 12),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide(color: borderColor),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide(color: borderColor),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: const BorderSide(
                              color: AppTheme.primaryIndigo, width: 1.5),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  onPressed: _isSending ? null : () => _sendMessage(),
                  icon: _isSending
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.send_rounded, size: 18),
                  style: IconButton.styleFrom(
                    backgroundColor: AppTheme.primaryIndigo,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.all(12),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(
    ChatMessage msg,
    bool isDark,
    Color textColor,
    Color subColor,
  ) {
    if (msg.isUser) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.end,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Flexible(
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                decoration: const BoxDecoration(
                  color: AppTheme.primaryIndigo,
                  borderRadius: BorderRadius.only(
                    topLeft: Radius.circular(16),
                    topRight: Radius.circular(4),
                    bottomLeft: Radius.circular(16),
                    bottomRight: Radius.circular(16),
                  ),
                ),
                child: Text(
                  msg.text,
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    color: Colors.white,
                    height: 1.5,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            const CircleAvatar(
              radius: 14,
              backgroundColor: AppTheme.primaryIndigoDark,
              child: Icon(Icons.person_rounded,
                  size: 16, color: Colors.white),
            ),
          ],
        ),
      );
    }

    // Assistant message bubble
    final bubbleBg = isDark
        ? const Color(0xFF161B22)
        : const Color(0xFFF5F7FA);

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.smart_toy_rounded,
                size: 16, color: Colors.white),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: bubbleBg,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(4),
                  topRight: Radius.circular(16),
                  bottomLeft: Radius.circular(16),
                  bottomRight: Radius.circular(16),
                ),
                border: Border.all(
                  color: isDark
                      ? const Color(0xFF30363D)
                      : const Color(0xFFE5E7EB),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  MarkdownBody(
                    data: msg.text,
                    styleSheet: MarkdownStyleSheet(
                      p: GoogleFonts.inter(
                        fontSize: 13,
                        color: textColor,
                        height: 1.6,
                      ),
                      strong: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: textColor,
                      ),
                      listBullet: GoogleFonts.inter(
                        fontSize: 13,
                        color: const Color(0xFF6C4DF6),
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Align(
                    alignment: Alignment.centerRight,
                    child: InkWell(
                      onTap: () async {
                        await Clipboard.setData(
                            ClipboardData(text: msg.text));
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Copied message ✓'),
                              duration: Duration(seconds: 1),
                            ),
                          );
                        }
                      },
                      child: Padding(
                        padding: const EdgeInsets.all(2),
                        child: Icon(Icons.copy_rounded,
                            size: 14, color: subColor.withValues(alpha: 0.6)),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTypingIndicator(bool isDark) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.smart_toy_rounded,
                size: 16, color: Colors.white),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF161B22) : const Color(0xFFF5F7FA),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Assistant is thinking',
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: const Color(0xFF6C4DF6),
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(width: 6),
                ...List.generate(
                  3,
                  (i) => Container(
                    margin: const EdgeInsets.symmetric(horizontal: 2),
                    width: 5,
                    height: 5,
                    decoration: BoxDecoration(
                      color: const Color(0xFF6C4DF6),
                      borderRadius: BorderRadius.circular(3),
                    ),
                  )
                      .animate(onPlay: (c) => c.repeat())
                      .fadeIn(
                          delay: Duration(milliseconds: i * 200),
                          duration: 350.ms)
                      .then()
                      .fadeOut(duration: 350.ms),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
