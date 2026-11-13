import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/api_client.dart';
import '../data/format.dart';
import '../data/media_models.dart';
import '../download/download_controller.dart';
import 'image_viewer_screen.dart';
import 'video_player_screen.dart';

class DetailScreen extends StatefulWidget {
  const DetailScreen({super.key, required this.item, required this.offline});

  final MediaItem item;
  final bool offline;

  @override
  State<DetailScreen> createState() => _DetailScreenState();
}

class _DetailScreenState extends State<DetailScreen> {
  late MediaItem _item;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _item = widget.item;
  }

  Future<MediaItem> _fresh() async {
    if (widget.offline) return _item;
    final latest = await context.read<ApiClient>().fetchMedia(_item.id);
    setState(() => _item = latest);
    return latest;
  }

  Future<void> _playOrView() async {
    final downloads = context.read<DownloadController>();
    final local = downloads.recordFor(_item.id);
    String? filePath;
    String? networkUrl;
    if (local?.isComplete == true) {
      filePath = local!.localPath;
    } else if (!widget.offline) {
      setState(() => _busy = true);
      try {
        final fresh = await _fresh();
        networkUrl = fresh.isVideo ? fresh.urls?.stream : fresh.urls?.stream;
      } on ApiException catch (error) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
        }
        return;
      } finally {
        if (mounted) setState(() => _busy = false);
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Download this item to play offline.')),
      );
      return;
    }

    if (!mounted) return;
    if (_item.isVideo) {
      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => VideoPlayerScreen(
            title: _item.filename,
            networkUrl: networkUrl,
            filePath: filePath,
          ),
        ),
      );
    } else {
      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => ImageViewerScreen(
            title: _item.filename,
            networkUrl: networkUrl,
            filePath: filePath,
          ),
        ),
      );
    }
  }

  Future<void> _download() async {
    final downloads = context.read<DownloadController>();
    setState(() => _busy = true);
    try {
      final item = widget.offline ? _item : await _fresh();
      await downloads.start(item);
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _deleteLocal() async {
    await context.read<DownloadController>().deleteLocal(_item.id);
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final downloads = context.watch<DownloadController>();
    final record = downloads.recordFor(_item.id);
    final downloaded = record?.isComplete == true;
    final duration = formatDuration(_item.durationSeconds);

    return Scaffold(
      appBar: AppBar(title: Text(_item.filename)),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(_item.filename, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            [
              _item.isVideo ? 'Video' : 'Image',
              formatBytes(_item.sizeBytes),
              if (duration.isNotEmpty) duration,
              if (_item.width != null && _item.height != null) '${_item.width}×${_item.height}',
            ].join(' · '),
          ),
          if (record != null && record.status == DownloadStatus.downloading) ...[
            const SizedBox(height: 16),
            LinearProgressIndicator(
              value: _item.sizeBytes > 0 ? (record.receivedBytes / _item.sizeBytes).clamp(0, 1) : null,
            ),
            const SizedBox(height: 4),
            Text('${formatBytes(record.receivedBytes)} / ${formatBytes(_item.sizeBytes)}'),
          ],
          if (record?.error != null && record?.status == DownloadStatus.failed) ...[
            const SizedBox(height: 12),
            Text(record!.error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: _busy ? null : _playOrView,
            icon: Icon(_item.isVideo ? Icons.play_arrow : Icons.visibility),
            label: Text(_item.isVideo ? 'Play' : 'View'),
          ),
          const SizedBox(height: 8),
          if (!downloaded)
            OutlinedButton.icon(
              onPressed: _busy || widget.offline ? null : _download,
              icon: const Icon(Icons.download),
              label: const Text('Download'),
            )
          else
            OutlinedButton.icon(
              onPressed: _deleteLocal,
              icon: const Icon(Icons.delete_outline),
              label: const Text('Delete local copy'),
            ),
        ],
      ),
    );
  }
}
