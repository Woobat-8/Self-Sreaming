import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/auth_store.dart';
import 'downloads_screen.dart';
import 'library_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_index == 0 ? 'Library' : 'Downloads'),
        actions: [
          IconButton(
            tooltip: 'Sign out',
            onPressed: () => context.read<AuthStore>().logoutRemote(),
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: IndexedStack(
        index: _index,
        children: const [
          LibraryScreen(),
          DownloadsScreen(),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (value) => setState(() => _index = value),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.video_library_outlined), label: 'Library'),
          NavigationDestination(icon: Icon(Icons.download_outlined), label: 'Downloads'),
        ],
      ),
    );
  }
}
