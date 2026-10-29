import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/format.dart';
import '../data/media_models.dart';
import '../download/download_controller.dart';
import 'detail_screen.dart';

class DownloadsScreen extends StatelessWidget {
  const DownloadsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final downloads = context.watch<DownloadController>();
    final records = downloads.records;

    return FutureBuilder<int>(
      future: downloads.storageUsedBytes(),
      builder: (context, snapshot) {
        final used = snapshot.data ?? 0;
        return Column(
          children: [
            ListTile(
              title: const Text('Storage used'),
              subtitle: Text(formatBytes(used)),
            ),
            const Divider(height: 1),
            Expanded(
              child: records.isEmpty
                  ? const Center(child: Text('No downloads yet.'))
                  : ListView.separated(
                      itemCount: records.length,
                      separatorBuilder: (_, _) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final record = records[index];
                        return ListTile(
                          leading: Icon(record.item.isVideo ? Icons.movie : Icons.image),
                          title: Text(record.item.filename),
                          subtitle: Text(_subtitle(record)),
                          onTap: () {
                            Navigator.of(context).push(
                              MaterialPageRoute<void>(
                                builder: (_) => DetailScreen(
                                  item: record.item,
                                  offline: record.isComplete,
                                ),
                              ),
                            );
                          },
                          trailing: Wrap(
                            spacing: 4,
                            children: [
                              if (record.status == DownloadStatus.downloading)
                                IconButton(
                                  tooltip: 'Cancel',
                                  onPressed: () => downloads.cancel(record.item.id),
                                  icon: const Icon(Icons.close),
                                ),
                              if (record.status == DownloadStatus.failed ||
                                  record.status == DownloadStatus.canceled)
                                IconButton(
                                  tooltip: 'Retry',
                                  onPressed: () => downloads.retry(record.item.id),
                                  icon: const Icon(Icons.refresh),
                                ),
                              IconButton(
                                tooltip: 'Delete',
                                onPressed: () => downloads.deleteLocal(record.item.id),
                                icon: const Icon(Icons.delete_outline),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
            ),
          ],
        );
      },
    );
  }

  String _subtitle(DownloadRecord record) {
    final status = switch (record.status) {
      DownloadStatus.queued => 'Queued',
      DownloadStatus.downloading =>
        '${formatBytes(record.receivedBytes)} / ${formatBytes(record.item.sizeBytes)}',
      DownloadStatus.completed => 'Downloaded · ${formatBytes(record.item.sizeBytes)}',
      DownloadStatus.failed => record.error ?? 'Failed',
      DownloadStatus.canceled => 'Canceled',
    };
    return status;
  }
}
