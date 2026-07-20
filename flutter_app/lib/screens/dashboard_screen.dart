import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../models/engine_status.dart';
import 'position_detail_screen.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(apiServiceProvider).connectWebSocket();
    });
  }

  @override
  void dispose() {
    ref.read(apiServiceProvider).disconnect();
    super.dispose();
  }

  void _sendCommand(String command, {String symbol = ''}) {
    ref.read(apiServiceProvider).sendCommand(command, symbol: symbol);
  }

  @override
  Widget build(BuildContext context) {
    final statusAsync = ref.watch(engineStatusProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Reshala v2'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(engineStatusProvider),
          ),
        ],
      ),
      body: statusAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text('Connection error: $err')),
        data: (status) => _buildDashboard(context, status),
      ),
    );
  }

  Widget _buildDashboard(BuildContext context, EngineStatus status) {
    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(engineStatusProvider),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _BalanceCard(status: status),
          const SizedBox(height: 12),
          _SupervisorBar(status: status),
          const SizedBox(height: 12),
          _RiskPanel(status: status),
          const SizedBox(height: 16),
          Text('Positions (${status.positions.length})',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          ...status.positions.map((pos) => _PositionCard(
                position: pos,
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => PositionDetailScreen(position: pos),
                  ),
                ),
                onPause: () => _sendCommand('pause', symbol: pos.symbol),
                onClose: () => _sendCommand('close', symbol: pos.symbol),
              )),
        ],
      ),
    );
  }
}

class _BalanceCard extends StatelessWidget {
  final EngineStatus status;
  const _BalanceCard({required this.status});

  @override
  Widget build(BuildContext context) {
    final wallet = status.balance['wallet'] ?? 0.0;
    final available = status.balance['available'] ?? 0.0;
    final margin = status.balance['margin'] ?? 0.0;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _BalanceItem('Wallet', wallet),
            _BalanceItem('Available', available),
            _BalanceItem('Margin', margin),
          ],
        ),
      ),
    );
  }

  Widget _BalanceItem(String label, double value) => Column(
        children: [
          Text(label, style: Theme.of(context).textTheme.labelSmall),
          const SizedBox(height: 4),
          Text('\$${value.toStringAsFixed(0)}',
              style: Theme.of(context).textTheme.headlineSmall),
        ],
      );
}

class _SupervisorBar extends StatelessWidget {
  final EngineStatus status;
  const _SupervisorBar({required this.status});

  Color get _color => switch (status.supervisorState) {
        'HEALTHY' => Colors.green,
        'RISK_LIMITED' => Colors.orange,
        'DEGRADED' => Colors.yellow,
        'CRITICAL' => Colors.red,
        _ => Colors.grey,
      };

  @override
  Widget build(BuildContext context) => Chip(
        avatar: Icon(Icons.circle, color: _color, size: 12),
        label: Text(status.supervisorState),
        backgroundColor: _color.withOpacity(0.15),
      );
}

class _RiskPanel extends StatelessWidget {
  final EngineStatus status;
  const _RiskPanel({required this.status});

  @override
  Widget build(BuildContext context) {
    final risk = status.risk;
    return Card(
      color: risk.circuitOpen ? Colors.red.withOpacity(0.15) : null,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Daily Loss: \$${risk.dailyLoss.toStringAsFixed(2)}'),
            if (risk.circuitOpen)
              const Text('⚠️ CIRCUIT BREAKER OPEN',
                  style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
            if (risk.dcaCounts.isNotEmpty)
              Text('DCA: ${risk.dcaCounts.entries.map((e) => '${e.key}: ${e.value}').join(', ')}'),
          ],
        ),
      ),
    );
  }
}

class _PositionCard extends StatelessWidget {
  final PositionInfo position;
  final VoidCallback onTap;
  final VoidCallback onPause;
  final VoidCallback onClose;

  const _PositionCard({
    required this.position,
    required this.onTap,
    required this.onPause,
    required this.onClose,
  });

  Color get _stateColor => switch (position.state) {
        'active' || 'monitoring' => Colors.green,
        'preparing' || 'sending_order' || 'verify' || 'wait_fill' => Colors.blue,
        'waiting' => Colors.orange,
        'error' || 'paused_manual' || 'paused_risk' => Colors.red,
        _ => Colors.grey,
      };

  @override
  Widget build(BuildContext context) {
    final pnl = position.unrealisedPnl;
    final pnlColor = pnl < 0 ? Colors.red : Colors.green;

    return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _stateColor,
          child: Text(position.state[0].toUpperCase()),
        ),
        title: Text('${position.symbol} ${position.side}'),
        subtitle: Text(position.substate ?? ''),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text('\$${pnl.toStringAsFixed(2)}',
                style: TextStyle(color: pnlColor, fontWeight: FontWeight.bold)),
            Text('${position.roePercent.toStringAsFixed(1)}%',
                style: TextStyle(color: pnlColor, fontSize: 12)),
          ],
        ),
        onTap: onTap,
      ),
    );
  }
}
