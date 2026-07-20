/// Full engine status received from API.
class EngineStatus {
  final Map<String, double> balance;
  final String supervisorState;
  final RiskStatus risk;
  final List<PositionInfo> positions;

  EngineStatus({
    required this.balance,
    required this.supervisorState,
    required this.risk,
    required this.positions,
  });

  factory EngineStatus.fromJson(Map<String, dynamic> json) => EngineStatus(
        balance: Map<String, double>.from(
            (json['balance'] as Map?)?.map((k, v) => MapEntry(k, (v as num).toDouble())) ?? {}),
        supervisorState: json['supervisor'] ?? 'UNKNOWN',
        risk: RiskStatus.fromJson(json['risk'] ?? {}),
        positions: (json['positions'] as List?)
                ?.map((p) => PositionInfo.fromJson(p))
                .toList() ??
            [],
      );
}

class RiskStatus {
  final double dailyLoss;
  final bool circuitOpen;
  final Map<String, int> dcaCounts;

  RiskStatus({
    required this.dailyLoss,
    required this.circuitOpen,
    required this.dcaCounts,
  });

  factory RiskStatus.fromJson(Map<String, dynamic> json) => RiskStatus(
        dailyLoss: (json['daily_loss'] as num?)?.toDouble() ?? 0.0,
        circuitOpen: json['circuit_open'] ?? false,
        dcaCounts: Map<String, int>.from(
            (json['dca_counts'] as Map?)?.map((k, v) => MapEntry(k, (v as num).toInt())) ?? {}),
      );
}

class PositionInfo {
  final String symbol;
  final String side;
  final String state;
  final String? substate;
  final int version;
  final PositionData? position;

  PositionInfo({
    required this.symbol,
    required this.side,
    required this.state,
    this.substate,
    required this.version,
    this.position,
  });

  factory PositionInfo.fromJson(Map<String, dynamic> json) => PositionInfo(
        symbol: json['symbol'] ?? '',
        side: json['side'] ?? '',
        state: json['state'] ?? 'idle',
        substate: json['substate'],
        version: json['version'] ?? 0,
        position: json['position'] != null ? PositionData.fromJson(json['position']) : null,
      );

  double get unrealisedPnl => position?.unrealisedPnl ?? 0.0;
  double get roePercent => position?.roePercent ?? 0.0;
  bool get isLosing => unrealisedPnl < 0;
}

class PositionData {
  final String symbol;
  final String side;
  final double size;
  final double avgPrice;
  final double markPrice;
  final double margin;
  final double unrealisedPnl;
  final double roePercent;
  final double liqPrice;

  PositionData({
    required this.symbol,
    required this.side,
    required this.size,
    required this.avgPrice,
    required this.markPrice,
    required this.margin,
    required this.unrealisedPnl,
    required this.roePercent,
    required this.liqPrice,
  });

  factory PositionData.fromJson(Map<String, dynamic> json) => PositionData(
        symbol: json['symbol'] ?? '',
        side: json['side'] ?? '',
        size: (json['size'] as num?)?.toDouble() ?? 0.0,
        avgPrice: (json['avg_price'] as num?)?.toDouble() ?? 0.0,
        markPrice: (json['mark_price'] as num?)?.toDouble() ?? 0.0,
        margin: (json['margin'] as num?)?.toDouble() ?? 0.0,
        unrealisedPnl: (json['unrealised_pnl'] as num?)?.toDouble() ?? 0.0,
        roePercent: (json['roe_percent'] as num?)?.toDouble() ?? 0.0,
        liqPrice: (json['liq_price'] as num?)?.toDouble() ?? 0.0,
      );
}
