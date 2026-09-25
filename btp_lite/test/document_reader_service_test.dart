import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:btp_lite/services/document_reader_service.dart';
import 'package:syncfusion_flutter_pdf/pdf.dart';

void main() {
  group('DocumentReaderService Tests', () {
    test('Extracts text correctly from .txt bytes', () {
      const sampleText = 'Patient admitted with severe chest pain. Diagnosed with STEMI.';
      final bytes = Uint8List.fromList(utf8.encode(sampleText));

      final res = DocumentReaderService.extractFromBytes(
        fileName: 'discharge_note.txt',
        bytes: bytes,
      );

      expect(res.extension, equals('txt'));
      expect(res.text, equals(sampleText));
      expect(res.wordCount, equals(9));
    });

    test('Extracts text correctly from .pdf bytes', () {
      // Create a small PDF in memory
      final doc = PdfDocument();
      final page = doc.pages.add();
      page.graphics.drawString(
        'Hospital Discharge Summary: Patient discharged in stable condition.',
        PdfStandardFont(PdfFontFamily.helvetica, 12),
      );
      final List<int> pdfBytes = doc.saveSync();
      doc.dispose();

      final res = DocumentReaderService.extractFromBytes(
        fileName: 'patient_record.pdf',
        bytes: Uint8List.fromList(pdfBytes),
      );

      expect(res.extension, equals('pdf'));
      expect(res.text, contains('Hospital Discharge Summary'));
      expect(res.text, contains('stable condition'));
      expect(res.wordCount, greaterThan(5));
    });

    test('Throws informative exception on empty document', () {
      final emptyBytes = Uint8List.fromList(utf8.encode('   \n\t  '));

      expect(
        () => DocumentReaderService.extractFromBytes(
          fileName: 'empty.txt',
          bytes: emptyBytes,
        ),
        throwsA(isA<Exception>()),
      );
    });
  });
}
