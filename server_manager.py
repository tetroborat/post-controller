from server import Server
import config
server1 = Server(config.vk_api_token_all, config.vk_api_app_token, 189468050, "server1")
# vk_api_app_token - для доступа к внешним группам
# vk_api_token_all - токен для всего (сообщений, управления и тд)
# 189468050 - id сообщества-бота
# "server1" - имя сервера

try:
    server1.start()
except:
    print("Сервер упал, запустите его заново")
    input()