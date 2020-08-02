from datetime import datetime

import vk_api.vk_api
import time
import datetime
import telebot

from sys import exit
from threading import Thread
from vk_api.bot_longpoll import VkBotLongPoll
from vk_api.bot_longpoll import VkBotEventType
from vk_api.utils import get_random_id
from dateutil.tz import tzoffset
from vk_api.keyboard import VkKeyboard, VkKeyboardColor


class Server:

    def __init__(self, api_token, api_app_token, group_id, server_name: str = "Empty"):
        # Даем серверу имя
        self.server_name = server_name

        # Для Long Poll
        self.vk = vk_api.VkApi(token=api_token)

        # Для использования Long Poll API
        self.long_poll = VkBotLongPoll(self.vk, group_id)

        # Для вызова методов vk_api
        self.vk_api = self.vk.get_api()

        # Для проверки постов других групп
        self.vk_api_app = vk_api.VkApi(token=api_app_token).get_api()

        self.users = {}
        self.kill = False
        self.keyboard = self.add_keyboard()
        self.last_function = None

        print('Сервер поднят!')

    def add_keyboard(self):

        keyboard = VkKeyboard(one_time=True)

        keyboard.add_button('Добавить сообщества', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Удалить сообщества', color=VkKeyboardColor.POSITIVE)
        keyboard.add_line()
        keyboard.add_button('Изменить частоту', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('Изменить интервал', color=VkKeyboardColor.POSITIVE)
        keyboard.add_line()
        keyboard.add_button('Прекратить контроль', color=VkKeyboardColor.POSITIVE)

        return keyboard.get_keyboard()

    def send_message(self, send_id, message, type):

        if type == 'default':
            self.vk_api.messages.send(user_id=send_id,
                                      random_id=get_random_id(),
                                      message=message,
                                      keyboard=self.keyboard)
        elif type == 'none':
            self.vk_api.messages.send(user_id=send_id,
                                      random_id=get_random_id(),
                                      message=message)
        elif type == 'begin':
            kb = VkKeyboard(one_time=True)
            kb.add_button('Начать', color=VkKeyboardColor.POSITIVE)
            self.vk_api.messages.send(user_id=send_id,
                                      random_id=get_random_id(),
                                      message=message,
                                      keyboard=kb.get_keyboard())

    def send_link(self, domain_or_id):
        try:
            domain_or_id = int(domain_or_id)
            return "https://vk.com/public{}".format(domain_or_id)
        except:
            return "https://vk.com/{}".format(domain_or_id)

    def send_img(self, peer_id, attachment):
        """attachment: id фотографии, например photo-164304930_457254346"""
        self.vk_api.messages.send(peer_id=peer_id,
                                  random_id=get_random_id(),
                                  attachment=attachment)

    def get_user_name(self, user_id):
        """ Получаем имя пользователя"""
        return self.vk_api.users.get(user_id=user_id)[0]['first_name']

    def get_user_city(self, user_id):
        """ Получаем город пользователя"""
        try:
            return self.vk_api.users.get(user_id=user_id, fields="city")[0]["city"]['title']
        except:
            return "unknown"

    def seconds_to_str(self, seconds):
        mm, ss = divmod(seconds, 60)
        hh, mm = divmod(mm, 60)
        return "%02d:%02d:%02d" % (hh, mm, ss)

    def print_name_interlocutor(self, event):
        print("Username: " + self.get_user_name(event.object.message['from_id']))
        print("From: " + self.get_user_city(event.object.message['from_id']))
        print("Text: " + event.object.message['text'])
        print("Type: ", end="")
        if event.object.message['id'] > 0:
            print("private message")
        else:
            print("group message")
        print(" --- ")

    def sleep_night(self, alarm_time, n, sleep_time, user_id):
        now = datetime.datetime.now().astimezone(tzoffset("UTC+{}".format(n), n * 3600))
        if now.hour < alarm_time.hour+1:
            then = datetime.datetime(now.year, now.month, now.day, alarm_time.hour, alarm_time.minute, tzinfo=tzoffset("UTC+{}".format(n), n * 3600))
        else:
            then = now + datetime.timedelta(days=1)
            then = datetime.datetime(then.year, then.month, then.day, alarm_time.hour, alarm_time.minute, tzinfo=tzoffset("UTC+{}".format(n), n * 3600))
        for i in range(int((then-now).total_seconds()/30)):
            if alarm_time == self.users[user_id][4] and sleep_time == self.users[user_id][5]:
                time.sleep(30)
            else:
                break

    def alarm(self, datetime_last_post, interval, n, user_id):
        datetime_last_post = datetime.datetime.fromtimestamp(datetime_last_post).astimezone(tzoffset("UTC+{}".format(n), n * 3600))
        then = datetime_last_post + datetime.timedelta(hours=interval.hour, minutes=interval.minute)
        now = datetime.datetime.now().astimezone(tzoffset("UTC+{}".format(n), n * 3600))
        if (then-now).total_seconds()>0:
            for i in range(int((then-now).total_seconds()/10)):
                if interval == self.users[user_id][3]:
                    time.sleep(10)
                else:
                    break
        else:
            for i in range(interval.hour*360 + interval.minute*6):
                if interval == self.users[user_id][3]:
                    time.sleep(10)
                else:
                    break

    def check_post(self, user_id, domain, n):
        """id пользователя, домен группы, периодичность постов, с какого по какое время выходят посты, часовой пояс UTC+n"""
        try:
            while True:
                if self.users[user_id][4] < datetime.datetime.now().astimezone(tzoffset("UTC+{}".format(n), n * 3600)).time() < self.users[user_id][5]:
                    try:
                        response = self.vk_api_app.wall.get(owner_id=-int(domain), count=2, extended=1)  # Используем метод wall.get
                    except:
                        response = self.vk_api_app.wall.get(domain=domain, count=2, extended=1)
                    if response['items']:
                        try:
                            if response['items'][0]['is_pinned'] and datetime.datetime.now().astimezone(tzoffset("UTC+{}".format(n), n * 3600)).timestamp() - response['items'][1]['date'] > self.users[user_id][3].hour*3600 + self.users[user_id][3].minute*60:
                                self.send_message(user_id, 'С момента публикации последнего поста в сообщетве "' + response['groups'][0]['name'] + '" прошло '
                                                  + str(self.seconds_to_str(datetime.datetime.now().astimezone(tzoffset("UTC+{}".format(n), n * 3600)).timestamp()
                                                  - response['items'][1]['date'])) + '\n' + self.send_link(domain),'default')
                            self.alarm(response['items'][1]['date'], self.users[user_id][3], n, user_id)
                        except:
                            if datetime.datetime.now().astimezone(tzoffset("UTC+{}".format(n), n * 3600)).timestamp() - response['items'][0]['date'] > self.users[user_id][3].hour*3600 + self.users[user_id][3].minute*60:
                                self.send_message(user_id, 'С момента публикации последнего поста в сообществе "' + response['groups'][0]['name'] + '" прошло '
                                                  + str(self.seconds_to_str(datetime.datetime.now().astimezone(tzoffset("UTC+{}".format(n), n * 3600)).timestamp()
                                                  - response['items'][0]['date'])) + '\n' + self.send_link(domain),'default')
                            self.alarm(response['items'][0]['date'], self.users[user_id][3], n, user_id)
                else:
                    self.sleep_night(self.users[user_id][4], n, self.users[user_id][5], user_id)
        except KeyError:
            0

    def listening_server(self):
        while not self.kill:
            for event in self.long_poll.listen():  # Слушаем сервер
                try:
                    if event.type == VkBotEventType.MESSAGE_NEW:
                        # Пришло новое сообщение
                        from_id = event.object.message['from_id']
                        text = event.object.message['text']
                        if not from_id in self.users:
                            if text == "Начать":
                                self.send_message(from_id,
                                f"Здравствуй, {self.get_user_name(from_id)}! "
                                f"Для контроля постов групп отправь мне их домены или id через пробел", 'none')
                            else:
                                self.users.update({from_id:
                                    [self.get_user_name(from_id), event.object.message['peer_id'],
                                     text.split(' ')]})
                                for i in range(3):
                                    self.users[from_id].append(None)
                                self.send_message(from_id, "Укажите в какое время должны опубликовываться новости в формате ЧЧ:ММ-ЧЧ:ММ", 'none')
                                self.last_function = 'Укажите в какое время должны опубликовываться новости в формате ЧЧ:ММ-ЧЧ:ММ'

                        else:
                            if text == 'убить':
                                self.kill = True
                                print('убит')
                                exit()
                            elif self.last_function == 'Укажите в какое время должны опубликовываться новости в формате ЧЧ:ММ-ЧЧ:ММ':
                                self.users[from_id][4], self.users[from_id][5] = list(map(lambda x: datetime.datetime.strptime(x, "%H:%M").time(), text.split("-")))
                                self.send_message(from_id, "Теперь введите частоту контроля в формате ЧЧ:ММ", 'none')
                                self.last_function = 'Теперь введите частоту контроля в формате ЧЧ:ММ'
                            elif self.last_function == 'Теперь введите частоту контроля в формате ЧЧ:ММ':
                                self.users[from_id][3] = (datetime.datetime.strptime(text, "%H:%M").time())
                                self.send_message(from_id, "Готово! Теперь я буду смотреть, чтобы посты выходили через каждые " + text[:2]+"ч"+text[3:] + "мин, и буду писать, если выход очередного поста запозднится.",'default')
                                self.last_function = None
                                self.control_groups(from_id, self.users[from_id][2])
                                print('Пользователь ' + str(from_id) + ' обслуживается')
                            elif self.last_function == 'Добавить сообщества':
                                self.control_groups(from_id, list(set(text.split(' ')) - set((self.users[from_id][2]))))
                                self.users[from_id][2] = list(set(text.split(' ') + (self.users[from_id][2])))
                                self.send_message(from_id, "Список сообществ расширен",'default')
                                self.last_function = None
                                print(f"Пользователь {from_id} добавил группы {text.split(' ')} в список")
                            elif self.last_function == 'Изменить частоту':
                                self.users[from_id][3] = (datetime.datetime.strptime(text, "%H:%M").time())
                                self.send_message(from_id, "Частота изменена",'default')
                                self.last_function = None
                                print(f"Пользователь {from_id} изменил частоту")
                            elif self.last_function == 'Удалить сообщества':
                                self.users[from_id][2] = list(set(self.users[from_id][2]) - set(text.split(' ')))
                                self.send_message(from_id, "Сообщества удалены из списка контролируемых", 'default')
                                self.last_function = None
                                print(f"Пользователь {from_id} удалил сообщества {text.split(' ')} из списка")
                            elif self.last_function == 'Изменить интервал':
                                self.users[from_id][4], self.users[from_id][5] = list(
                                    map(lambda x: datetime.datetime.strptime(x, "%H:%M").time(), text.split("-")))
                                self.send_message(from_id,"Время контроля изменено", 'default')
                                self.last_function = None
                                print(f"Пользователь {from_id} изменил интервал")

                            elif text == "Добавить сообщества":
                                self.send_message(from_id, "Введите через пробел домены или id сообществ, которые хотите контролировать", 'none')
                                self.last_function = 'Добавить сообщества'
                            elif text == "Прекратить контроль":
                                self.users.pop(from_id)
                                self.send_message(from_id, "Контроль прекращен",'begin')
                                print(f"Пользователь {from_id} прекратил контроль")
                            elif text == "Изменить частоту":
                                self.send_message(from_id, "Введите максимальную разницу по времени между постами в формате ЧЧ:ММ", 'none')
                                self.last_function = 'Изменить частоту'
                            elif text == 'Удалить сообщества':
                                self.send_message(from_id, "Введите через пробел домены или id сообществ, которые больше не нужно контролировать", 'none')
                                self.last_function = 'Удалить сообщества'
                            elif text == "Изменить интервал":
                                self.send_message(from_id, "Введите интервал, во время которого должны опубликовываться новости в формате ЧЧ:ММ-ЧЧ:ММ", 'none')
                                self.last_function = 'Изменить интервал'


                except:
                    self.users.pop(event.object.message['from_id'])
                    self.send_message(event.object.message['from_id'],'На сервере произошла ошибка, вся информация об интересующем Вас контроле удалена','begin')

    def control_groups(self, user_id, domains):
        for domain in domains:
            print('Контроль ' + domain + ' для ' + str(user_id) + ' запущен')
            Thread(target=self.check_post, args=(user_id, domain, 3)).start()

    def start(self):
        self.listening_server()