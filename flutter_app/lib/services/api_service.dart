import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/engine_status.dart';

/// REST + WebSocket client for reshala-v2 API.
class ApiService {
  final String baseUrl;
  final String wsUrl;
  WebSocketChannel? _channel;
  final _statusController = StreamController<EngineStatus>.broadcast();

  Stream<EngineStatus> get statusStream => _statusController.stream;

  ApiService({this.baseUrl = 'http://10.0.2.2:8420', this.wsUrl = 'ws://10.0.2.2:8420'});

  /// Fetch current status via REST.
  Future<EngineStatus> fetchStatus() async {
    // In real app: use http package
    // final response = await http.get(Uri.parse('$baseUrl/api/status'));
    // return EngineStatus.fromJson(jsonDecode(response.body));
    throw UnimplementedError('Add http package and implement');
  }

  /// Send command to engine (pause, resume, close).
  Future<bool> sendCommand(String command, {String symbol = '', Map<String, dynamic> params = const {}}) async {
    // final response = await http.post(
    //   Uri.parse('$baseUrl/api/command'),
    //   body: jsonEncode({'command': command, 'symbol': symbol, 'params': params}),
    // );
    // return response.statusCode == 200;
    throw UnimplementedError('Add http package and implement');
  }

  /// Connect to real-time WebSocket stream.
  void connectWebSocket() {
    _channel = WebSocketChannel.connect(Uri.parse('$wsUrl/api/ws'));
    _channel!.stream.listen(
      (data) {
        final msg = jsonDecode(data as String);
        if (msg['type'] == 'snapshot' || msg['type'] == 'update') {
          final status = EngineStatus.fromJson(msg['data'] as Map<String, dynamic>);
          _statusController.add(status);
        }
      },
      onError: (error) {
        // Reconnect after delay
        Future.delayed(const Duration(seconds: 5), connectWebSocket);
      },
    );
  }

  void disconnect() {
    _channel?.sink.close();
    _channel = null;
  }
}

/// Riverpod provider for ApiService singleton.
final apiServiceProvider = Provider<ApiService>((ref) {
  return ApiService();
});

/// Stream provider for real-time engine status.
final engineStatusProvider = StreamProvider<EngineStatus>((ref) {
  final api = ref.watch(apiServiceProvider);
  return api.statusStream;
});
