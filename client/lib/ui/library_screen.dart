import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../data/api_client.dart';
import '../data/media_models.dart';
import '../data/media_repository.dart';
import '../download/download_controller.dart';
import 'detail_screen.dart';

class LibraryScreen extends StatefulWidget {
  const LibraryScreen({super.key});

  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  String? _filter;
  bool _loading = true;
  bool _offline = false;
  String? _error;
  List<MediaItem> _items = [];

  @override
  void initState() {
    super.initState();
    _reload();
  }

  Future<void> _reload() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final snapshot = await context.read<MediaRepository>().loadLibrary(type: _filter);
      if (!mounted) return;
      setState(() {
        _items = snapshot.items;
        _offline = snapshot.offline;
        _loading = false;
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final downloads = context.watch<DownloadController>();
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
          child: Wrap(
            spacing: 8,
            children: [
              ChoiceChip(
                label: const Text('All'),
                selected: _filter == null,
                onSelected: (_) {
                  setState(() => _filter = null);
                  _reload();
                },
              ),
              ChoiceChip(
                label: const Text('Videos'),
                selected: _filter == 'video',
                onSelected: (_) {
                  setState(() => _filter = 'video');
                  _reload();
                },
              ),
              ChoiceChip(
                label: const Text('Images'),
                selected: _filter == 'image',
                onSelected: (_) {
                  setState(() => _filter = 'image');
                  _reload();
                },
              ),
            ],
          ),
        ),
        if (_offline)
          MaterialBanner(
            content: const Text('Server unreachable. Showing downloaded items only.'),
            actions: [
              TextButton(onPressed: _reload, child: const Text('Retry')),
            ],
          ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ),
        Expanded(
          child: RefreshIndicator(
            onRefresh: _reload,
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _items.isEmpty
                    ? ListView(
                        children: const [
                          SizedBox(height: 80),
                          Center(child: Text('No media yet.')),
                        ],
                      )
                    : GridView.builder(
                        padding: const EdgeInsets.all(12),
                        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 3,
                          mainAxisSpacing: 8,
                          crossAxisSpacing: 8,
                          childAspectRatio: 0.72,
                        ),
                        itemCount: _items.length,
                        itemBuilder: (context, index) {
                          final item = _items[index];
                          return _LibraryTile(
                            item: item,
                            downloaded: downloads.isDownloaded(item.id),
                            onTap: () async {
                              await Navigator.of(context).push(
                                MaterialPageRoute<void>(
                                  builder: (_) => DetailScreen(item: item, offline: _offline),
                                ),
                              );
                              if (mounted) setState(() {});
                            },
                          );
                        },
                      ),
          ),
        ),
      ],
    );
  }
}

class _LibraryTile extends StatelessWidget {
  const _LibraryTile({
    required this.item,
    required this.downloaded,
    required this.onTap,
  });

  final MediaItem item;
  final bool downloaded;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final thumb = item.urls?.thumbnail;
    return InkWell(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  ColoredBox(
                    color: Theme.of(context).colorScheme.surfaceContainerHighest,
                    child: thumb == null
                        ? Icon(item.isVideo ? Icons.movie : Icons.image, size: 36)
                        : CachedNetworkImage(
                            imageUrl: thumb,
                            fit: BoxFit.cover,
                            errorWidget: (_, _, _) =>
                                Icon(item.isVideo ? Icons.movie : Icons.image),
                          ),
                  ),
                  if (downloaded)
                    const Align(
                      alignment: Alignment.topRight,
                      child: Padding(
                        padding: EdgeInsets.all(4),
                        child: Icon(Icons.download_done, size: 18, color: Colors.white),
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            item.filename,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
