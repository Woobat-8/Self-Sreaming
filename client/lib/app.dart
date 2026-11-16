import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'data/auth_store.dart';
import 'ui/home_shell.dart';
import 'ui/login_screen.dart';

class HouseholdApp extends StatelessWidget {
  const HouseholdApp({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthStore>();
    return MaterialApp(
      title: 'Household Media',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF3D5A80),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
        inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder()),
      ),
      home: !auth.loaded
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : auth.isLoggedIn
              ? const HomeShell()
              : const LoginScreen(),
    );
  }
}
