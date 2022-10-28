import asyncio
import json
from tkinter import Canvas, Button, S, Toplevel
from random import randrange
from Ship import Ship


class BattleMap:
    def __init__(self, width, height, loop: asyncio, master=None, user=True, ws=None):
        self.loop = loop
        self.master = master
        self.canvas_x = width
        self.canvas_y = height
        self.s_x = self.s_y = 10
        self.step_x = self.canvas_x // self.s_x
        self.step_y = self.canvas_y // self.s_y
        self.user = user
        self.user_ships = []
        self.indent = 2
        self.offset_x_user = 30
        self.gauge = 32
        self.offset_y = 40
        self.offset_x_comp = 430
        self.ws = ws
        self.username = None
        self.top_level = None
        self.shoot = False
        self.tmp_text = None

    def preset(self):
        if self.user:
            self.canvas = Canvas(self.master)
            self.canvas["height"] = self.canvas_y
            self.canvas["width"] = self.canvas_x
            self.canvas.pack()
            self.tmp_button = Button(self.canvas, text="Готов", command=self.__temp_b)
            self.tmp_button.place(x=182, y=417)
        else:
            self.top_level = Toplevel(self.master)
            self.canvas = Canvas(self.top_level)
            self.canvas["height"] = self.canvas_y
            self.canvas["width"] = self.canvas_x
            self.canvas.pack()
            self.canvas.bind("<Button-1>", self.shoot_f)

    def __temp_b(self):
        self.tmp_button.destroy()
        self.create_map(rebuild=True)
        self.paintShips()
        self.loop.create_task(self.__send_data())

    async def __send_data(self):
        data = []
        for i in self.user_ships:
            data.append(i.__dict__)
        await self.ws.send(json.dumps({"header": "send_map", 'data': {'map': data, 'username': self.username}}))

    def get_ships(self):
        return self.user_ships

    def shoot_f(self, e):
        self.loop.create_task(self.shoot_enemy(e))

    async def shoot_enemy(self, e):
        print("current tag", self.canvas.gettags("current"))
        print(e.x, e.y)
        if self.shoot:
            await self.ws.send(
                json.dumps({"header": "shoot", 'data': {'coords': {"x": e.x, "y": e.y}, 'username': self.username}}))

    def create_map(self, rebuild=False):
        self.canvas.delete('all')
        # добавление игровых полей пользователя и компьютера
        # создание поля для пользователя
        # перебор строк
        for i in range(10):
            # перебор столбцов
            for j in range(10):
                xn = j * self.gauge + (j + 1) * self.indent + self.offset_x_user
                xk = xn + self.gauge
                yn = i * self.gauge + (i + 1) * self.indent + self.offset_y
                yk = yn + self.gauge
                # добавление прямоугольника на холст с тегом в формате:
                # префикс_строка_столбец
                self.canvas.create_rectangle(xn, yn, xk, yk, tag="my_" + str(i) + "_" + str(j))
        # добавление букв и цифр
        for i in reversed(range(10)):
            # цифры пользователя
            xc = self.offset_x_user - 15
            yc = i * self.gauge + (i + 1) * self.indent + self.offset_y + round(self.gauge / 2)
            self.canvas.create_text(xc, yc, text=str(i + 1))

        # буквы
        symbols = "АБВГДЕЖЗИК"
        for i in range(10):
            # буквы пользователя
            xc = i * self.gauge + (i + 1) * self.indent + self.offset_x_user + round(self.gauge / 2)
            yc = self.offset_y - 15
            self.canvas.create_text(xc, yc, text=symbols[i])

        # генерация кораблей противника
        # генерация своих кораблей
        if self.user and not rebuild:
            self.createShips("my")

    def createShips(self, prefix="my", test=False):
        # функция генерации кораблей на поле
        # количество сгенерированных кораблей
        count_ships = 0

        while count_ships < 10:
            # массив занятых кораблями точек
            fleet_array = []
            # обнулить количество кораблей
            count_ships = 0
            # массив с флотом
            fleet_ships = []
            # генерация кораблей (length - палубность корабля)
            for length in reversed(range(1, 5)):
                # генерация необходимого количества кораблей необходимой длины
                for i in range(5 - length):
                    # генерация точки со случайными координатами, пока туда не установится корабль
                    try_create_ship = 0
                    while 1:
                        try_create_ship += 1
                        # если количество попыток превысило 50, начать всё заново
                        if try_create_ship > 50:
                            break
                        # генерация точки со случайными координатами
                        ship_point = prefix + "_" + str(randrange(10)) + "_" + str(randrange(10))
                        # случайное расположение корабля (либо горизонтальное, либо вертикальное)
                        orientation = randrange(2)
                        # создать экземпляр класса Ship
                        new_ship = Ship(length, orientation, ship_point)
                        # если корабль может быть поставлен корректно и его точки не пересекаются с уже занятыми точками поля
                        # пересечение множества занятых точек поля и точек корабля:
                        intersect_array = list(set(fleet_array) & set(new_ship.around_map + new_ship.coord_map))
                        if new_ship.ship_correct == 1 and len(intersect_array) == 0:
                            # добавить в массив со всеми занятыми точками точки вокруг корабля и точки самого корабля
                            fleet_array += new_ship.around_map + new_ship.coord_map
                            fleet_ships.append(new_ship)
                            count_ships += 1
                            break
        # отрисовка кораблей
        if len(fleet_ships) != 0:
            self.user_ships = fleet_ships.copy()
            #print(len(self.user_ships))
            if not test:
                self.paintShips()

        # метод для отрисовки кораблей

    def paintShips(self):
        # отрисовка кораблей
        for obj in self.user_ships:
            print(obj.coord_map)
            for point in obj.coord_map:
                self.canvas.itemconfig(point, fill="gray")

    def paintCross(self, xn, yn, tag):
        xk = xn + self.gauge
        yk = yn + self.gauge
        if self.user:
            self.canvas.itemconfig(tag, fill="white")
        self.canvas.create_line(xn + 2, yn + 2, xk - 2, yk - 2, width="3")
        self.canvas.create_line(xk - 2, yn + 2, xn + 2, yk - 2, width="3")

    # метод рисования промаха
    def paintMiss(self, xn, yn, point):
        # найти координаты
        # добавить прямоугольник
        # покрасить в белый
        st, x1, x2 = point.split('_')
        self.canvas.itemconfig(point, fill="white")
        self.canvas.create_oval(xn + 13, yn + 13, xn + 17, yn + 17, fill="blue")

    def enable_shoot(self):
        self.shoot = True

    def disable_shoot(self):
        self.shoot = False

    def create_text(self):
        if self.tmp_text is None:
            self.tmp_text = self.canvas.create_text(50, 500, text="SHOOT!!!", fill="black", font=('Helvetica 15 bold'))
            self.canvas.pack()

    def remove_text(self):
        if self.tmp_text is not None:
            self.canvas.delete(self.tmp_text)
            self.tmp_text = None
