import 'dart:convert';
import 'dart:typed_data';
import 'package:syncfusion_flutter_pdf/pdf.dart';

class DocumentExtractionResult {
  final String fileName;
  final String text;
  final String extension;
  final int byteSize;

  const DocumentExtractionResult({
    required this.fileName,
    required this.text,
    required this.extension,
    required this.byteSize,
  });

  int get wordCount =>
      text.split(RegExp(r'\s+')).where((w) => w.isNotEmpty).length;
}

class DocumentReaderService {
  /// Extracts text content from file bytes based on file extension
  static DocumentExtractionResult extractFromBytes({
    required String fileName,
    required Uint8List bytes,
  }) {
    final lowerName = fileName.toLowerCase();
    String extracted = '';
    String ext = 'txt';

    if (lowerName.endsWith('.pdf')) {
      ext = 'pdf';
      try {
        final PdfDocument document = PdfDocument(inputBytes: bytes);
        extracted = PdfTextExtractor(document).extractText();
        document.dispose();
      } catch (e) {
        throw Exception('Failed to read PDF file: $e');
      }
    } else {
      // txt, md, or generic plain text
      if (lowerName.endsWith('.md')) {
        ext = 'md';
      } else {
        ext = 'txt';
      }
      extracted = utf8.decode(bytes, allowMalformed: true);
    }

    final cleanedText = extracted.trim();
    if (cleanedText.isEmpty) {
      throw Exception(
        'The selected $ext file appears to be empty or contains scanned images without selectable text.',
      );
    }

    return DocumentExtractionResult(
      fileName: fileName,
      text: cleanedText,
      extension: ext,
      byteSize: bytes.length,
    );
  }
}
