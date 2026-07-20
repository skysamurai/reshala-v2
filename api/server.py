"""FastAPI server — connects Flutter app to reshala-v2 trading engine.

Endpoints:
  GET  /api/status        — positions, FSM states, balance, risk status
  POST /api/command       — pause, resume, close position
  WS   /api/ws            — real-time events (PriceUpdate, OrderFilled, FSM transitions)
"""
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel

log = logging.getLogger(__name__)


class CommandRequest(BaseModel):
    command: str       # "pause", "resume", "close", "status"
    symbol: str = ""   # target symbol (required for close)
    params: dict = {}


class ApiServer:
    """Wraps the trading engine for mobile app consumption."""

    def __init__(self, engine, bus, supervisor, state, risk_engine, host: str = "0.0.0.0", port: int = 8420):
        self._engine = engine
        self._bus = bus
        self._supervisor = supervisor
        self._state = state
        self._risk = risk_engine
        self._host = host
        self._port = port
        self._ws_clients: list[WebSocket] = []

    def build_app(self) -> FastAPI:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Start broadcasting events to WS clients
            asyncio.create_task(self._broadcast_loop())
            yield

        app = FastAPI(title="Reshala v2 API", lifespan=lifespan)

        @app.get("/api/status")
        async def status():
            return JSONResponse(self._build_status())

        @app.post("/api/command")
        async def command(req: CommandRequest):
            from domain.events import UserCommand
            event = UserCommand(command=req.command, symbol=req.symbol, params=req.params)
            await self._bus.publish(event)
            return {"ok": True, "command": req.command}

        @app.websocket("/api/ws")
        async def ws_endpoint(ws: WebSocket):
            await ws.accept()
            self._ws_clients.append(ws)
            # Send initial snapshot
            await ws.send_json({"type": "snapshot", "data": self._build_status()})
            try:
                while True:
                    # Keep alive + receive commands from app
                    data = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                    msg = json.loads(data)
                    if msg.get("type") == "command":
                        from domain.events import UserCommand
                        event = UserCommand(
                            command=msg.get("command", ""),
                            symbol=msg.get("symbol", ""),
                            params=msg.get("params", {}),
                        )
                        await self._bus.publish(event)
            except (WebSocketDisconnect, asyncio.TimeoutError):
                self._ws_clients.remove(ws)

        return app

    def _build_status(self) -> dict:
        positions = []
        for key, fsm in self._supervisor.fsms.items():
            pos = self._state.get_position(fsm.symbol)
            positions.append({
                "symbol": fsm.symbol,
                "side": fsm.side,
                "state": fsm.state.value,
                "substate": fsm.active_substate.value if fsm.active_substate else None,
                "version": fsm.state_version,
                "position": pos,
            })

        return {
            "balance": self._state._balance,
            "supervisor": self._supervisor.state.name,
            "risk": {
                "daily_loss": self._risk._daily_loss,
                "circuit_open": self._risk.is_circuit_open(),
                "dca_counts": dict(self._risk._dca_count),
            },
            "positions": positions,
        }

    async def _broadcast_loop(self) -> None:
        """Send real-time updates to all WS clients every 2 seconds."""
        while True:
            await asyncio.sleep(2.0)
            if self._ws_clients:
                data = {"type": "update", "data": self._build_status()}
                dead = []
                for ws in self._ws_clients:
                    try:
                        await ws.send_json(data)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    self._ws_clients.remove(ws)

    def run(self):
        import uvicorn
        uvicorn.run(self.build_app(), host=self._host, port=self._port, log_level="info")
