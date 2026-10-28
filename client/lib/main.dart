import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'data/api_client.dart';
import 'data/auth_store.dart';
import 'data/local_db.dart';
import 'data/media_repository.dart';
import 'download/download_controller.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final auth = AuthStore();
  await auth.load();
  final db = await LocalDb.open();
  final api = ApiClient(auth);
  final downloads = DownloadController(db: db, api: api);
  await downloads.load();
  final repository = MediaRepository(api: api, db: db);

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: auth),
        Provider.value(value: api),
        Provider.value(value: db),
        Provider.value(value: repository),
        ChangeNotifierProvider.value(value: downloads),
      ],
      child: const HouseholdApp(),
    ),
  );
}
