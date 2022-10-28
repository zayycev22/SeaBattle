import asyncio
import websockets
import json
import pprint

indent = 2
offset_x_user = 30
gauge = 32
offset_y = 40
offset_x_comp = 430


class Game(object):
    ws_clients = set()
    players = dict()
    cur_pl_num = 0
    count_ready = 0
    users = []


global_Game = Game()


async def check_coord(ws, enemy, coord):
    tag = ""
    hit_status = 0
    for i in range(10):
        for j in range(10):
            xn = i * gauge + (i + 1) * indent + offset_x_user
            xk = xn + gauge
            yn = j * gauge + (j + 1) * indent + offset_y
            yk = yn + gauge
            if xn <= coord['x'] <= xk and yn <= coord['y'] <= yk:
                print("CLICKED_COORD =", "my_" + str(i) + "_" + str(j))
                print("SQARE", xn, xk, yn, yk)
                print("COORD in")
                for ship in enemy['map']:
                    print("ship =", ship)
                    print("COORDS =", "my_" + str(j) + "_" + str(i), coord['x'], coord['y'])
                    # если координаты точки совпадают с координатой корабля, то вызвать метод выстрела
                    coordinate = "my_" + str(j) + "_" + str(i)
                    if coordinate in ship['coord_map']:
                        print("SHIP CORDS", ship['coord_map'])
                        # изменить статус попадания
                        hit_status = 1
                        enemy['deaths'] += 1
                        # мы попали, поэтому надо нарисовать крест
                        # self.paintCross(xn, yn, "nmy_" + str(i) + "_" + str(j))
                        # если метод вернул двойку, значит, корабль убит
                        tag = coordinate
                        ship['coord_map'].remove(tag)
                        print("FIND SHIP")
                        return hit_status, xn, yn, xk, yk, tag
                # если статус попадания остался равным нулю - значит, мы промахнулись, передать управление компьютеру
                # иначе дать пользователю стрелять
                if hit_status == 0:
                    tag = "my_" + str(i) + "_" + str(j)
                return hit_status, xn, yn, xk, yk, tag

    return hit_status, xn, yn, xk, yk, tag


async def shoot(ws, data):
    print(global_Game.users)
    username = data['username']
    u_idx = global_Game.users.index(username)
    print("usershootin", username)
    print("enemy =", global_Game.users[global_Game.users.index(username) - 1])
    if u_idx == 1:
        enemy = global_Game.players[global_Game.users[0]]
    else:
        enemy = global_Game.players[global_Game.users[1]]
    res = await check_coord(ws, enemy, data['coords'])
    if res[0]:
        websockets.broadcast(global_Game.ws_clients,
                             generate_payload("killed",
                                              {"xn": res[1], "yn": res[2],
                                               "xk": res[3], "yk": res[4],
                                               "tag": res[5],
                                               "shooted_on": global_Game.users[global_Game.users.index(username) - 1],
                                               "next_turn": username}))
    else:
        websockets.broadcast(global_Game.ws_clients,
                             generate_payload("miss",
                                              {"xn": res[1], "yn": res[2],
                                               "xk": res[3], "yk": res[4],
                                               "tag": res[5],
                                               "shooted_on": global_Game.users[global_Game.users.index(username) - 1],
                                               "next_turn": global_Game.users[global_Game.users.index(username) - 1]
                                               }))
    if enemy['deaths'] == 20:
        websockets.broadcast(global_Game.ws_clients, generate_payload(
            "endgame", {"winner": username}
        ))


async def send_data(ws, data):
    global_Game.players[data['username']]['map'] = data['map']
    pprint.pprint(data)
    global_Game.players[data['username']]['status'] = 'ready'
    global_Game.count_ready += 1
    global_Game.players[data['username']]['deaths'] = 0
    await ws.send(generate_payload("ready", {'username': data['username']}))
    print(global_Game.cur_pl_num, global_Game.count_ready)
    if global_Game.cur_pl_num == 2 and global_Game.count_ready == 2:
        for i in global_Game.players.keys():
            global_Game.players[i]['status'] = 'in_game'
            global_Game.users.append(i)
        websockets.broadcast(global_Game.ws_clients,
                             generate_payload("in_game!!!",
                                              {"fist": global_Game.users[0], "second": global_Game.users[1],
                                               "turn": global_Game.users[0]}))


def generate_payload(header, data):
    return json.dumps({"header": header, "data": data})


async def handle_disconnected(ws):
    global_Game.ws_clients.remove(ws)
    tmp = global_Game.players
    global_Game.players = dict()
    global_Game.cur_pl_num -= 1
    global_Game.count_ready -= 1
    if global_Game.cur_pl_num < 0:
        global_Game.cur_pl_num = 0
    if global_Game.count_ready < 0:
        global_Game.count_ready = 0

    disconnected_ply = None
    nickname = ""
    for nick, pipe in tmp.items():
        if pipe['websocket'] == ws:
            disconnected_ply = nick
            nickname = nick

    print(f"Player {disconnected_ply} disconnected")
    if nickname in global_Game.users:
        global_Game.users.remove(nickname)
    if len(global_Game.ws_clients) == 0:
        return

    global_Game.players = {nick: pipe for nick, pipe in tmp.items() if pipe != ws}

    websockets.broadcast(global_Game.ws_clients, generate_payload("disconnected", {"nick": disconnected_ply}))


async def knock_knock(ws, data):
    if global_Game.cur_pl_num >= 2:
        await ws.send(generate_payload("knock-deny", {}))
        return False
    global_Game.ws_clients.add(ws)
    global_Game.players[data["nick"]] = {}
    global_Game.players[data["nick"]]['websocket'] = ws
    global_Game.players[data["nick"]]['status'] = 'waiting'
    await ws.send(generate_payload("knock-allow", {}))
    websockets.broadcast(global_Game.ws_clients, generate_payload("joined", {"nick": data["nick"]}))
    print(f"Player {data['nick']} joined the lobby")
    global_Game.cur_pl_num += 1
    await ws.send(generate_payload("registered", {}))

    return True


recv_funcs = {
    "knock-knock": knock_knock,
    "send_map": send_data,
    "shoot": shoot,
}


async def msg_handler(ws):
    msg = await ws.recv()
    msg = json.loads(msg)
    knock_res = await knock_knock(ws, msg["data"])

    if not knock_res:
        await ws.close()
        return

    while True:
        await asyncio.sleep(0.1)

        try:
            msg = await ws.recv()
        except Exception as ex:
            await handle_disconnected(ws)
            break
        else:
            msg = json.loads(msg)
            await recv_funcs[msg["header"]](ws, msg["data"])


def main():
    srv = websockets.serve(msg_handler, "", 27000)
    asyncio.get_event_loop().run_until_complete(srv)
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()
