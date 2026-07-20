# Exchange + FSM Wiring — Design Spec

**Date:** 2026-07-20
**Status:** Awaiting implementation plan
**Topic:** Подключение reshala-v2 FSM-движка к Bybit через MCP — real-time WebSocket потоки + REST для ордеров

---

## Layer Dependency

```
Application  ── engine/trading_engine.py, ai/
     │            (координирует, но не содержит бизнес-правил)
     ▼
Domain       ── domain/exchange_state.py, domain/events/, domain/commands/,
     │            domain/fsm/, domain/recovery/
     ▼            (бизнес-логика — НЕ знает про Bybit, MCP, WebSocket)
Infrastructure ── exchange/, engine/bus/, logging/
                  (знает про Bybit MCP, транспорт, сериализацию)
```

**Главное правило:** Domain НЕ знает про Infrastructure.

- ✅ `PositionFSM → OrderCommand` (команда — это доменный объект)
- ❌ `PositionFSM → BybitClient` (никогда)
- ✅ `TickerStream → PriceUpdate → EventBus` (инфраструктура публикует доменные события)
- ❌ `ExchangeState.fetch_from_bybit()` (домен не ходит в API)

---

## Architecture Principles

1. **Биржа — единственный источник истины.** Любое расхождение разрешается в пользу биржи.
2. **ExchangeState изменяется только через события.** Никаких прямых присваиваний извне.
3. **PositionFSM читает только ExchangeState.** Не сырые события, не WebSocket, не REST.
4. **События и команды разделены.** EventBus для фактов, CommandBus для намерений.
5. **Один переход состояния FSM на одно событие.** Побочные действия — сколько угодно, но transition() вызывается ровно один раз.
6. **Все переходы детерминированы и воспроизводимы.** Event Log + Snapshot = полный replay.
7. **Бизнес-логика не знает о деталях Bybit API.** OrderCommand — единственный контракт.
8. **Внешние зависимости взаимодействуют с ядром только через события или команды.** AI, Telegram, Metrics — все подписчики/публикаторы EventBus.

---

## 1. File Structure

```
reshala-v2/
│
├── domain/                          # Бизнес-логика — не знает про Bybit
│   ├── __init__.py
│   │
│   ├── events/                      # Типизированные события (факты)
│   │   ├── __init__.py
│   │   ├── base.py                  # Event, EventType enum
│   │   ├── market.py                # PriceUpdate
│   │   ├── orders.py                # OrderFilled, OrderRejected, OrderCancelled
│   │   ├── positions.py             # PositionChanged, FundingChanged
│   │   ├── ai.py                    # AICompleted
│   │   ├── system.py                # TimerTick, SystemShutdown, HealthEvent
│   │   └── risk.py                  # RiskLimitHit
│   │
│   ├── commands/                    # Команды (намерения — можно отклонить)
│   │   ├── __init__.py
│   │   ├── base.py                  # BaseCommand
│   │   ├── order.py                 # OrderCommand
│   │   ├── cancel.py                # CancelCommand
│   │   └── close_position.py        # ClosePositionCommand
│   │
│   ├── fsm/                         # Per-position state machine
│   │   ├── __init__.py
│   │   ├── states.py                # FSMState, ActiveSubState, WaitReason
│   │   ├── transitions.py           # TransitionTable
│   │   ├── position_fsm.py          # PositionFSM
│   │   └── supervisor.py            # GlobalSupervisor
│   │
│   ├── recovery/                    # Восстановление после рестарта
│   │   ├── __init__.py
│   │   ├── manager.py               # RecoveryManager
│   │   ├── snapshot.py              # StateSnapshotter
│   │   └── replay.py                # Event replay engine
│   │
│   └── exchange_state.py            # Event-sourced cache биржи
│
├── exchange/                        # Инфраструктура — знает про Bybit MCP
│   ├── __init__.py
│   ├── adapter.py                   # ExchangeAdapter — MCP REST wrapper
│   ├── mapper.py                    # Raw Bybit data → typed Events
│   │
│   ├── streams/                     # WebSocket → EventBus producers
│   │   ├── __init__.py
│   │   ├── base.py                  # BaseStream, StreamStatus enum
│   │   ├── ticker.py                # TickerStream → PriceUpdate
│   │   ├── position.py              # PositionStream → PositionChanged ⭐
│   │   ├── execution.py             # ExecutionStream → OrderFilled ⭐
│   │   ├── order.py                 # OrderStream → OrderRejected/Cancelled
│   │   ├── manager.py               # StreamManager — lifecycle, health, restart
│   │   ├── gap_detector.py          # Per-stream sequence gap detection
│   │   └── reconnect.py             # ReconnectPolicy — exponential backoff
│   │
│   └── __init__.py
│
├── engine/                          # Application layer
│   ├── __init__.py
│   ├── trading_engine.py            # TradingEngine — main loop, dispatch
│   │
│   ├── bus/                         # Message buses
│   │   ├── __init__.py
│   │   ├── event_bus.py             # EventBus (upgraded: bounded queues, priority)
│   │   ├── command_bus.py            # CommandBus — separate from EventBus
│   │   └── subscriptions.py         # Subscription routing + Dead Letter Queue
│   │
│   └── supervisor.py                # GlobalSupervisor health checks
│
├── ai/                              # AI decision service
│   ├── __init__.py
│   ├── service.py                   # AIService — request/response lifecycle
│   ├── prompts.py                   # Prompt templates
│   └── providers/                   # Model backends
│       ├── __init__.py
│       ├── deepseek.py
│       └── claude.py
│
├── event_logging/                   # Black box event log
│   ├── __init__.py
│   └── event_logger.py              # JSONL append-only logger
│
└── tests/
    ├── unit/
    │   ├── domain/
    │   │   ├── test_exchange_state.py
    │   │   ├── test_events.py
    │   │   ├── test_commands.py
    │   │   ├── test_transitions.py
    │   │   ├── test_position_fsm.py
    │   │   ├── test_supervisor.py
    │   │   └── test_recovery.py
    │   ├── exchange/
    │   │   ├── test_adapter.py
    │   │   ├── test_streams.py
    │   │   ├── test_stream_manager.py
    │   │   ├── test_mapper.py
    │   │   ├── test_gap_detector.py
    │   │   └── test_reconnect.py
    │   └── engine/
    │       ├── test_event_bus.py
    │       ├── test_command_bus.py
    │       └── test_trading_engine.py
    ├── integration/
    │   ├── test_full_flow.py         # EventBus → FSM → CommandBus
    │   └── test_recovery_flow.py     # RecoveryManager → ExchangeState → FSM
    ├── replay/
    │   └── test_replay.py            # Snapshot + EventLog → full state recovery
    └── stress/
        └── test_reconnect.py         # ReconnectPolicy under failure
```

**Total:** ~55 small files instead of ~10 large ones. Каждый файл — одна ответственность.

---

## 2. EventBus → EventBus + CommandBus

Два раздельных шины:

```
Streams → EventBus → ExchangeState → PositionFSM → CommandBus → ExchangeAdapter → Bybit REST
```

**EventBus** — факты, которые уже произошли (нельзя отменить):
- PriceUpdate, PositionChanged, OrderFilled, OrderRejected, OrderCancelled
- AICompleted, TimerTick, RiskLimitHit, HealthEvent

**CommandBus** — намерения (можно отклонить):
- PlaceOrder, CancelOrder, CancelAllOrders

---

## 3. Stream Architecture

### 3.1 Streams as Producers

Каждый stream — независимый producer, сам публикует в EventBus:

```python
class TickerStream:
    """PriceUpdate producer. Подписывается на tickers.{symbol}."""
    status: StreamStatus = StreamStatus.STARTING

    async def run(self, symbol: str) -> None:
        self.status = StreamStatus.RUNNING
        while self._running:
            try:
                sub_id = await self._mcp.start_subscription(
                    category="linear", topic=f"tickers.{symbol}"
                )
                await self._consume(sub_id)
            except Exception:
                self.status = StreamStatus.RECONNECTING
                await self._reconnect.wait()
                self.status = StreamStatus.RUNNING
```

**PriceUpdate coalescing:** хранится только последняя цена per symbol.
При переполнении очереди старые PriceUpdate перезаписываются новыми.

### 3.2 Stream Priority

| Stream | Priority | Drop Policy | Gap Detection |
|--------|----------|-------------|---------------|
| PositionStream | ⭐⭐⭐⭐⭐ | Never drop | Yes → REST resync |
| ExecutionStream | ⭐⭐⭐⭐⭐ | Never drop | Yes → REST resync |
| OrderStream | ⭐⭐⭐⭐ | Never drop | Yes |
| TickerStream | ⭐⭐⭐ | Coalesce latest | No |

### 3.3 StreamManager

```python
class StreamManager:
    """Запуск, остановка, рестарт, health check всех stream'ов."""

    async def start_all(self) -> None: ...
    async def stop_all(self) -> None: ...
    async def restart_symbol(self, symbol: str) -> None: ...
    def health(self) -> dict[str, StreamStatus]: ...
```

### 3.4 Long-poll вместо частого polling

```python
# ❌ НЕ ТАК: asyncio.sleep(0.1)  # 10 req/s per stream
# ✅ ТАК:
messages = await self._mcp.read_messages(sub_id, limit=50)  # блокируется до сообщений
await asyncio.sleep(1.0)  # heartbeat если нет сообщений
```

### 3.5 ReconnectPolicy

```python
class ReconnectPolicy:
    BACKOFF = [1, 2, 5, 10, 30, 60]  # секунды, exponential

    async def wait(self) -> None:
        delay = self.BACKOFF[min(self._attempt, len(self.BACKOFF) - 1)]
        self._attempt += 1
        await asyncio.sleep(delay)

    def reset(self) -> None:
        self._attempt = 0
```

### 3.6 GapDetector — per stream type

Разные типы потоков Bybit могут использовать разные механизмы нумерации. GapDetector знает особенности конкретного stream'а:

```python
class GapDetector:
    def __init__(self, max_gap: int = 5):
        self._last_seq = 0

    def check(self, raw_msg: dict) -> bool:
        seq = raw_msg.get("seq", 0)
        gap = seq - self._last_seq > 1
        self._last_seq = max(self._last_seq, seq)
        return gap  # если True → trigger REST resync
```

---

## 4. ExchangeState — Event-Sourced Cache

```python
class ExchangeState:
    """Локальный кеш биржи. Изменяется ТОЛЬКО через apply(event)."""

    def apply(self, event: Event) -> None:
        """Единственный способ изменить состояние."""
        handler = self._handlers.get(event.type)
        if handler:
            handler(event)
            self._version += 1

    # Read-only accessors
    def get_position(self, symbol: str) -> dict | None: ...
    def has_open_orders(self, symbol: str) -> bool: ...
    def get_balance(self, coin: str) -> float: ...

    # Snapshot + Replay
    def snapshot(self) -> dict: ...
    @classmethod
    def from_snapshot(cls, data: dict) -> "ExchangeState": ...
    @classmethod
    def replay(cls, snapshot: dict, events: list[Event]) -> "ExchangeState": ...
```

**Snapshot interval:** каждые 100 событий.

**Recovery flow:**
```
Snapshot + Event Log → replay → Current ExchangeState
```

---

## 5. OrderCommand — Контракт FSM ↔ Exchange

```python
@dataclass
class OrderCommand:
    symbol: str
    side: str              # "Buy" | "Sell"
    qty: str               # уже округлено до шага биржи
    price: str = ""        # "" = Market
    reduce_only: bool = False
    operation_id: str = "" # связка FSM → order
    order_link_id: str = ""# идемпотентность
    tp_price: str = ""
    sl_price: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    correlation_id: str = ""  # сквозная цепочка: AI → Order → Fill → TP → Close
```

FSM публикует `OrderCommand` в `CommandBus`. ExchangeAdapter читает CommandBus и исполняет.

---

## 6. ExchangeAdapter — Без бизнес-логики

ExchangeAdapter **никогда не принимает решений.** Только исполняет команды:

```python
class ExchangeAdapter:
    """Тонкая обёртка над Bybit MCP. Без бизнес-логики."""

    # Commands (from CommandBus)
    async def place_order(self, cmd: OrderCommand) -> dict: ...
    async def cancel_order(self, symbol: str, order_id: str) -> dict: ...
    async def cancel_all_orders(self, symbol: str) -> None: ...

    # Queries (used by RecoveryManager and gap resync)
    async def fetch_positions(self) -> list[dict]: ...
    async def fetch_open_orders(self, symbol: str = None) -> list[dict]: ...
    async def fetch_balance(self, coin: str = "USDT") -> dict: ...
    async def fetch_execution_history(self, symbol: str) -> list[dict]: ...
```

---

## 7. TradingEngine — Main Loop

### 7.1 Single dispatcher per symbol

```python
class TradingEngine:
    """По одному диспетчеру на символ → параллельно, без гонок."""

    async def run(self) -> None:
        # 1. Recovery
        fsms = await self._recover()

        # 2. Start all streams
        await self._stream_manager.start_all()

        # 3. Per-symbol event loops
        tasks = [
            asyncio.create_task(self._symbol_loop(symbol, fsm))
            for symbol, fsm in fsms.items()
        ]
        await asyncio.gather(*tasks)

    async def _symbol_loop(self, symbol: str, fsm: PositionFSM) -> None:
        """Один символ = один последовательный цикл. Нет гонок."""
        while self._running:
            event = await self._bus.get(symbol, timeout=1.0)
            if event is None:
                await self._tick(fsm)
                continue

            # 1. Update exchange state
            self._state.apply(event)

            # 2. One event → one FSM decision
            await self._dispatch_one(fsm, event)
```

### 7.2 Dispatch — один переход на событие

```python
async def _dispatch_one(self, fsm: PositionFSM, event: Event) -> None:
    """Одно событие → одно изменение состояния. Побочные эффекты — сколько угодно."""

    match (fsm.state, event.type):
        case (FSMState.IDLE, EventType.PRICE_UPDATE):
            if self._should_evaluate(fsm):
                await self._ai_service.request_decision(fsm, self._state)

        case (FSMState.WAIT_FILL, EventType.ORDER_FILLED):
            fsm.transition(FSMState.ACTIVE, trigger="OrderFilled",
                          reason=f"filled {event.qty} @ {event.price}",
                          correlation_id=event.correlation_id)

        case (FSMState.WAIT_FILL, EventType.ORDER_REJECTED):
            fsm.transition(FSMState.VERIFY, trigger="OrderRejected",
                          reason=event.reason)

        case (_, EventType.POSITION_CHANGED):
            if not self._position_matches_fsm(fsm):
                await self._reconcile_fsm(fsm)  # exchange always wins

        case (_, EventType.RISK_LIMIT_HIT):
            fsm.transition(FSMState.PAUSED_RISK, trigger="RiskLimitHit",
                          reason=f"{event.limit_type}")

        case (_, EventType.HEALTH_EVENT) if event.severity == "critical":
            fsm.transition(FSMState.PAUSED_EXCHANGE, trigger="HealthCritical",
                          reason=event.message)
```

### 7.3 Race protection

- **Один диспетчер на символ** — события BTC не блокируют ETH
- **Внутри символа строгая последовательность** — никаких `asyncio.gather()` для FSM переходов
- **FSM читает ExchangeState, не EventBus напрямую** — состояние консистентно

---

## 8. AI Service — Отдельный сервис

TradingEngine не знает про LLM:

```python
class AIService:
    """AI decision service. TradingEngine публикует AIRequest → AIService → AICompleted."""

    async def request_decision(self, fsm: PositionFSM, state: ExchangeState) -> None:
        """Асинхронно. Результат придёт как AICompleted в EventBus."""
        request = AIRequest(
            symbol=fsm.symbol,
            state_version=fsm.state_version,
            position=state.get_position(fsm.symbol),
            correlation_id=str(uuid.uuid4()),
        )
        # Запускаем асинхронно — не блокируем движок
        asyncio.create_task(self._call_model(request))

    async def _call_model(self, request: AIRequest) -> None:
        try:
            decision = await self._provider.decide(request)
            event = AICompleted(
                decision=decision,
                operation_id=request.correlation_id,
                state_version=request.state_version,
                correlation_id=request.correlation_id,
            )
            await self._bus.publish(event)
        except Exception:
            # Retry or fallback model
            pass
```

**Провайдеры:**

```python
# ai/providers/deepseek.py
class DeepSeekProvider:
    async def decide(self, request: AIRequest) -> dict: ...

# ai/providers/claude.py
class ClaudeProvider:
    async def decide(self, request: AIRequest) -> dict: ...
```

---

## 9. Correlation ID — Сквозная трассировка

```python
@dataclass
class Event:
    correlation_id: str = ""  # сквозной ID через всю цепочку
    sequence: int = 0         # монотонный в рамках stream'а
    source: str = ""          # "bybit_ws", "ai_service", "supervisor"
```

Цепочка: `AI → Order → Fill → TP → Close` — все с одним `correlation_id`.

---

## 10. Dead Letter Queue

```python
class DeadLetterQueue:
    """События, которые невозможно обработать."""

    async def push(self, event: Event, error: str) -> None:
        await self._logger.log({
            "event_id": event.event_id,
            "type": event.type.name,
            "symbol": getattr(event, "symbol", ""),
            "error": error,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
```

FSM удалена, битые данные, неизвестный symbol — всё попадает в DLQ для анализа.

---

## 11. Health Events

Supervisor публикует HealthEvent в EventBus. FSM реагирует не зная об инфраструктуре:

```python
@dataclass
class HealthEvent(Event):
    severity: str   # "warning" | "critical"
    component: str  # "ticker_stream" | "position_stream" | "api"
    message: str

    def __post_init__(self):
        self.type = EventType.HEALTH_EVENT
```

---

## 12. Data Flow Summary

```
Bybit WS
    │
    ▼
exchange/streams/  (Ticker / Position / Execution / Order)
    │
    ▼
engine/bus/EventBus  (факты)
    │
    ├── domain/exchange_state.py.apply(event)  ← event-sourced
    ├── event_logging/event_logger.py           ← JSONL black box
    ├── engine/bus/subscriptions.py (DLQ)      ← unprocessable
    └── engine/trading_engine.py._dispatch()
            │
            ▼
        domain/fsm/position_fsm.py  ← читает ExchangeState
            │
            ▼
        domain/commands/order.py    ← контракт OrderCommand
            │
            ▼
        engine/bus/CommandBus  (намерения)
            │
            ▼
        exchange/adapter.py.place_order()  ← MCP-обёртка
            │
            ▼
        Bybit REST
```

---

## 13. Scope Boundaries

**В этом spec:**
- Layer dependency diagram + 8 architecture principles
- Domain layer: events (7 files), commands (4 files), FSM (4 files), recovery (3 files), ExchangeState
- Exchange layer: adapter, mapper, streams (8 files), ReconnectPolicy, GapDetector
- Engine layer: TradingEngine, EventBus, CommandBus, subscriptions/DLQ
- AI service with pluggable providers
- Correlation ID, Dead Letter Queue, Health Events
- ~55 small files, каждый с одной ответственностью

**Out of scope (отдельные specs):**
- AI prompt engineering
- Risk Engine (Level 1/2/3 guards)
- Telegram notifications
- Metrics/Monitoring dashboard
- Multi-account support
- Strategy backtesting

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-20 | Initial spec — Exchange + FSM wiring design |
| 2026-07-20 | v2: polished file structure — domain/exchange/engine/ai/logging layers, packages instead of large files, tests restructured into unit/integration/replay/stress |
