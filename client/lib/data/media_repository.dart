import 'api_client.dart';
import 'local_db.dart';
import 'media_models.dart';

class LibrarySnapshot {
  const LibrarySnapshot({required this.items, required this.offline});

  final List<MediaItem> items;
  final bool offline;
}

class MediaRepository {
  MediaRepository({required ApiClient api, required LocalDb db})
      : _api = api,
        _db = db;

  final ApiClient _api;
  final LocalDb _db;

  Future<LibrarySnapshot> loadLibrary({String? type}) async {
    try {
      final items = await _api.fetchAllLibrary(type: type);
      return LibrarySnapshot(items: items, offline: false);
    } on ApiException catch (error) {
      if (!error.offline && error.statusCode != null && error.statusCode! < 500) {
        rethrow;
      }
      final local = await _db.all();
      var items = local
          .where((row) => row.isComplete)
          .map((row) => row.item)
          .toList();
      if (type != null) {
        items = items.where((item) => item.type == type).toList();
      }
      return LibrarySnapshot(items: items, offline: true);
    }
  }
}
