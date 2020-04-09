#
# Серверное приложение для соединений
#
import asyncio
from asyncio import transports


class ServerProtocol(asyncio.Protocol):
    login: str = None #по умолчинию логин - пустой
    server: 'Server' #ссылка на класс, объявленный ниже - в одинарных кавычках
    transport: transports.Transport

    def __init__(self, server: 'Server'): #запуск сервера
        self.server = server

    def data_received(self, data: bytes): # Наследуется из asyncio.Protocol -  Protocol.data_received(data)
        decoded = data.decode(errors='ignore')

        if self.login is not None:
            if len(decoded.replace("\r\n", ""))>0:
                self.send_message(decoded) # отправляем декодированную строку пользователю
                print(f"{self.login}: {decoded}")  # Выводим декодированную строку
        else:
            if decoded.startswith("login:"):
                suggested_login = decoded.replace("login:", "").replace("\r\n", "")
                login_is_uniq = True
                for person in self.server.clients:
                    if person.login == suggested_login:
                        login_is_uniq = False
                        self.transport.write("This login already exists, please pick another\r\n".encode())
                if login_is_uniq: #если логин не повторяется
                    self.login = suggested_login #записываем его в свойства клиента
                    self.transport.write( #и приветвуем пользователя по имени
                        f"Welcome, {self.login}!\r\n".encode()
                        )
                    print(f"Welcome, {self.login}!") #выводим в консоль
                    self.send_history() #и отправляем новоприбывшему все сообщения из лога

            else:
                if len(decoded.replace("\r\n", "")) > 0:
                    self.transport.write("To use this chat you need login\r\nPlease enter it as 'login:<desired login>' and send to the chat\r\n".encode())

    def connection_made(self, transport: transports.Transport): # Наследуется из asyncio.Protocol (см. мануалы по asyncio)
        self.server.clients.append(self) # при установлении соединений добавляем нового клиента к списку
        self.transport = transport
        print("New client comes") # выводим в консоль уведомление о присоединении нового (пока анонимного) клиента

    def connection_lost(self, exception): # Наследуется из asyncio.Protocol (см. мануалы по asyncio)
        if self.login is None: #если пользователь решил отключиться, так и не представившись
            self.login = "Anonymous" #называем его анонимом
        print(f"{self.login} leaves") # и пишем в консоль, что пользователь ушел
        self.server.clients.remove(self) #удаляем ушедшего из списка подключенных клиентов


    def send_message(self, content: str): # метод отправки сообщений
        message = f"{self.login}: {content}\r\n" #сформировали текст для вывода
        self.server.messages.append(message) #записываем сообщение в лог
        if len(self.server.messages)>10: #если в логе стало больше 10 сообщений
            self.server.messages.pop(0) #самое давнее из них убираем
        for user in self.server.clients: #и рассылаем сообщение по всем клиентам того сервера, к которому подключен self
            user.transport.write(message.encode())

    def send_history(self): # метод отправки лога клиенту self
        for i in range(len(self.server.messages)):  # отправляем все сообщения из лога
            self.transport.write(self.server.messages[i].encode())


class Server:
    clients: list #подключенные клиенты
    messages: list #лог

    def __init__(self):
        self.clients = [] #подключенные клиенты
        self.messages = [] #лог

    def build_protocol(self):
        return ServerProtocol(self)

    async def start(self):
        loop = asyncio.get_running_loop() #ссылка на работающий в данный момент объект цикла

        coroutine = await loop.create_server( # корутина, которая создает TCP-сервер с указанным хостом и портом
            self.build_protocol,
            '127.0.0.1',
            8888
        )

        print("Server is ready...")

        await coroutine.serve_forever() #Начинает принимать соединения до тех пор, пока корутина не будет остановлена


process = Server()

try: #пример обработки исключения KeyboardInterrupt
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Server stopped")
