import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:btp_lite/main.dart';
import 'package:btp_lite/services/storage_service.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    final storage = await StorageService.create();
    await tester.pumpWidget(
      Provider<StorageService>.value(
        value: storage,
        child: const MedSimplifyApp(),
      ),
    );
    expect(find.text('MedSimplify'), findsOneWidget);
  });
}
