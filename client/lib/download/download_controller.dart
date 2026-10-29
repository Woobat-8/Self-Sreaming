import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../data/api_client.dart';
import '../data/format.dart';
import '../data/local_db.dart';
import '../data/media_models.dart';

class DownloadController extends ChangeNotifier {
  DownloadController({required LocalDb db, required ApiClient api})
      : _db = db,
        _api = api,
        _http = Dio(
          BaseOptions(
            connectTimeout: const Duration(seconds: 20),
            receiveTimeout: const Duration(hours: 2),
            followRedirects: true,
          ),
        );

  final LocalDb _db;
  final ApiClient _api;
  final Dio _http;
  final Map<String, DownloadRecord> _records = {};
  final Map<String, CancelToken> _cancels = {};
  String? _activeId;

  List<DownloadRecord> get records =>
      _records.values.toList()..sort((a, b) => a.item.filename.compareTo(b.item.filename));

  bool get hasActive => _activeId != null;

  Future<void> load() async {
    final rows = await _db.all();
    _records
      ..clear()
      ..addEntries(rows.map((row) => MapEntry(row.item.id, row)));
    for (final record in _records.values) {
      if (record.status == DownloadStatus.downloading || record.status == DownloadStatus.queued) {
        record.status = DownloadStatus.failed;
        record.error = 'Interrupted';
        await _db.upsert(record);
      }
    }
    notifyListeners();
  }

  DownloadRecord? recordFor(String id) => _records[id];

  bool isDownloaded(String id) => _records[id]?.isComplete == true;

  Future<int> storageUsedBytes() async {
    var total = 0;
    for (final record in _records.values) {
      if (!record.isComplete || record.localPath == null) continue;
      final file = File(record.localPath!);
      if (await file.exists()) {
        total += await file.length();
      }
    }
    return total;
  }

  Future<void> start(MediaItem item) async {
    if (_activeId != null && _activeId != item.id) {
      throw ApiException('A download is already in progress');
    }
    final existing = _records[item.id];
    if (existing?.isComplete == true) return;
    if (_activeId == item.id) return;

    final dest = await _destinationFor(item);
    final record = DownloadRecord(
      item: item,
      status: DownloadStatus.downloading,
      localPath: dest.path,
      receivedBytes: 0,
    );
    _records[item.id] = record;
    _activeId = item.id;
    await _db.upsert(record);
    notifyListeners();

    final token = CancelToken();
    _cancels[item.id] = token;

    try {
      var fresh = item;
      if (fresh.urls == null) {
        fresh = await _api.fetchMedia(item.id);
      }
      await _downloadTo(fresh, dest, token, record);
      record.status = DownloadStatus.completed;
      record.error = null;
      record.item = fresh.copyWith(urls: null);
      await _db.upsert(record);
    } on DioException catch (error) {
      if (token.isCancelled) {
        record.status = DownloadStatus.canceled;
        record.error = 'Canceled';
      } else if (error.response?.statusCode == 401) {
        try {
          final fresh = await _api.fetchMedia(item.id);
          await _downloadTo(fresh, dest, token, record);
          record.status = DownloadStatus.completed;
          record.error = null;
          await _db.upsert(record);
        } catch (retryError) {
          record.status = DownloadStatus.failed;
          record.error = retryError.toString();
        }
      } else {
        record.status = DownloadStatus.failed;
        record.error = error.message ?? 'Download failed';
      }
      await _db.upsert(record);
    } catch (error) {
      record.status = DownloadStatus.failed;
      record.error = error.toString();
      await _db.upsert(record);
    } finally {
      _cancels.remove(item.id);
      if (_activeId == item.id) _activeId = null;
      notifyListeners();
    }
  }

  Future<void> _downloadTo(
    MediaItem item,
    File dest,
    CancelToken token,
    DownloadRecord record,
  ) async {
    final url = item.urls?.download;
    if (url == null) {
      throw ApiException('Missing download URL');
    }
    await dest.parent.create(recursive: true);
    await _http.download(
      url,
      dest.path,
      cancelToken: token,
      deleteOnError: true,
      onReceiveProgress: (received, total) {
        record.receivedBytes = received;
        notifyListeners();
        unawaited(_db.upsert(record));
      },
    );
    record.receivedBytes = await dest.length();
    record.localPath = dest.path;
  }

  Future<void> cancel(String id) async {
    _cancels[id]?.cancel('canceled');
  }

  Future<void> retry(String id) async {
    final record = _records[id];
    if (record == null) return;
    await start(record.item);
  }

  Future<void> deleteLocal(String id) async {
    await cancel(id);
    final record = _records.remove(id);
    if (record?.localPath != null) {
      final file = File(record!.localPath!);
      if (await file.exists()) {
        await file.delete();
      }
    }
    await _db.delete(id);
    notifyListeners();
  }

  Future<File> _destinationFor(MediaItem item) async {
    final root = await getApplicationDocumentsDirectory();
    final dir = Directory(p.join(root.path, 'downloads'));
    await dir.create(recursive: true);
    final ext = extensionFor(item.filename, item.mimeType);
    return File(p.join(dir.path, '${item.id}$ext'));
  }
}
