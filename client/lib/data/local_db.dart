import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

import 'media_models.dart';

class LocalDb {
  LocalDb(this._db);

  final Database _db;

  static Future<LocalDb> open() async {
    final dir = await getApplicationDocumentsDirectory();
    final db = await openDatabase(
      p.join(dir.path, 'household_media.db'),
      version: 1,
      onCreate: (database, version) async {
        await database.execute('''
          CREATE TABLE downloads (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            type TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            duration_seconds REAL,
            width INTEGER,
            height INTEGER,
            local_path TEXT,
            status TEXT NOT NULL,
            received_bytes INTEGER NOT NULL DEFAULT 0,
            error TEXT
          )
        ''');
      },
    );
    return LocalDb(db);
  }

  DownloadRecord _fromRow(Map<String, Object?> row) {
    return DownloadRecord(
      item: MediaItem(
        id: row['id'] as String,
        filename: row['filename'] as String,
        type: row['type'] as String,
        mimeType: row['mime_type'] as String,
        sizeBytes: row['size_bytes'] as int,
        durationSeconds: (row['duration_seconds'] as num?)?.toDouble(),
        width: row['width'] as int?,
        height: row['height'] as int?,
      ),
      status: DownloadStatus.values.firstWhere(
        (value) => value.name == row['status'],
        orElse: () => DownloadStatus.failed,
      ),
      localPath: row['local_path'] as String?,
      receivedBytes: row['received_bytes'] as int? ?? 0,
      error: row['error'] as String?,
    );
  }

  Future<List<DownloadRecord>> all() async {
    final rows = await _db.query('downloads', orderBy: 'filename COLLATE NOCASE');
    return rows.map(_fromRow).toList();
  }

  Future<DownloadRecord?> get(String id) async {
    final rows = await _db.query('downloads', where: 'id = ?', whereArgs: [id]);
    if (rows.isEmpty) return null;
    return _fromRow(rows.first);
  }

  Future<void> upsert(DownloadRecord record) async {
    await _db.insert(
      'downloads',
      {
        'id': record.item.id,
        'filename': record.item.filename,
        'type': record.item.type,
        'mime_type': record.item.mimeType,
        'size_bytes': record.item.sizeBytes,
        'duration_seconds': record.item.durationSeconds,
        'width': record.item.width,
        'height': record.item.height,
        'local_path': record.localPath,
        'status': record.status.name,
        'received_bytes': record.receivedBytes,
        'error': record.error,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<void> delete(String id) async {
    await _db.delete('downloads', where: 'id = ?', whereArgs: [id]);
  }
}
