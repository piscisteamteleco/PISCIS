from twitchio.ext import commands

class Bot(commands.Bot):

    def __init__(self):
        super().__init__(
            token="a5s3ye7q0ew6rztahpve9puwgiezlu",  # Asegúrate de que el token es válido
            client_id="gp762nuuoqcoxypju8c569th9wz7q5",
            prefix="!",
            initial_channels=["piscisteleco"]  # Asegúrate de que el canal es correcto
        )

    async def event_ready(self):
        print(f'✅ Bot conectado como {self.nick}')

    async def event_message(self, message):
        if message.author.name.lower() == self.nick.lower():
            return  # Evita que el bot responda a sí mismo

        print(f'Mensaje recibido: {message.content}')  

        mensaje_limpio = message.content.lower().strip()  # Normaliza el mensaje

        # Responde a palabras clave específicas
        if "hola" in mensaje_limpio:
            await message.channel.send(f'👋 Hola {message.author.name}!')

        if "nombre" in mensaje_limpio:
            await message.channel.send(f'👋 Hola {message.author.name}, me llamo PEP!')

bot = Bot()
bot.run()
