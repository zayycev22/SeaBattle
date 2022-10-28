import asyncio
import json
import time
from tkinter import *
from tkinter import messagebox
import websockets
from server import generate_payload
from User import BattleMap


class UserInterface:
    def __init__(self, loop: asyncio):
        self.loop = loop
        self.master = Tk()
        self.width = 600
        self.height = 600
        self.bg = "white"
        self.states = {1: 'user_input', 2: "ship_placement", 3: "user_waiting", 4: "game", 5: "endgame"}
        self.running = True
        self.host = StringVar()
        self.nickname = StringVar()
        self.tasks = []
        self.host = ""
        self.username = ""
        self.state = 1
        self._preset()
        self.turn = None
        self.msg = {}
        self.__Map = BattleMap(self.width, self.height, self.loop, self.master)
        self.__Enemy_map = BattleMap(self.width, self.height, self.loop, self.master, False)
        self.tasks.append(self.loop.create_task(self.run()))
        self.ws = None
        self.winner = False

    def __makeform(self, fields):
        entries = []
        for field in fields:
            row = Frame(self.master)
            lab = Label(row, width=15, text=field, anchor='w')
            ent = Entry(row)
            row.pack(side=TOP, fill=X, padx=5, pady=5)
            lab.pack(side=LEFT)
            ent.pack(side=RIGHT, expand=YES, fill=X)
            entries.append((field, ent, row))
        return entries

    def _preset(self):
        if self.states[self.state] == 'user_input':
            self.master.resizable(False, False)
            self.master.title("Морской бой")
            self.master['bg'] = self.bg
            self.master.protocol("WM_DELETE_WINDOW", self.__on_stop)
            self.ents = self.__makeform(['host', 'username'])
            self.b1 = Button(self.master, text='Начать игру',
                             command=self.__check_data2)
            self.b1.pack(side=LEFT, padx=100, pady=5)
        elif self.states[self.state] == 'ship_placement':
            self.__Map.preset()
            self.__Map.create_map()
            print("PASSED")
        elif self.states[self.state] == "user_waiting":

            print("OK pr 3")
            self.__Enemy_map.preset()

        elif self.states[self.state] == "game":
            print("game started")
            self.__Enemy_map.create_map()
            self.tasks.append(self.loop.create_task(self.check_turn()))

        elif self.states[self.state] == "endgame":
            if self.winner:
                text = "Вы выйграли"
            else:
                text = "Вы проиграли"
            if messagebox.showinfo("Игра завершилась", text):
                self.__on_stop(True)

    async def run(self):
        while self.running:
            if self.running:
                self.master.update_idletasks()
                self.master.update()
                # self.__preset()
                await asyncio.sleep(.01)

    def __on_stop(self, endgame=False):
        if not endgame:
            if messagebox.askokcancel("Выход из игры", "Хотите выйти из игры?"):
                self.running = False
                print(len(self.tasks))
                for task in self.tasks:
                    task.cancel()
                self.loop.stop()
                self.master.destroy()
        else:
            self.running = False
            print(len(self.tasks))
            for task in self.tasks:
                task.cancel()
            self.loop.stop()
            self.master.destroy()

    def __check_data2(self):
        self.tasks.append(self.loop.create_task(self.__check_data()))

    def destroy_all(self):
        self.b1.destroy()
        for i in self.ents:
            for j in range(1, len(i)):
                i[j].destroy()

    @staticmethod
    def generate_payload(header, data):
        return json.dumps({"header": header, "data": data})

    async def ws_handler(self):
        async with websockets.connect(f"ws://{self.host}:27000") as websocket:
            if self.state < 2:
                await websocket.send(generate_payload("knock-knock", {"nick": self.username}))
            while True:
                self.msg = await websocket.recv()
                print("message =", self.msg)
                self.msg = json.loads(self.msg)
                hdr = self.msg["header"]

                if hdr == "registered":
                    self.ws = websocket
                    self.__Map.ws = self.ws
                    self.__Enemy_map.ws = self.ws
                # elif hdr in recv_funcs:
                # recv_funcs[hdr](websocket, self.msg["data"])
                elif hdr == "ready":
                    self.state += 1
                    self._preset()
                    print("ready or in_game preset")
                    print("WS ready or in game preset", self.ws)
                    print(self.msg)

                elif hdr == "in_game!!!":
                    self.turn = self.msg['data']['turn']
                    self.state += 1
                    print("state =", self.state)
                    self._preset()

                elif hdr == "miss":
                    self.turn = self.msg['data']['next_turn']
                    if self.msg['data']['shooted_on'] != self.username:
                        self.__Enemy_map.paintMiss(self.msg['data']['xn'], self.msg['data']['yn'],
                                                   self.msg['data']['tag'])
                    else:
                        self.__Map.paintMiss(self.msg['data']['xn'], self.msg['data']['yn'], self.msg['data']['tag'])

                elif hdr == "killed":
                    self.turn = self.msg['data']['next_turn']
                    if self.msg['data']['shooted_on'] != self.username:
                        self.__Enemy_map.paintCross(self.msg['data']['xn'], self.msg['data']['yn'],
                                                    self.msg['data']['tag'])
                    else:
                        self.__Map.paintCross(self.msg['data']['xn'], self.msg['data']['yn'], self.msg['data']['tag'])

                elif hdr == "endgame":
                    self.state += 1
                    if self.msg['data']['winner'] == self.username:
                        self.winner = True
                    self._preset()

                print("state =", self.state)

                print(self.msg, "checked")
                await asyncio.sleep(0.1)

    async def __check_data(self):
        self.host = self.ents[0][1].get()
        self.username = self.ents[1][1].get()
        if self.host != "" and self.username != "":
            self.ents[0][1].delete(0, 'end')
            self.ents[1][1].delete(0, "end")
            try:
                self.tasks.append(self.loop.create_task(self.ws_handler()))
                await asyncio.sleep(0.4)
                if len(self.msg) != 0:
                    if self.msg['header'] == "registered":
                        self.destroy_all()
                        self.state += 1
                        self.__Map.username = self.username
                        self.__Enemy_map.username = self.username
                        self._preset()

                        print("runned preset")
            except Exception as ex:
                print("Connection failure", ex)

    async def check_turn(self):
        while True:
            if self.turn == self.username:
                self.__Map.create_text()
                self.__Enemy_map.enable_shoot()
            else:
                self.__Map.remove_text()
                self.__Enemy_map.disable_shoot()
            await asyncio.sleep(0.1)


if __name__ == '__main__':
    async_loop = asyncio.get_event_loop()

    u = UserInterface(async_loop)
    async_loop.run_forever()
