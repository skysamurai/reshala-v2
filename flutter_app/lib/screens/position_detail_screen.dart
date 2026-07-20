import 'package:flutter/material.dart';
import '../models/engine_status.dart';

class PositionDetailScreen extends StatelessWidget {
  final PositionInfo position;
  const PositionDetailScreen({super.key, required this.position});

  @override
  Widget build(BuildContext context) {
    final pos = position.position;
    final pnl = position.unrealisedPnl;
    final pnlColor = pnl < 0 ? Colors.red : Colors.green;

    return Scaffold(
      appBar: AppBar(title: Text('${position.symbol} ${position.side}')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // FSM State
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Text('FSM State',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  _InfoRow('State', position.state),
                  if (position.substate != null)
                    _InfoRow('Sub-state', position.substate!),
                  _InfoRow('Version', position.version.toString()),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Position Data
          if (pos != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Text('Position', style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 8),
                    _InfoRow('Size', '${pos.size}'),
                    _InfoRow('Entry', '\$${pos.avgPrice.toStringAsFixed(2)}'),
                    _InfoRow('Mark', '\$${pos.markPrice.toStringAsFixed(2)}'),
                    _InfoRow('Liq', '\$${pos.liqPrice.toStringAsFixed(2)}'),
                    _InfoRow('Margin', '\$${pos.margin.toStringAsFixed(2)}'),
                    const Divider(),
                    _InfoRow('uPNL', '\$${pnl.toStringAsFixed(2)}',
                        valueColor: pnlColor),
                    _InfoRow('ROE', '${position.roePercent.toStringAsFixed(1)}%',
                        valueColor: pnlColor),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;
  const _InfoRow(this.label, this.value, {this.valueColor});

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: Theme.of(context).textTheme.bodyMedium),
            Text(value,
                style: Theme.of(context)
                    .textTheme
                    .bodyMedium
                    ?.copyWith(color: valueColor)),
          ],
        ),
      );
}
