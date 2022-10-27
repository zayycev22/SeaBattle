import asyncio
from random import randint

import pytest
import json
import websockets
from User import BattleMap
import threading


def generate_payload(header, data):
    return json.dumps({"header": header, "data": data})


class HelpTest:
    def __init__(self, loop):
        self.loop = loop
        self.ws1 = None
        self.ws2 = None
        self.msg1 = None
        self.msg2 = None
        self.tasks = []

    async def listen1(self):
        async with websockets.connect(f"ws://localhost:27000") as websocket:
            self.ws1 = websocket
            while True:
                try:
                    self.msg1 = await websocket.recv()
                    await asyncio.sleep(0.1)
                except RuntimeError:
                    break

    async def listen2(self):
        async with websockets.connect(f"ws://localhost:27000") as websocket:
            self.ws2 = websocket
            while True:
                try:
                    self.msg2 = await websocket.recv()
                    await asyncio.sleep(0.1)
                except RuntimeError:
                    break

    async def in_game_helper(self, mapData1, mapData2):
        self.tasks.extend([self.loop.create_task(self.listen1()), self.loop.create_task(self.listen2())])
        await asyncio.sleep(1)
        await self.ws1.send(generate_payload("knock-knock", {"nick": 'a'}))
        await asyncio.sleep(0.4)
        await self.ws2.send(generate_payload("knock-knock", {"nick": 'b'}))
        await asyncio.sleep(0.4)
        await self.ws1.send(json.dumps({"header": "send_map", 'data': mapData1}))
        await asyncio.sleep(0.4)
        await self.ws1.send(json.dumps({"header": "send_map", 'data': mapData2}))
        await asyncio.sleep(0.4)
        self.ws1 = None
        self.ws2 = None
        for task in self.tasks:
            print(task)
            task.cancel()

        yield json.loads(self.msg1)

    async def shoot_helper(self, mapData1, mapData2, coords):
        self.tasks.extend([self.loop.create_task(self.listen1()), self.loop.create_task(self.listen2())])
        await asyncio.sleep(1)
        await self.ws1.send(generate_payload("knock-knock", {"nick": 'a'}))
        await asyncio.sleep(0.4)
        await self.ws2.send(generate_payload("knock-knock", {"nick": 'b'}))
        await asyncio.sleep(0.4)
        await self.ws1.send(json.dumps({"header": "send_map", 'data': mapData1}))
        await asyncio.sleep(0.4)
        await self.ws2.send(json.dumps({"header": "send_map", 'data': mapData2}))
        await asyncio.sleep(2.1)
        await self.ws1.send(
            json.dumps({"header": "shoot", 'data': {'coords': {"x": coords[0], "y": coords[1]}, 'username': 'a'}}))
        await asyncio.sleep(3)
        self.ws1 = None
        self.ws2 = None
        for task in self.tasks:
            print(task)
            task.cancel()
        yield json.loads(self.msg1)

    async def win_helper(self, mapData1, mapData2, coords):
        self.tasks.extend([self.loop.create_task(self.listen1()), self.loop.create_task(self.listen2())])
        await asyncio.sleep(1)
        await self.ws1.send(generate_payload("knock-knock", {"nick": 'a'}))
        await asyncio.sleep(0.4)
        await self.ws2.send(generate_payload("knock-knock", {"nick": 'b'}))
        await asyncio.sleep(0.4)
        await self.ws1.send(json.dumps({"header": "send_map", 'data': mapData1}))
        await asyncio.sleep(0.4)
        await self.ws2.send(json.dumps({"header": "send_map", 'data': mapData2}))
        await asyncio.sleep(2.1)
        await self.ws1.send(
            json.dumps({"header": "shoot", 'data': {'coords': {"x": coords[0], "y": coords[1]}, 'username': 'a'}}))
        await asyncio.sleep(3)
        # дописать
        self.ws1 = None
        self.ws2 = None
        for task in self.tasks:
            print(task)
            task.cancel()
        yield json.loads(self.msg1)


class TestServer:

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

    @pytest.fixture
    def event_loop(self):
        loop = asyncio.get_event_loop()
        yield loop
        loop.close()

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
                await websocket.recv()
                await asyncio.sleep(0.5)
            await websocket.send(json.dumps({"header": "send_map", 'data': mapData1}))
            msg = json.loads(await websocket.recv())
            assert msg['header'] == 'ready'
            await websocket.close()

    @pytest.mark.asyncio
    async def test_send2(self, mapData2):
        async with websockets.connect(f"ws://localhost:27000") as websocket:
            await websocket.send(generate_payload("knock-knock", {"nick": 'b'}))
            for i in range(4):
                await websocket.recv()
                await asyncio.sleep(0.5)
            await websocket.send(json.dumps({"header": "send_map", 'data': mapData2}))
            msg = json.loads(await websocket.recv())
            assert msg['header'] == 'ready'
            await websocket.close()

    @pytest.mark.asyncio
    async def test_game_started(self, mapData1, mapData2, event_loop):
        helper = HelpTest(event_loop)
        answer = {}
        async for i in helper.in_game_helper(mapData1, mapData2):
            answer = i
        await asyncio.sleep(2)
        print(answer)
        assert answer['header'] == "in_game!!!"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("x, y",
                             [(267, 206), (134, 359), (365, 209), (150, 229), (165, 366), (349, 199),
                              (50, 108), (139, 254), (60, 98), (119, 93)])
    async def test_kill_shoot(self, x, y, mapData1, mapData2, event_loop):
        helper = HelpTest(event_loop)
        answer = {}
        async for i in helper.shoot_helper(mapData1, mapData2, (x, y)):
            answer = i
        print(answer)
        await asyncio.sleep(0.4)
        assert answer['header'] == "killed"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("x, y", [(randint(50, 600), randint(50, 600)) for _ in range(5)])
    async def test_miss_shoot(self, x, y, mapData1, mapData2, event_loop):
        helper = HelpTest(event_loop)
        answer = {}
        async for i in helper.shoot_helper(mapData1, mapData2, (x, y)):
            answer = i
        print(answer)
        await asyncio.sleep(0.4)
        event_loop.stop()
        assert answer['header'] == "miss"


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
