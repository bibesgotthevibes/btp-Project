import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../screens/history_screen.dart';
import '../screens/settings_screen.dart';

class AppDrawer extends StatelessWidget {
  final bool isDark;
  final VoidCallback onToggleTheme;

  const AppDrawer({
    super.key,
    required this.isDark,
    required this.onToggleTheme,
  });

  @override
  Widget build(BuildContext context) {
    final bgColor = isDark ? const Color(0xFF161B22) : Colors.white;
    final textColor =
        isDark ? const Color(0xFFE6EDF3) : const Color(0xFF1A1A2E);
    final subColor =
        isDark ? const Color(0xFF8B949E) : const Color(0xFF6B7280);

    return Drawer(
      backgroundColor: bgColor,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header ────────────────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF6C4DF6), Color(0xFF9B7FFF)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(Icons.medical_services_rounded,
                        color: Colors.white, size: 24),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'MedSimplify',
                        style: GoogleFonts.inter(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: textColor,
                        ),
                      ),
                      Text(
                        'Lite',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          color: const Color(0xFF6C4DF6),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            Divider(
                color: isDark
                    ? const Color(0xFF30363D)
                    : const Color(0xFFE5E7EB)),
            const SizedBox(height: 8),
            // ── Nav items ─────────────────────────────────────────────────────
            _DrawerItem(
              icon: Icons.home_rounded,
              label: 'Simplifier',
              isDark: isDark,
              onTap: () => Navigator.pop(context),
            ),
            _DrawerItem(
              icon: Icons.history_rounded,
              label: 'History',
              isDark: isDark,
              onTap: () {
                Navigator.pop(context);
                Navigator.push(context,
                    MaterialPageRoute(builder: (_) => const HistoryScreen()));
              },
            ),
            _DrawerItem(
              icon: Icons.settings_rounded,
              label: 'Settings',
              isDark: isDark,
              onTap: () {
                Navigator.pop(context);
                Navigator.push(context,
                    MaterialPageRoute(builder: (_) => const SettingsScreen()));
              },
            ),
            const Spacer(),
            Divider(
                color: isDark
                    ? const Color(0xFF30363D)
                    : const Color(0xFFE5E7EB)),
            // ── Theme toggle ──────────────────────────────────────────────────
            Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  Icon(
                    isDark ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
                    color: subColor,
                    size: 20,
                  ),
                  const SizedBox(width: 12),
                  Text(
                    isDark ? 'Light mode' : 'Dark mode',
                    style: GoogleFonts.inter(
                        fontSize: 14, color: subColor),
                  ),
                  const Spacer(),
                  Switch(
                    value: isDark,
                    onChanged: (_) => onToggleTheme(),
                    activeThumbColor: const Color(0xFF6C4DF6),
                  ),
                ],
              ),
            ),
            // ── Version ───────────────────────────────────────────────────────
            Padding(
              padding:
                  const EdgeInsets.only(left: 16, right: 16, bottom: 16),
              child: Text(
                'MedSimplify Lite v1.0.0 · Research use only',
                style:
                    GoogleFonts.inter(fontSize: 11, color: subColor),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DrawerItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isDark;
  final VoidCallback onTap;

  const _DrawerItem({
    required this.icon,
    required this.label,
    required this.isDark,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final textColor =
        isDark ? const Color(0xFFE6EDF3) : const Color(0xFF1A1A2E);

    return ListTile(
      leading: Icon(icon, color: const Color(0xFF6C4DF6), size: 22),
      title: Text(
        label,
        style: GoogleFonts.inter(
            fontSize: 14, fontWeight: FontWeight.w500, color: textColor),
      ),
      onTap: onTap,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      contentPadding:
          const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
    );
  }
}
