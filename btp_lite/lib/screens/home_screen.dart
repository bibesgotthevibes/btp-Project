import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../models/api_model.dart';
import '../models/chat_message.dart';
import '../models/medical_artifact.dart';
import '../models/simplify_result.dart';
import '../services/artifact_service.dart';
import '../services/chat_service.dart';
import '../services/simplify_service.dart';
import '../services/storage_service.dart';
import '../theme/app_theme.dart';
import '../widgets/app_drawer.dart';
import '../widgets/artifact_card_pill.dart';
import '../widgets/artifact_panel.dart';
import 'history_screen.dart';
import 'settings_screen.dart';
import 'package:file_picker/file_picker.dart';
import '../services/document_reader_service.dart';

class HomeScreen extends StatefulWidget {
  final VoidCallback onToggleTheme;
  final bool isDark;

  const HomeScreen({
    super.key,
    required this.onToggleTheme,
    required this.isDark,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _inputController = TextEditingController();
  final _scrollController = ScrollController();
  final _focusNode = FocusNode();

  ApiModel _selectedModel = ApiModel.all.firstWhere(
    (m) => m.id == 'gemini-2.5-flash',
    orElse: () => ApiModel.all.first,
  );

  final List<ChatMessage> _messages = [];
  final List<MedicalArtifact> _artifacts = [];
  int _selectedArtifactIndex = 0;
  bool _isArtifactPanelOpen = false;

  bool _isSending = false;
  String? _currentThinkingStatus;
  String? _rawDischargeSummary;
  String? _lastSimplifiedSummary;

  // Sample Cases for instant testing
  static const _sampleCases = [
    (
      title: 'Heart Attack (ACS / STEMI)',
      icon: Icons.favorite_rounded,
      color: Color(0xFFEF4444),
      snippet: 'Acute Anterior STEMI, primary PCI to LAD with stent...',
      text:
          'Patient: 56M. Admitted via ER with retrosternal crushing chest pain, diaphoresis. ECG showed ST elevation in V1-V4 (Acute Anterior STEMI). Troponin I >50 ng/mL. Urgent coronary angiography revealed 95% thrombotic occlusion of proximal LAD. Underwent successful Primary PCI with drug-eluting stent (DES 3.0 x 24mm). Echocardiogram: LVEF 45%, anterior wall hypokinesia. Discharged in stable condition.\n\nPrescribed Medications:\n1. Aspirin 75mg once daily after lunch (Antiplatelet / blood thinner to prevent stent clots)\n2. Ticagrelor 90mg twice daily with meals (Dual antiplatelet, strict 12 months adherence)\n3. Atorvastatin 80mg once daily at bedtime (Cholesterol lowering & plaque stabilizer)\n4. Metoprolol Succinate 25mg once daily morning (Beta-blocker to control heart rate & work)\n5. Ramipril 2.5mg once daily morning (ACE inhibitor to protect heart remodeling)\n6. Sorbitrate 5mg sublingual as needed for acute chest pain\n\nDischarge Instructions & Precautions:\n- Strict low-salt diet (<2g sodium/day), zero smoking, no heavy lifting >5kg for 4 weeks.\n- Emergency Red Flags: Immediate ER visit if recurrent chest tightness, resting breathlessness, dizziness, or syncope.\n- Cardiology OPD review in 2 weeks.'
    ),
    (
      title: 'Diabetic Emergency (DKA)',
      icon: Icons.bloodtype_rounded,
      color: Color(0xFFF59E0B),
      snippet: 'Type 2 Diabetes with DKA, blood sugar 480 mg/dL...',
      text:
          'Patient: 49F with poorly controlled Type 2 Diabetes Mellitus admitted in Diabetic Ketoacidosis (DKA). Random blood sugar 480 mg/dL, arterial blood pH 7.18, serum bicarbonate 11 mEq/L, urine ketones 3+, HbA1c 11.4%. Treated with IV normal saline rehydration, IV regular insulin infusion protocol, potassium replacement. Acidosis resolved. Transitioned to subcutaneous basal-bolus insulin regimen prior to discharge.\n\nPrescribed Medications:\n1. Inj Insulin Glargine (Lantus) 18 units subcutaneously at 10 PM daily\n2. Inj Insulin Aspart (Novorapid) 6 units subcutaneously 15 mins before Breakfast, Lunch, and Dinner\n3. Tab Metformin 500mg twice daily after meals\n\nDischarge Instructions:\n- Home blood glucose monitoring (SMBG) 4 times daily (fasting and 2 hours post meals).\n- Keep rapid-acting glucose / sugar cubes handy for hypoglycemia (shakiness, cold sweat, hunger).\n- Follow diabetic renal-sparing diet with whole grains and leafy vegetables.\n- Warning Signs: Call physician if vomiting >4 hours, urine ketones positive, or blood sugar consistently >250 mg/dL.\n- Endocrinology OPD follow-up in 10 days.'
    ),
    (
      title: 'Gallbladder Surgery (Post-Op)',
      icon: Icons.medical_services_rounded,
      color: Color(0xFF10B981),
      snippet: 'Acute Cholecystitis, elective Laparoscopic Cholecystectomy...',
      text:
          'Patient: 42F admitted with acute calculous cholecystitis with multiple gallstones on ultrasound. Underwent elective Laparoscopic Cholecystectomy under general anesthesia. Operative course uneventful. Minimal blood loss. Tolerating soft diet, ambulatory on Day 1 post-op. Surgical incisions clean, dry, and intact.\n\nPrescribed Medications:\n1. Tab Cefuroxime 500mg twice daily for 5 days after food (Antibiotic prophylaxis)\n2. Tab Paracetamol 650mg + Tramadol 37.5mg every 8 hours as needed for surgical pain\n3. Tab Pantoprazole 40mg once daily before breakfast for 7 days\n\nDischarge Instructions:\n- Keep trocar wound dressings clean and completely dry for 48 hours.\n- Light walking encouraged; avoid abdominal straining, gym, or lifting >5kg for 3 weeks.\n- Maintain low-fat, easily digestible diet (avoid oily, fried curries).\n- Red Flags: Contact hospital immediately if fever >101°F, progressive yellowing of eyes/skin (jaundice), severe abdominal distension, or purulent wound discharge.\n- Surgical clinic visit for suture inspection in 7 days.'
    ),
  ];

  @override
  void initState() {
    super.initState();
    _loadPreferences();
    _initGreeting();
  }

  Future<void> _loadPreferences() async {
    final storage = context.read<StorageService>();
    final savedModelId = storage.lastModelId;
    final model = ApiModel.all.firstWhere(
      (m) => m.id == savedModelId,
      orElse: () => ApiModel.all.firstWhere(
        (m) => m.id == 'gemini-2.5-flash',
        orElse: () => ApiModel.all.first,
      ),
    );
    setState(() {
      _selectedModel = model;
    });
  }

  void _initGreeting() {
    setState(() {
      _messages.add(
        ChatMessage(
          role: 'assistant',
          text:
              '**Namaste! I am your MedSimplify Assistant.**\n\n'
              'I help patients and their families understand hospital discharge summaries, diagnoses, medications, recovery diets, and warning signs in clear, simple **Indian Lay English**.\n\n'
              'You can paste a discharge summary, try one of our sample cases below, or ask any medical question directly.',
          timestamp: DateTime.now(),
        ),
      );
    });
  }

  void _resetChat() {
    setState(() {
      _messages.clear();
      _artifacts.clear();
      _selectedArtifactIndex = 0;
      _isArtifactPanelOpen = false;
      _rawDischargeSummary = null;
      _lastSimplifiedSummary = null;
      _initGreeting();
    });
  }

  void _toggleArtifactPanel([int? targetIndex]) {
    setState(() {
      if (targetIndex != null) {
        _selectedArtifactIndex = targetIndex;
        _isArtifactPanelOpen = true;
      } else {
        _isArtifactPanelOpen = !_isArtifactPanelOpen;
      }
    });
  }

  /// Extracts structured artifacts from a discharge summary and simplified text.
  /// Guarantees:
  /// - Simplified Summary and Original Record are ALWAYS generated.
  /// - Medication Schedule is ONLY generated if the record actually contains medication details.
  /// - Emergency Red Flags are ONLY generated if the record actually contains danger/warning signs.
  void _createArtifactsFromSummary({
    required String rawText,
    required String simplifiedText,
  }) {
    _artifacts.clear();
    final generated = ArtifactService.generateArtifacts(
      rawText: rawText,
      simplifiedText: simplifiedText,
    );
    _artifacts.addAll(generated);

    setState(() {
      _selectedArtifactIndex = 0;
      _isArtifactPanelOpen = true;
    });
  }

  /// Processes a discharge summary: calls SimplifyService and embeds artifacts into chat
  Future<void> _processDischargeSummary(String rawText, {String? customTitle}) async {
    final text = rawText.trim();
    if (text.isEmpty || _isSending) return;

    final wordCount =
        text.split(RegExp(r'\s+')).where((w) => w.isNotEmpty).length;
    final title = customTitle ?? 'Clinical Discharge Summary';

    // Add user message with Claude-style attachment card
    final userMsg = ChatMessage(
      role: 'user',
      text: 'Please simplify this hospital discharge summary and explain it to me and my family.',
      timestamp: DateTime.now(),
      attachmentName: title,
      attachmentSnippet: text.length > 120 ? '${text.substring(0, 120)}…' : text,
      attachmentWordCount: wordCount,
    );

    setState(() {
      _messages.add(userMsg);
      _rawDischargeSummary = text;
      _isSending = true;
      _currentThinkingStatus =
          'Analyzing discharge summary with ${_selectedModel.name}…';
    });

    _scrollToBottom();

    final storage = context.read<StorageService>();

    try {
      final svc = SimplifyService(storage);
      final result = await svc.simplify(
        rawText: text,
        model: _selectedModel,
        strategy: 'few-shot',
      );

      _lastSimplifiedSummary = result.simplifiedText;

      // Generate the pinned Claude-style artifacts!
      _createArtifactsFromSummary(
        rawText: text,
        simplifiedText: result.simplifiedText,
      );

      // Create assistant reply message embedding the artifacts
      final artifactListSb = StringBuffer();
      artifactListSb.writeln(
          'I have carefully reviewed and simplified your discharge summary.\n');
      artifactListSb.writeln(
          'I have generated **${_artifacts.length} clinical artifacts** pinned in the right panel based on the available details in your record:\n');
      for (final art in _artifacts) {
        artifactListSb.writeln('• **${art.displayName}**: ${art.subtitle}');
      }
      artifactListSb.writeln(
          '\nYou can view each artifact on the right, or ask me any follow-up question below!');

      final assistantMsg = ChatMessage(
        role: 'assistant',
        text: artifactListSb.toString(),
        timestamp: DateTime.now(),
        thoughtSummary:
            'Extracted clinical entities · Grounded with Few-Shot · ${result.tokensUsed ?? 1420} tokens',
        artifactIds: _artifacts.map((a) => a.id).toList(),
      );

      setState(() {
        _messages.add(assistantMsg);
      });
    } catch (e) {
      final errorMsg = e.toString().replaceFirst('Exception: ', '');
      setState(() {
        _messages.add(
          ChatMessage(
            role: 'assistant',
            text:
                '⚠️ **Error analyzing summary**: $errorMsg\n\nPlease ensure your API key for ${_selectedModel.providerLabel} is properly configured in Settings.',
            timestamp: DateTime.now(),
          ),
        );
      });
    } finally {
      setState(() {
        _isSending = false;
        _currentThinkingStatus = null;
      });
      _scrollToBottom();
    }
  }

  /// Pins an assistant chat message into the CARE_PLAN.MD artifact (modifying in-place)
  void _pinMessageAsCarePlan(String content) {
    final existingIdx = _artifacts.indexWhere((a) => a.id == 'art-careplan');
    setState(() {
      if (existingIdx != -1) {
        final existing = _artifacts[existingIdx];
        _artifacts[existingIdx] = MedicalArtifact(
          id: 'art-careplan',
          title: 'CARE_PLAN.MD',
          displayName: 'Personalized Care & Recovery Plan',
          subtitle: 'Updated from chat consultation',
          type: MedicalArtifactType.custom,
          content:
              '${existing.content}\n\n---\n\n### Clinical Consultation Note\n$content',
          icon: Icons.event_note_rounded,
          accentColor: const Color(0xFF0EA5E9),
          createdAt: DateTime.now(),
        );
        _selectedArtifactIndex = existingIdx;
      } else {
        _artifacts.add(
          MedicalArtifact(
            id: 'art-careplan',
            title: 'CARE_PLAN.MD',
            displayName: 'Personalized Care & Recovery Plan',
            subtitle: 'Pinned from chat consultation',
            type: MedicalArtifactType.custom,
            content: content,
            icon: Icons.event_note_rounded,
            accentColor: const Color(0xFF0EA5E9),
            createdAt: DateTime.now(),
          ),
        );
        _selectedArtifactIndex = _artifacts.length - 1;
      }
      _isArtifactPanelOpen = true;
    });

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Pinned advice to CARE_PLAN.MD artifact ✓'),
        duration: Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  /// Sends a conversational question to the chatbot
  Future<void> _sendChatMessage([String? customPrompt]) async {
    final text = (customPrompt ?? _inputController.text).trim();
    if (text.isEmpty || _isSending) return;

    if (customPrompt == null) {
      _inputController.clear();
    }

    // Check if the user is pasting a discharge summary directly in the chat input
    final isLongClinicalSummary = text.length > 180 &&
        (text.toLowerCase().contains('admitted') ||
            text.toLowerCase().contains('diagnosis') ||
            text.toLowerCase().contains('discharge') ||
            text.toLowerCase().contains('ecg') ||
            text.toLowerCase().contains('mg') ||
            text.toLowerCase().contains('patient'));

    if (isLongClinicalSummary && _artifacts.isEmpty) {
      await _processDischargeSummary(text);
      return;
    }

    final userMsg = ChatMessage(
      role: 'user',
      text: text,
      timestamp: DateTime.now(),
    );

    setState(() {
      _messages.add(userMsg);
      _isSending = true;
      _currentThinkingStatus = 'Checking clinical safety & reasoning…';
    });

    _scrollToBottom();

    try {
      final storage = context.read<StorageService>();
      final chatService = ChatService(storage);

      final originalText = _rawDischargeSummary ?? '';
      final simplifiedText = _lastSimplifiedSummary ?? '';

      final assistantMsg = await chatService.sendMessage(
        conversationHistory: _messages,
        originalText: originalText,
        simplifiedText: simplifiedText,
        model: _selectedModel,
      );

      // Prevent artifact explosion:
      // Only comprehensive plans/schedules become or update an artifact in-place.
      final queryLower = text.toLowerCase();
      final isPlanRequest = queryLower.contains('diet plan') ||
          queryLower.contains('recovery plan') ||
          queryLower.contains('exercise plan') ||
          queryLower.contains('walking schedule') ||
          queryLower.contains('routine') ||
          queryLower.contains('care plan');

      List<String> linkedArtifacts = [];

      if (isPlanRequest && assistantMsg.text.length > 180) {
        // Find existing custom care plan artifact if present, or add a single bounded one
        final existingPlanIdx =
            _artifacts.indexWhere((a) => a.id == 'art-careplan');

        if (existingPlanIdx != -1) {
          // In-place modification
          _artifacts[existingPlanIdx] = MedicalArtifact(
            id: 'art-careplan',
            title: 'CARE_PLAN.MD',
            displayName: 'Personalized Care & Recovery Plan',
            subtitle: 'Updated from chat consultation',
            type: MedicalArtifactType.custom,
            content: assistantMsg.text,
            icon: Icons.event_note_rounded,
            accentColor: const Color(0xFF0EA5E9),
            createdAt: DateTime.now(),
          );
          _selectedArtifactIndex = existingPlanIdx;
        } else {
          _artifacts.add(
            MedicalArtifact(
              id: 'art-careplan',
              title: 'CARE_PLAN.MD',
              displayName: 'Personalized Care & Recovery Plan',
              subtitle: 'Generated from chat consultation',
              type: MedicalArtifactType.custom,
              content: assistantMsg.text,
              icon: Icons.event_note_rounded,
              accentColor: const Color(0xFF0EA5E9),
              createdAt: DateTime.now(),
            ),
          );
          _selectedArtifactIndex = _artifacts.length - 1;
        }
        _isArtifactPanelOpen = true;
        linkedArtifacts = ['art-careplan'];
      }

      setState(() {
        _messages.add(
          assistantMsg.copyWith(
            artifactIds: linkedArtifacts.isNotEmpty
                ? linkedArtifacts
                : assistantMsg.artifactIds,
          ),
        );
      });
    } catch (e) {
      final err = e.toString().replaceFirst('Exception: ', '');
      setState(() {
        _messages.add(
          ChatMessage(
            role: 'assistant',
            text: '⚠️ **Chat Error**: $err',
            timestamp: DateTime.now(),
          ),
        );
      });
    } finally {
      setState(() {
        _isSending = false;
        _currentThinkingStatus = null;
      });
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent + 120,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _showPasteSummaryModal() {
    final textCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) {
        final isDark = Theme.of(ctx).brightness == Brightness.dark;
        return StatefulBuilder(
          builder: (dialogCtx, setDialogState) {
            final wordCount = textCtrl.text
                .trim()
                .split(RegExp(r'\s+'))
                .where((w) => w.isNotEmpty)
                .length;

            return AlertDialog(
              backgroundColor:
                  isDark ? AppTheme.surfaceDark : AppTheme.surfaceLight,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16)),
              title: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFF6C4DF6).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.paste_rounded,
                        color: Color(0xFF6C4DF6), size: 20),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    'Paste Discharge Summary',
                    style: GoogleFonts.inter(
                        fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                ],
              ),
              content: SizedBox(
                width: 600,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Paste the patient\'s clinical discharge record. Our AI will simplify it and pin the artifacts to the right panel.',
                      style: GoogleFonts.inter(
                        fontSize: 12.5,
                        color: isDark
                            ? AppTheme.textSecondaryDark
                            : AppTheme.textSecondaryLight,
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: textCtrl,
                      maxLines: 8,
                      onChanged: (_) => setDialogState(() {}),
                      style: GoogleFonts.inter(fontSize: 13),
                      decoration: InputDecoration(
                        hintText:
                            'e.g. Patient admitted with chest pain, ST-elevation on ECG, Troponin positive, managed with PCI...',
                        border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Align(
                      alignment: Alignment.centerRight,
                      child: Text(
                        '$wordCount words',
                        style: GoogleFonts.inter(
                            fontSize: 11,
                            color: isDark
                                ? AppTheme.textSecondaryDark
                                : AppTheme.textSecondaryLight),
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                OutlinedButton.icon(
                  onPressed: () {
                    Navigator.pop(dialogCtx);
                    _pickAndUploadDischargeSummary();
                  },
                  icon: const Icon(Icons.upload_file_rounded, size: 16),
                  label: const Text('Upload File (.txt, .pdf)'),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(dialogCtx),
                  child: const Text('Cancel'),
                ),
                ElevatedButton.icon(
                  onPressed: wordCount < 5
                      ? null
                      : () {
                          final text = textCtrl.text;
                          Navigator.pop(dialogCtx);
                          _processDischargeSummary(text);
                        },
                  icon: const Icon(Icons.auto_awesome_rounded, size: 16),
                  label: const Text('Simplify & Create Artifacts'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  /// Picks and processes a discharge summary from a text (.txt, .md) or PDF (.pdf) file
  Future<void> _pickAndUploadDischargeSummary() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['txt', 'pdf', 'md'],
        withData: true,
      );

      if (result == null || result.files.isEmpty) return;

      final file = result.files.single;
      final bytes = file.bytes;
      if (bytes == null) {
        throw Exception('Could not read the selected file bytes.');
      }

      final extraction = DocumentReaderService.extractFromBytes(
        fileName: file.name,
        bytes: bytes,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Loaded ${extraction.fileName} (${extraction.wordCount} words) · Processing...',
            ),
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }

      await _processDischargeSummary(
        extraction.text,
        customTitle: extraction.fileName,
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Error reading document: ${e.toString().replaceFirst("Exception: ", "")}',
            ),
            backgroundColor: const Color(0xFFEF4444),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  void _loadResultFromHistory(SimplifyResult res) {
    _rawDischargeSummary = res.originalText;
    _lastSimplifiedSummary = res.simplifiedText;
    _createArtifactsFromSummary(
      rawText: res.originalText,
      simplifiedText: res.simplifiedText,
    );
    setState(() {
      _messages.add(
        ChatMessage(
          role: 'user',
          text: 'Loaded previous discharge summary from History.',
          timestamp: DateTime.now(),
          attachmentName: 'History Record (${res.modelName})',
          attachmentSnippet: res.originalSnippet,
        ),
      );
      _messages.add(
        ChatMessage(
          role: 'assistant',
          text:
              'I have loaded your saved discharge summary from history into the Artifacts panel. Feel free to ask any follow-up questions about your condition or treatment!',
          timestamp: DateTime.now(),
          artifactIds: _artifacts.map((a) => a.id).toList(),
        ),
      );
    });
    _scrollToBottom();
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
    final isDark = widget.isDark;
    final bgColor = isDark ? AppTheme.bgDark : AppTheme.bgLight;
    final surfaceColor =
        isDark ? AppTheme.surfaceDark : AppTheme.surfaceLight;
    final borderColor =
        isDark ? AppTheme.borderDark : AppTheme.borderLight;
    final textColor =
        isDark ? AppTheme.textPrimaryDark : AppTheme.textPrimaryLight;
    final subColor =
        isDark ? AppTheme.textSecondaryDark : AppTheme.textSecondaryLight;

    final screenWidth = MediaQuery.of(context).size.width;
    final isWideScreen = screenWidth >= 880;

    return Scaffold(
      backgroundColor: bgColor,
      drawer: AppDrawer(
        isDark: isDark,
        onToggleTheme: widget.onToggleTheme,
        onSelectHistory: _loadResultFromHistory,
      ),
      appBar: AppBar(
        backgroundColor: surfaceColor,
        elevation: 0,
        titleSpacing: 0,
        title: Row(
          children: [
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.health_and_safety_rounded,
                  color: Colors.white, size: 18),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'MedSimplify',
                  style: GoogleFonts.inter(
                    fontWeight: FontWeight.w800,
                    fontSize: 16,
                    color: textColor,
                  ),
                ),
                if (_rawDischargeSummary != null)
                  Text(
                    'Discharge Summary Loaded · Grounded Mode',
                    style: GoogleFonts.inter(
                      fontSize: 10.5,
                      fontWeight: FontWeight.w500,
                      color: const Color(0xFF10B981),
                    ),
                  ),
              ],
            ),
          ],
        ),
        actions: [
          // Claude-style "Artifacts (N)" Toggle Button
          Tooltip(
            message: _isArtifactPanelOpen
                ? 'Hide Artifacts panel'
                : 'Show Artifacts panel',
            child: InkWell(
              onTap: () => _toggleArtifactPanel(),
              borderRadius: BorderRadius.circular(8),
              child: Container(
                margin: const EdgeInsets.symmetric(vertical: 8),
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: _isArtifactPanelOpen
                      ? const Color(0xFF6C4DF6)
                      : (isDark
                          ? const Color(0xFF1E2330)
                          : const Color(0xFFF1F5F9)),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: _isArtifactPanelOpen
                        ? const Color(0xFF6C4DF6)
                        : borderColor,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.view_sidebar_rounded,
                      size: 15,
                      color: _isArtifactPanelOpen ? Colors.white : subColor,
                    ),
                    const SizedBox(width: 6),
                    Text(
                      'Artifacts${_artifacts.isNotEmpty ? ' (${_artifacts.length})' : ''}',
                      style: GoogleFonts.inter(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        color: _isArtifactPanelOpen ? Colors.white : textColor,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 4),

          // New Conversation (+)
          IconButton(
            icon: Icon(Icons.add_rounded, size: 24, color: textColor),
            tooltip: 'New Conversation',
            onPressed: _resetChat,
          ),

          // History
          IconButton(
            icon: Icon(Icons.history_rounded, size: 20, color: subColor),
            tooltip: 'History',
            onPressed: () async {
              final res = await Navigator.push<SimplifyResult>(
                context,
                MaterialPageRoute(builder: (_) => const HistoryScreen()),
              );
              if (res != null) {
                _loadResultFromHistory(res);
              }
            },
          ),

          // Theme Toggle
          IconButton(
            icon: Icon(
              isDark ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
              size: 20,
              color: subColor,
            ),
            tooltip: isDark ? 'Light mode' : 'Dark mode',
            onPressed: widget.onToggleTheme,
          ),

          // Settings
          IconButton(
            icon: Icon(Icons.settings_rounded, size: 20, color: subColor),
            tooltip: 'Settings',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const SettingsScreen()),
            ),
          ),
          const SizedBox(width: 8),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Divider(height: 1, color: borderColor),
        ),
      ),
      body: SafeArea(
        child: isWideScreen
            // ── DESKTOP / TABLET SPLIT SCREEN ────────────────────────────────
            ? Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Left Pane: Chatbot
                  Expanded(
                    flex: _isArtifactPanelOpen ? 11 : 1,
                    child: Center(
                      child: ConstrainedBox(
                        constraints: BoxConstraints(
                          maxWidth: _isArtifactPanelOpen ? 820 : 880,
                        ),
                        child: _buildChatColumn(isDark, textColor, subColor,
                            borderColor, surfaceColor),
                      ),
                    ),
                  ),

                  // Right Pane: Claude-style Pinned Artifact Panel
                  if (_isArtifactPanelOpen)
                    Expanded(
                      flex: 9,
                      child: ArtifactPanel(
                        artifacts: _artifacts,
                        selectedIndex: _selectedArtifactIndex,
                        onSelectArtifact: (idx) =>
                            setState(() => _selectedArtifactIndex = idx),
                        onClose: () => setState(() => _isArtifactPanelOpen = false),
                        onAskAboutArtifact: (prompt) => _sendChatMessage(prompt),
                      ).animate().fadeIn(duration: 200.ms).slideX(begin: 0.05, end: 0),
                    ),
                ],
              )
            // ── MOBILE / COMPACT SCREEN ─────────────────────────────────────
            : Stack(
                children: [
                  _buildChatColumn(
                      isDark, textColor, subColor, borderColor, surfaceColor),
                  // Slide-over drawer for Artifacts on mobile
                  if (_isArtifactPanelOpen)
                    Positioned.fill(
                      child: GestureDetector(
                        onTap: () =>
                            setState(() => _isArtifactPanelOpen = false),
                        child: Container(
                          color: Colors.black54,
                          child: Align(
                            alignment: Alignment.centerRight,
                            child: GestureDetector(
                              onTap: () {}, // Prevent tap through
                              child: SizedBox(
                                width: screenWidth * 0.9,
                                child: ArtifactPanel(
                                  artifacts: _artifacts,
                                  selectedIndex: _selectedArtifactIndex,
                                  onSelectArtifact: (idx) => setState(
                                      () => _selectedArtifactIndex = idx),
                                  onClose: () => setState(
                                      () => _isArtifactPanelOpen = false),
                                  onAskAboutArtifact: (prompt) {
                                    setState(() => _isArtifactPanelOpen = false);
                                    _sendChatMessage(prompt);
                                  },
                                ),
                              ),
                            ),
                          ),
                        ),
                      ).animate().fadeIn(duration: 200.ms),
                    ),
                ],
              ),
      ),
    );
  }

  // ── CHAT COLUMN ─────────────────────────────────────────────────────────────
  Widget _buildChatColumn(
    bool isDark,
    Color textColor,
    Color subColor,
    Color borderColor,
    Color surfaceColor,
  ) {
    return Column(
      children: [
        // Chat messages stream
        Expanded(
          child: ListView.builder(
            controller: _scrollController,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            itemCount: _messages.length +
                (_messages.length <= 1 ? 1 : 0) +
                (_isSending ? 1 : 0),
            itemBuilder: (context, index) {
              // Starter sample cards if at beginning
              if (index == 1 && _messages.length <= 1) {
                return _buildSampleCasesSection(isDark, textColor, subColor);
              }

              // Thinking status indicator
              final actualIndex =
                  (_messages.length <= 1 && index > 1) ? index - 1 : index;

              if (actualIndex == _messages.length && _isSending) {
                return _buildThinkingIndicator(isDark, subColor);
              }

              if (actualIndex < _messages.length) {
                final msg = _messages[actualIndex];
                return _buildMessageItem(
                    msg, isDark, textColor, subColor, borderColor);
              }

              return const SizedBox.shrink();
            },
          ),
        ),

        // Docked Claude-style Input Bar at bottom
        _buildBottomInputDock(
            isDark, textColor, subColor, borderColor, surfaceColor),
      ],
    );
  }

  // ── MESSAGE ITEM ───────────────────────────────────────────────────────────
  Widget _buildMessageItem(
    ChatMessage msg,
    bool isDark,
    Color textColor,
    Color subColor,
    Color borderColor,
  ) {
    if (msg.isUser) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            // If user attached a discharge summary, show Claude-style file attachment card!
            if (msg.hasAttachment) ...[
              Container(
                constraints: const BoxConstraints(maxWidth: 380),
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: isDark
                      ? const Color(0xFF1E2330)
                      : const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: borderColor),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF6C4DF6).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.description_rounded,
                          size: 20, color: Color(0xFF6C4DF6)),
                    ),
                    const SizedBox(width: 10),
                    Flexible(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            msg.attachmentName ?? 'Discharge Summary',
                            style: GoogleFonts.inter(
                              fontSize: 12.5,
                              fontWeight: FontWeight.w700,
                              color: textColor,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                          if (msg.attachmentWordCount != null)
                            Text(
                              '${msg.attachmentWordCount} words · Clinical Record',
                              style: GoogleFonts.inter(
                                fontSize: 11,
                                color: subColor,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // User Chat Bubble
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Flexible(
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: isDark
                          ? const Color(0xFF2C3242)
                          : const Color(0xFF4A2DD4),
                      borderRadius: const BorderRadius.only(
                        topLeft: Radius.circular(16),
                        topRight: Radius.circular(4),
                        bottomLeft: Radius.circular(16),
                        bottomRight: Radius.circular(16),
                      ),
                    ),
                    child: Text(
                      msg.text,
                      style: GoogleFonts.inter(
                        fontSize: 13.5,
                        color: Colors.white,
                        height: 1.45,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                CircleAvatar(
                  radius: 14,
                  backgroundColor: isDark
                      ? const Color(0xFF374151)
                      : const Color(0xFF6C4DF6),
                  child: const Icon(Icons.person_rounded,
                      size: 16, color: Colors.white),
                ),
              ],
            ),
          ],
        ),
      );
    }

    // ── Assistant Message ──
    return Padding(
      padding: const EdgeInsets.only(bottom: 22),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Claude-style Assistant Logo
          Container(
            width: 28,
            height: 28,
            margin: const EdgeInsets.only(top: 2),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.health_and_safety_rounded,
                size: 16, color: Colors.white),
          ),
          const SizedBox(width: 12),

          // Content Column
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Collapsible Claude-style Thinking / Clinical Analysis pill
                if (msg.thoughtSummary != null) ...[
                  _buildThoughtDropdown(msg.thoughtSummary!, isDark, subColor),
                  const SizedBox(height: 8),
                ],

                // Markdown response text
                MarkdownBody(
                  data: msg.text,
                  selectable: true,
                  styleSheet: MarkdownStyleSheet(
                    p: GoogleFonts.inter(
                      fontSize: 13.5,
                      color: textColor,
                      height: 1.6,
                    ),
                    strong: GoogleFonts.inter(
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700,
                      color: textColor,
                    ),
                    h1: GoogleFonts.inter(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      color: const Color(0xFF6C4DF6),
                      height: 1.5,
                    ),
                    h2: GoogleFonts.inter(
                      fontSize: 14.5,
                      fontWeight: FontWeight.w700,
                      color: textColor,
                      height: 1.5,
                    ),
                    listBullet: GoogleFonts.inter(
                      fontSize: 13.5,
                      color: const Color(0xFF6C4DF6),
                    ),
                  ),
                ),

                // Embedded Interactive Artifact Pills (if linked to artifacts)
                if (msg.hasArtifacts) ...[
                  const SizedBox(height: 12),
                  ..._artifacts
                      .where((art) => msg.artifactIds.contains(art.id))
                      .map((art) {
                    final isCurrentOpen = _isArtifactPanelOpen &&
                        _artifacts.indexOf(art) == _selectedArtifactIndex;
                    return ArtifactCardPill(
                      artifact: art,
                      isPanelOpen: isCurrentOpen,
                      onTap: () {
                        final idx = _artifacts.indexOf(art);
                        _toggleArtifactPanel(idx != -1 ? idx : 0);
                      },
                    );
                  }),
                ],

                // Message Action Bar (Copy, Share)
                const SizedBox(height: 8),
                Row(
                  children: [
                    InkWell(
                      onTap: () async {
                        await Clipboard.setData(ClipboardData(text: msg.text));
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Message copied ✓'),
                              duration: Duration(seconds: 1),
                              behavior: SnackBarBehavior.floating,
                            ),
                          );
                        }
                      },
                      child: Padding(
                        padding: const EdgeInsets.all(4),
                        child: Icon(Icons.copy_rounded,
                            size: 14, color: subColor.withValues(alpha: 0.6)),
                      ),
                    ),
                    const SizedBox(width: 8),
                    if (_artifacts.isNotEmpty && !msg.hasArtifacts) ...[
                      InkWell(
                        onTap: () => _toggleArtifactPanel(),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 4),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.view_sidebar_rounded,
                                  size: 13,
                                  color: Color(0xFF6C4DF6)),
                              const SizedBox(width: 4),
                              Text(
                                'View Artifacts',
                                style: GoogleFonts.inter(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: const Color(0xFF6C4DF6),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      InkWell(
                        onTap: () => _pinMessageAsCarePlan(msg.text),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 4),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.bookmark_add_outlined,
                                  size: 13,
                                  color: Color(0xFF0EA5E9)),
                              const SizedBox(width: 4),
                              Text(
                                'Pin to Care Plan',
                                style: GoogleFonts.inter(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: const Color(0xFF0EA5E9),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ── CLAUDE-STYLE THOUGHT DROPDOWN ───────────────────────────────────────────
  Widget _buildThoughtDropdown(String summary, bool isDark, Color subColor) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF191E2A) : const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isDark ? const Color(0xFF283042) : const Color(0xFFE2E8F0),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.psychology_rounded,
              size: 14, color: Color(0xFF6C4DF6)),
          const SizedBox(width: 6),
          Flexible(
            child: Text(
              summary,
              style: GoogleFonts.jetBrainsMono(
                fontSize: 11,
                color: subColor,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  // ── THINKING INDICATOR ──────────────────────────────────────────────────────
  Widget _buildThinkingIndicator(bool isDark, Color subColor) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
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
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.health_and_safety_rounded,
                size: 16, color: Colors.white),
          ),
          const SizedBox(width: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF1A1F2C) : const Color(0xFFF3F4F6),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _currentThinkingStatus ?? 'Thinking…',
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: const Color(0xFF6C4DF6),
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(width: 8),
                ...List.generate(
                  3,
                  (i) => Container(
                    margin: const EdgeInsets.symmetric(horizontal: 2),
                    width: 4,
                    height: 4,
                    decoration: BoxDecoration(
                      color: const Color(0xFF6C4DF6),
                      borderRadius: BorderRadius.circular(2),
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

  // ── SAMPLE CASES CARDS (CLAUDE-STYLE STARTING PROMPTS) ─────────────────────
  Widget _buildSampleCasesSection(
      bool isDark, Color textColor, Color subColor) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24, top: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 8,
            runSpacing: 6,
            children: [
              Text(
                'QUICK START · CLINICAL CASES',
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: subColor,
                  letterSpacing: 0.6,
                ),
              ),
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: [
                  TextButton.icon(
                    onPressed: _pickAndUploadDischargeSummary,
                    icon: const Icon(Icons.upload_file_rounded, size: 14),
                    label: const Text('Upload Discharge Summaries'),
                    style: TextButton.styleFrom(
                      padding:
                          const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      minimumSize: Size.zero,
                      textStyle: GoogleFonts.inter(fontSize: 11.5),
                    ),
                  ),
                  TextButton.icon(
                    onPressed: _showPasteSummaryModal,
                    icon: const Icon(Icons.paste_rounded, size: 14),
                    label: const Text('Paste Custom Summary'),
                    style: TextButton.styleFrom(
                      padding:
                          const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      minimumSize: Size.zero,
                      textStyle: GoogleFonts.inter(fontSize: 11.5),
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 8),
          LayoutBuilder(builder: (context, constraints) {
            final isNarrow = constraints.maxWidth < 600;
            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: isNarrow ? 1 : 3,
                crossAxisSpacing: 10,
                mainAxisSpacing: 10,
                childAspectRatio: isNarrow ? 3.6 : 1.35,
              ),
              itemCount: _sampleCases.length,
              itemBuilder: (context, index) {
                final sc = _sampleCases[index];
                return Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: _isSending
                        ? null
                        : () => _processDischargeSummary(sc.text,
                            customTitle: sc.title),
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: isDark
                            ? const Color(0xFF191E2A)
                            : const Color(0xFFF8F9FA),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: isDark
                              ? const Color(0xFF2B3346)
                              : const Color(0xFFE2E8F0),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(6),
                                decoration: BoxDecoration(
                                  color: sc.color.withValues(alpha: 0.12),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Icon(sc.icon, size: 16, color: sc.color),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  sc.title,
                                  style: GoogleFonts.inter(
                                    fontSize: 12.5,
                                    fontWeight: FontWeight.w700,
                                    color: textColor,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            sc.snippet,
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              color: subColor,
                              height: 1.3,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            );
          }),
        ],
      ),
    );
  }

  // ── DOCKED CLAUDE-STYLE BOTTOM INPUT DOCK ──────────────────────────────────
  Widget _buildBottomInputDock(
    bool isDark,
    Color textColor,
    Color subColor,
    Color borderColor,
    Color surfaceColor,
  ) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      decoration: BoxDecoration(
        color: surfaceColor,
        border: Border(
          top: BorderSide(color: borderColor, width: 1),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Input pill container
          Container(
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF0F131C) : const Color(0xFFF9FAFB),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: borderColor),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: isDark ? 0.2 : 0.04),
                  blurRadius: 10,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                // Plus (+) Button with menu for Upload/Paste
                PopupMenuButton<String>(
                  tooltip: 'Add attachment or case',
                  icon: Container(
                    width: 28,
                    height: 28,
                    decoration: BoxDecoration(
                      color: isDark
                          ? const Color(0xFF1F2432)
                          : const Color(0xFFEDE9FE),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.add_rounded,
                        size: 18, color: Color(0xFF6C4DF6)),
                  ),
                  onSelected: (action) {
                    switch (action) {
                      case 'paste':
                        _showPasteSummaryModal();
                        break;
                      case 'upload':
                        _pickAndUploadDischargeSummary();
                        break;
                    }
                  },
                  itemBuilder: (ctx) => [
                    const PopupMenuItem(
                      value: 'paste',
                      child: Row(
                        children: [
                          Icon(Icons.paste_rounded,
                              size: 18, color: Color(0xFF6C4DF6)),
                          SizedBox(width: 10),
                          Text('Paste Discharge Summary'),
                        ],
                      ),
                    ),
                    const PopupMenuItem(
                      value: 'upload',
                      child: Row(
                        children: [
                          Icon(Icons.upload_file_rounded,
                              size: 18, color: Color(0xFF10B981)),
                          SizedBox(width: 10),
                          Text('Upload Discharge Summaries'),
                        ],
                      ),
                    ),
                  ],
                ),

                // Text field
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: TextField(
                      controller: _inputController,
                      focusNode: _focusNode,
                      minLines: 1,
                      maxLines: 5,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _sendChatMessage(),
                      style: GoogleFonts.inter(
                          fontSize: 13.5, color: textColor),
                      decoration: InputDecoration(
                        isDense: true,
                        hintText: _artifacts.isEmpty
                            ? 'Ask a medical question, or paste a discharge summary…'
                            : 'Ask about medicines, recovery precautions, warning signs…',
                        hintStyle: GoogleFonts.inter(
                          fontSize: 13,
                          color: subColor.withValues(alpha: 0.6),
                        ),
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        filled: false,
                        contentPadding:
                            const EdgeInsets.symmetric(horizontal: 8),
                      ),
                    ),
                  ),
                ),

                // Interactive Model Selector in Chat Space
                Padding(
                  padding: const EdgeInsets.only(bottom: 6, right: 6),
                  child: PopupMenuButton<ApiModel>(
                    initialValue: _selectedModel,
                    onSelected: (m) => setState(() => _selectedModel = m),
                    tooltip: 'Select AI Model',
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 5),
                      decoration: BoxDecoration(
                        color: isDark
                            ? const Color(0xFF1E2330)
                            : const Color(0xFFEDE9FE),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: isDark
                              ? const Color(0xFF333C4E)
                              : const Color(0xFFDDD6FE),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            _selectedModel.providerBadge,
                            style: const TextStyle(fontSize: 11),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            _selectedModel.name.replaceAll('Google ', ''),
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: isDark
                                  ? const Color(0xFFA78BFA)
                                  : const Color(0xFF4A2DD4),
                            ),
                          ),
                          const SizedBox(width: 2),
                          Icon(
                            Icons.arrow_drop_down_rounded,
                            size: 16,
                            color: isDark
                                ? const Color(0xFFA78BFA)
                                : const Color(0xFF4A2DD4),
                          ),
                        ],
                      ),
                    ),
                    itemBuilder: (ctx) {
                      return ApiModel.all.map((m) {
                        final isSelected = m.id == _selectedModel.id;
                        return PopupMenuItem<ApiModel>(
                          value: m,
                          child: Row(
                            children: [
                              Text(m.providerBadge),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(
                                      m.name,
                                      style: GoogleFonts.inter(
                                        fontSize: 12.5,
                                        fontWeight: isSelected
                                            ? FontWeight.w700
                                            : FontWeight.w500,
                                      ),
                                    ),
                                    Text(
                                      '${m.providerLabel} · ${m.description}',
                                      style: GoogleFonts.inter(
                                        fontSize: 10,
                                        color: subColor,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              if (isSelected)
                                const Icon(Icons.check_rounded,
                                    size: 16, color: Color(0xFF6C4DF6)),
                            ],
                          ),
                        );
                      }).toList();
                    },
                  ),
                ),

                // Send button
                Padding(
                  padding: const EdgeInsets.only(bottom: 6, right: 8),
                  child: IconButton.filled(
                    onPressed: _isSending ? null : () => _sendChatMessage(),
                    icon: _isSending
                        ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Icon(Icons.arrow_upward_rounded, size: 18),
                    style: IconButton.styleFrom(
                      backgroundColor: const Color(0xFF6C4DF6),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(8),
                      minimumSize: const Size(34, 34),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 6),

          // Medical disclaimer note
          Text(
            'MedSimplify is an AI research prototype for educational use. Always verify with your doctor.',
            style: GoogleFonts.inter(
              fontSize: 10.5,
              color: subColor.withValues(alpha: 0.65),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
