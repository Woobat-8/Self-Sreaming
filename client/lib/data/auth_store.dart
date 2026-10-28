import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'format.dart';

class AuthStore extends ChangeNotifier {
  AuthStore({FlutterSecureStorage? storage, Dio? dio})
        : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
            ),
        _plainDio = dio ??
            Dio(
              BaseOptions(
                connectTimeout: const Duration(seconds: 15),
                receiveTimeout: const Duration(seconds: 15),
              ),
            );

  static const _kBaseUrl = 'base_url';
  static const _kAccess = 'access_token';
  static const _kRefresh = 'refresh_token';

  final FlutterSecureStorage _storage;
  final Dio _plainDio;

  String? baseUrl;
  String? accessToken;
  String? refreshToken;
  bool loaded = false;

  Future<void>? _refreshInFlight;

  bool get isLoggedIn =>
      (baseUrl != null && baseUrl!.isNotEmpty) &&
      (accessToken != null && accessToken!.isNotEmpty);

  String get normalizedBaseUrl => normalizeBaseUrl(baseUrl ?? '');

  Future<void> load() async {
    baseUrl = await _storage.read(key: _kBaseUrl);
    accessToken = await _storage.read(key: _kAccess);
    refreshToken = await _storage.read(key: _kRefresh);
    loaded = true;
    notifyListeners();
  }

  Future<void> saveSession({
    required String url,
    required String access,
    required String refresh,
  }) async {
    baseUrl = normalizeBaseUrl(url);
    accessToken = access;
    refreshToken = refresh;
    await _storage.write(key: _kBaseUrl, value: baseUrl);
    await _storage.write(key: _kAccess, value: access);
    await _storage.write(key: _kRefresh, value: refresh);
    notifyListeners();
  }

  Future<void> clearSession() async {
    accessToken = null;
    refreshToken = null;
    await _storage.delete(key: _kAccess);
    await _storage.delete(key: _kRefresh);
    notifyListeners();
  }

  Future<void> logoutRemote() async {
    final url = baseUrl;
    final refresh = refreshToken;
    if (url != null && refresh != null) {
      try {
        await _plainDio.post<void>(
          '${normalizeBaseUrl(url)}/api/v1/auth/logout',
          data: {'refresh_token': refresh},
        );
      } catch (_) {
        // Local session is still cleared below.
      }
    }
    await clearSession();
  }

  Future<bool> refreshAccessToken() async {
    final existing = _refreshInFlight;
    if (existing != null) {
      try {
        await existing;
        return accessToken != null;
      } catch (_) {
        return false;
      }
    }
    final future = _refreshOnce();
    _refreshInFlight = future;
    try {
      await future;
      return accessToken != null;
    } catch (_) {
      return false;
    } finally {
      _refreshInFlight = null;
    }
  }

  Future<void> _refreshOnce() async {
    final url = baseUrl;
    final refresh = refreshToken;
    if (url == null || refresh == null) {
      await clearSession();
      return;
    }
    try {
      final response = await _plainDio.post<Map<String, dynamic>>(
        '${normalizeBaseUrl(url)}/api/v1/auth/refresh',
        data: {'refresh_token': refresh},
      );
      final data = response.data ?? {};
      await saveSession(
        url: url,
        access: data['access_token'] as String,
        refresh: data['refresh_token'] as String,
      );
    } catch (_) {
      await clearSession();
      rethrow;
    }
  }
}
