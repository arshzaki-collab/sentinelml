"""FastAPI application providing REST endpoints, WebSockets, and multiplayer APIs."""

from __future__ import annotations

import os
from typing import Annotated

import duckdb
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from blindbillion.data.db import DEFAULT_DB_PATH
from blindbillion.engine.engine import GameEngine
from blindbillion.multiplayer.connection_manager import connection_manager
from blindbillion.multiplayer.db import get_db as get_db
from blindbillion.multiplayer.db import get_engine, init_db
from blindbillion.multiplayer.db_models import RoomModel, RoomPlayerModel
from blindbillion.multiplayer.game_coordinator import GameCoordinator
from blindbillion.multiplayer.models import (
    ActionResponse,
    AddAIPlayerRequest,
    CreateRoomRequest,
    CreateRoomResponse,
    JoinRoomRequest,
    JoinRoomResponse,
    MultiplayerGameActionRequest,
    RealtimeEventType,
    RoomGameStateResponse,
    RoomPublicView,
    SetReadyRequest,
)
from blindbillion.multiplayer.rate_limiter import global_rate_limiter
from blindbillion.multiplayer.room_manager import (
    RoomManager,
    serialize_room_view,
)
from blindbillion.multiplayer.session_manager import (
    authenticate_player,
    get_authenticated_player,
)

# Global engine coordinator backed by analytical DuckDB cache
_coordinator: GameCoordinator | None = None


def get_game_coordinator() -> GameCoordinator:
    """Retrieve or lazily initialize GameCoordinator with read-only DuckDB connection."""
    global _coordinator
    if _coordinator is None:
        con = duckdb.connect(str(DEFAULT_DB_PATH), read_only=True)
        engine = GameEngine(con=con)
        _coordinator = GameCoordinator(engine=engine)
    return _coordinator


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    app = FastAPI(
        title="Blind Billion 2.0 Multiplayer API",
        version="2.0.0",
        description="Server-authoritative multiplayer backend with realtime synchronization.",
    )

    allowed_origins_env = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
    )
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins if allowed_origins else ["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup() -> None:
        init_db(get_engine())

    @app.post(
        "/api/rooms",
        response_model=CreateRoomResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a new multiplayer room",
    )
    def create_room_endpoint(
        request: Request,
        payload: CreateRoomRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> CreateRoomResponse:
        client_ip = request.client.host if request.client else "unknown"
        if not global_rate_limiter.check_rate_limit(f"create_{client_ip}", max_requests=10):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Room creation rate limit exceeded. Please wait.",
            )

        return RoomManager.create_room(
            session=db, host_name=payload.host_name, custom_seed=payload.room_seed
        )

    @app.post(
        "/api/rooms/{room_code}/join",
        response_model=JoinRoomResponse,
        status_code=status.HTTP_200_OK,
        summary="Join an existing room as a player",
    )
    async def join_room_endpoint(
        request: Request,
        room_code: str,
        payload: JoinRoomRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> JoinRoomResponse:
        client_ip = request.client.host if request.client else "unknown"
        if not global_rate_limiter.check_rate_limit(f"join_{client_ip}", max_requests=30):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Room joining rate limit exceeded. Please wait.",
            )

        resp = RoomManager.join_room(
            session=db, room_code=room_code, player_name=payload.player_name
        )

        # Broadcast update to room members
        await connection_manager.broadcast_to_room(
            room_code=resp.room.room_code,
            event=RealtimeEventType.PLAYER_JOINED,
            payload={"player_id": resp.player_id, "room": resp.room.model_dump(mode="json")},
        )
        return resp

    @app.get(
        "/api/rooms/{room_code}",
        response_model=RoomPublicView,
        status_code=status.HTTP_200_OK,
        summary="Get room summary and player listing",
    )
    def get_room_endpoint(
        room_code: str,
        request: Request,
        db: Annotated[Session, Depends(get_db)],
    ) -> RoomPublicView:
        client_ip = request.client.host if request.client else "unknown"
        rate_key = f"get_room_{client_ip}"
        if not global_rate_limiter.check_rate_limit(rate_key, max_requests=60, window_seconds=60.0):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Room query rate limit exceeded. Please wait.",
            )

        code = room_code.strip().upper()
        room = db.query(RoomModel).filter(RoomModel.room_code == code).first()
        if not room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")
        return serialize_room_view(room)

    @app.post(
        "/api/rooms/{room_code}/ready",
        response_model=RoomPublicView,
        summary="Toggle ready status in lobby",
    )
    async def set_ready_endpoint(
        room_code: str,
        payload: SetReadyRequest,
        request: Request,
        session_token: Annotated[str, Depends(get_authenticated_player)],
        db: Annotated[Session, Depends(get_db)],
    ) -> RoomPublicView:
        client_ip = request.client.host if request.client else "unknown"
        rate_key = f"ready_{client_ip}"
        if not global_rate_limiter.check_rate_limit(rate_key, max_requests=30, window_seconds=60.0):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Ready toggle rate limit exceeded. Please wait.",
            )

        player = authenticate_player(session=db, session_token=session_token, room_code=room_code)
        updated_room = RoomManager.set_player_ready(
            session=db, player=player, is_ready=payload.is_ready
        )

        await connection_manager.broadcast_to_room(
            room_code=room_code,
            event=RealtimeEventType.PLAYER_READY,
            payload={
                "player_id": player.player_id,
                "is_ready": payload.is_ready,
                "room": updated_room.model_dump(mode="json"),
            },
        )
        return updated_room

    @app.post(
        "/api/rooms/{room_code}/ai",
        response_model=RoomPublicView,
        summary="Add an AI opponent to lobby (host only)",
    )
    async def add_ai_endpoint(
        room_code: str,
        payload: AddAIPlayerRequest,
        session_token: Annotated[str, Depends(get_authenticated_player)],
        db: Annotated[Session, Depends(get_db)],
    ) -> RoomPublicView:
        player = authenticate_player(session=db, session_token=session_token, room_code=room_code)
        if not player.is_host:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the host can add AI opponents.",
            )

        updated_room = RoomManager.add_ai_player(
            session=db, room_code=room_code, difficulty=payload.difficulty
        )

        await connection_manager.broadcast_to_room(
            room_code=room_code,
            event=RealtimeEventType.PLAYER_JOINED,
            payload={"room": updated_room.model_dump(mode="json")},
        )
        return updated_room

    @app.delete(
        "/api/rooms/{room_code}/ai/{player_id}",
        response_model=RoomPublicView,
        summary="Remove an AI opponent from lobby (host only)",
    )
    async def remove_ai_endpoint(
        room_code: str,
        player_id: str,
        session_token: Annotated[str, Depends(get_authenticated_player)],
        db: Annotated[Session, Depends(get_db)],
    ) -> RoomPublicView:
        player = authenticate_player(session=db, session_token=session_token, room_code=room_code)
        if not player.is_host:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the host can remove AI opponents.",
            )

        updated_room = RoomManager.remove_ai_player(
            session=db, room_code=room_code, player_id=player_id
        )

        await connection_manager.broadcast_to_room(
            room_code=room_code,
            event=RealtimeEventType.PLAYER_DISCONNECTED,
            payload={"player_id": player_id, "room": updated_room.model_dump(mode="json")},
        )
        return updated_room

    @app.post(
        "/api/rooms/{room_code}/start",
        response_model=RoomGameStateResponse,
        summary="Start the game (host only)",
    )
    async def start_game_endpoint(
        room_code: str,
        session_token: Annotated[str, Depends(get_authenticated_player)],
        db: Annotated[Session, Depends(get_db)],
        coordinator: Annotated[GameCoordinator, Depends(get_game_coordinator)],
    ) -> RoomGameStateResponse:
        player = authenticate_player(session=db, session_token=session_token, room_code=room_code)
        resp = coordinator.start_game(
            session=db, room_code=room_code, caller_player_id=player.player_id
        )

        await connection_manager.broadcast_to_room(
            room_code=room_code,
            event=RealtimeEventType.GAME_STARTED,
            payload={"room": resp.room.model_dump(mode="json")},
        )
        return resp

    @app.get(
        "/api/rooms/{room_code}/state",
        response_model=RoomGameStateResponse,
        summary="Get player's current game state view",
    )
    def get_game_state_endpoint(
        room_code: str,
        session_token: Annotated[str, Depends(get_authenticated_player)],
        db: Annotated[Session, Depends(get_db)],
        coordinator: Annotated[GameCoordinator, Depends(get_game_coordinator)],
    ) -> RoomGameStateResponse:
        player = authenticate_player(session=db, session_token=session_token, room_code=room_code)
        return coordinator.get_room_game_state(
            session=db, room_code=room_code, player_id=player.player_id
        )

    @app.post(
        "/api/rooms/{room_code}/action",
        response_model=ActionResponse,
        summary="Submit buying or transfer action",
    )
    async def submit_action_endpoint(
        room_code: str,
        payload: MultiplayerGameActionRequest,
        request: Request,
        session_token: Annotated[str, Depends(get_authenticated_player)],
        db: Annotated[Session, Depends(get_db)],
        coordinator: Annotated[GameCoordinator, Depends(get_game_coordinator)],
    ) -> ActionResponse:
        client_ip = request.client.host if request.client else "unknown"
        rate_key = f"action_{client_ip}"
        if not global_rate_limiter.check_rate_limit(rate_key, max_requests=60, window_seconds=60.0):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Action submission rate limit exceeded. Please wait.",
            )

        player = authenticate_player(session=db, session_token=session_token, room_code=room_code)
        resp = coordinator.submit_action(
            session=db, room_code=room_code, player=player, request=payload
        )

        # Broadcast action committed event
        await connection_manager.broadcast_to_room(
            room_code=room_code,
            event=RealtimeEventType.ACTION_COMMITTED,
            payload={
                "player_id": player.player_id,
                "display_name": player.display_name,
                "action_type": payload.action_type,
                "is_barrier_cleared": resp.is_barrier_cleared,
                "room": resp.room.model_dump(mode="json"),
            },
        )

        if resp.is_barrier_cleared:
            event_type = (
                RealtimeEventType.GAME_FINISHED
                if resp.room.is_completed
                else RealtimeEventType.ROUND_ADVANCED
            )
            await connection_manager.broadcast_to_room(
                room_code=room_code,
                event=event_type,
                payload={"room": resp.room.model_dump(mode="json")},
            )

        return resp

    @app.websocket("/ws/rooms/{room_code}")
    async def websocket_endpoint(
        websocket: WebSocket,
        room_code: str,
        token: Annotated[str | None, Query()] = None,
        db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
    ) -> None:
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        try:
            player = authenticate_player(session=db, session_token=token, room_code=room_code)
        except HTTPException:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        player.is_connected = True
        db.commit()
        player_id = player.player_id
        display_name = player.display_name
        # Release DB connection back to pool during active WebSocket loop
        db.close()

        await connection_manager.connect(
            room_code=room_code, player_id=player_id, websocket=websocket
        )
        await connection_manager.broadcast_to_room(
            room_code=room_code,
            event=RealtimeEventType.PLAYER_RECONNECTED,
            payload={"player_id": player_id, "display_name": display_name},
        )

        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            await connection_manager.disconnect(room_code=room_code, player_id=player_id)
            player_record = (
                db.query(RoomPlayerModel).filter(RoomPlayerModel.player_id == player_id).first()
            )
            migrated_host_id: str | None = None
            if player_record:
                player_record.is_connected = False
                migrated_host_id = RoomManager.migrate_host_if_needed(
                    session=db, room=player_record.room
                )
                db.commit()

            await connection_manager.broadcast_to_room(
                room_code=room_code,
                event=RealtimeEventType.PLAYER_DISCONNECTED,
                payload={"player_id": player_id, "display_name": display_name},
            )

            if migrated_host_id:
                await connection_manager.broadcast_to_room(
                    room_code=room_code,
                    event=RealtimeEventType.HOST_MIGRATED,
                    payload={"new_host_id": migrated_host_id},
                )

    return app


app = create_app()
