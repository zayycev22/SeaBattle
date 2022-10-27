import asyncio
import pytest
import json
from server import generate_payload
import websockets
from User import BattleMap


class TestServer:
    # main()
    msg = None

    @pytest.fixture
    def mapData1(self):
        f = open("map1.json", 'r').read()
        data = json.loads(f)
        return data

    @pytest.fixture
    def mapData2(self):
        f = open("map2.json", 'r').read()
        data = json.loads(f)
        return data

    @pytest.mark.asyncio
    async def test_knock(self):
        async with websockets.connect(f"ws://localhost:27000") as websocket:
            await websocket.send(generate_payload("knock-knock", {"nick": 'a'}))
            for i in range(3):
                msg = json.loads(await websocket.recv())
                await asyncio.sleep(0.5)
            assert msg['header'] == 'registered'

    @pytest.mark.asyncio
    async def test_send1(self, mapData1):
        async with websockets.connect(f"ws://localhost:27000") as websocket:
            await websocket.send(generate_payload("knock-knock", {"nick": 'a'}))
            for i in range(3):
                msg = json.loads(await websocket.recv())
                await asyncio.sleep(0.5)


class TestClient:

    def test_ship1(self):
        map = BattleMap(100, 100, None)
        map.createShips(test=True)
        assert len(map.user_ships) == 10

    def test_all_ships_correct(self):
        correct = 0
        map = BattleMap(100, 100, None)
        map.createShips(test=True)
        for i in map.user_ships:
            if i.ship_correct:
                correct += 1
        assert correct == 10
