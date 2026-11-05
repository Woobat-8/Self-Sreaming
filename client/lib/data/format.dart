String normalizeBaseUrl(String raw) {
  var url = raw.trim();
  if (url.endsWith('/')) {
    url = url.substring(0, url.length - 1);
  }
  return url;
}

bool looksLikeHttpUrl(String raw) {
  final uri = Uri.tryParse(raw.trim());
  return uri != null &&
      uri.hasScheme &&
      (uri.scheme == 'http' || uri.scheme == 'https') &&
      uri.host.isNotEmpty;
}

String formatBytes(int bytes) {
  if (bytes < 1024) return '$bytes B';
  const units = ['KB', 'MB', 'GB', 'TB'];
  var value = bytes.toDouble();
  var unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit++;
  }
  final digits = value >= 10 || unit == 0 ? 0 : 1;
  return '${value.toStringAsFixed(digits)} ${units[unit]}';
}

String formatDuration(double? seconds) {
  if (seconds == null || seconds.isNaN || seconds < 0) return '';
  final total = seconds.round();
  final h = total ~/ 3600;
  final m = (total % 3600) ~/ 60;
  final s = total % 60;
  if (h > 0) {
    return '$h:${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }
  return '$m:${s.toString().padLeft(2, '0')}';
}

String extensionFor(String filename, String mimeType) {
  final dot = filename.lastIndexOf('.');
  if (dot >= 0 && dot < filename.length - 1) {
    return filename.substring(dot);
  }
  if (mimeType.contains('mp4')) return '.mp4';
  if (mimeType.contains('webm')) return '.webm';
  if (mimeType.contains('png')) return '.png';
  if (mimeType.contains('webp')) return '.webp';
  if (mimeType.contains('jpeg') || mimeType.contains('jpg')) return '.jpg';
  return '';
}
