import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/storage_service.dart';
import 'theme/app_theme.dart';
import 'screens/home_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final storage = await StorageService.create();
  runApp(
    Provider<StorageService>.value(
      value: storage,
      child: const MedSimplifyApp(),
    ),
  );
}

class MedSimplifyApp extends StatefulWidget {
  const MedSimplifyApp({super.key});

  @override
  State<MedSimplifyApp> createState() => _MedSimplifyAppState();
}

class _MedSimplifyAppState extends State<MedSimplifyApp> {
  ThemeMode _themeMode = ThemeMode.system;

  @override
  void initState() {
    super.initState();
    _loadTheme();
  }

  Future<void> _loadTheme() async {
    final storage = context.read<StorageService>();
    final saved = storage.themeMode;
    setState(() {
      _themeMode = switch (saved) {
        'light' => ThemeMode.light,
        'dark' => ThemeMode.dark,
        _ => ThemeMode.system,
      };
    });
  }

  void _toggleTheme() {
    final storage = context.read<StorageService>();
    setState(() {
      if (_themeMode == ThemeMode.dark) {
        _themeMode = ThemeMode.light;
        storage.setThemeMode('light');
      } else {
        _themeMode = ThemeMode.dark;
        storage.setThemeMode('dark');
      }
    });
  }

  bool get _isDark {
    if (_themeMode == ThemeMode.system) {
      final brightness = WidgetsBinding
          .instance.platformDispatcher.platformBrightness;
      return brightness == Brightness.dark;
    }
    return _themeMode == ThemeMode.dark;
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MedSimplify Lite',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: _themeMode,
      home: HomeScreen(
        onToggleTheme: _toggleTheme,
        isDark: _isDark,
      ),
    );
  }
}
