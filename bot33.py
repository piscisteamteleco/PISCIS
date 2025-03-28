import os
import asyncio
import random
import unicodedata
from dotenv import load_dotenv
from twitchio.ext import commands

# Cargar las variables del archivo .env
load_dotenv("token.env")

def normalize_text(text):
    """ Normaliza el texto, eliminando tildes y caracteres especiales """
    text = unicodedata.normalize('NFD', text)  # Descompone los caracteres acentuados
    text = ''.join([c for c in text if unicodedata.category(c) != 'Mn'])  # Elimina los caracteres de diacríticos (tildes)
    text = text.replace("¡", "").replace("!", "").replace("¿", "").replace("?", "")
    return text.lower()

class Bot(commands.Bot):

    def __init__(self):
        super().__init__(
            token=os.getenv("TWITCH_TOKEN"),  # Obtiene el token del archivo .env
            prefix="!",
            initial_channels=["piscisteleco"]
        )
        self.secret_word = None
        self.hint = None
        self.challenges = [
            ("PEP", "Es el nombre de nuestro pez en el sistema de acuaponía 🐟"),
            ("Acuaponia", "Es el sistema que combina acuicultura y hidroponía 🌱"),
            ("UPCT", "Universidad donde participamos en las Olimpiadas de Telecomunicaciones 🎓"),
            ("Oxígeno", "Es vital para que PEP pueda respirar en el agua 💨"),
            # Nuevos retos
            ("Corales", "Forman hábitats marinos y son clave para la vida submarina."),
            ("Mariposa", "Es un insecto que vuela, y tiene colores vibrantes en sus alas."),
            ("Océano", "Cubre más del 70% de la superficie terrestre."),
            ("Kraken", "Un monstruo marino legendario, gigante y temido por los marineros."),
            ("Delfín", "Un mamífero marino muy inteligente y social."),
            ("Alga", "Planta acuática que vive en el mar y es fundamental en la cadena alimenticia."),
            ("Tiburón", "Un depredador marino temido, conocido por sus afilados dientes."),
            ("Playa", "Un lugar donde el mar se encuentra con la tierra, lleno de arena y sol."),
            ("Medusa", "Un animal marino con tentáculos venenosos."),
            ("Ballena", "El animal más grande del planeta, vive en los océanos."),
            ("Océano Pacífico", "El océano más grande y profundo del mundo."),
            ("Mar de Coral", "Es un mar cálido famoso por su biodiversidad marina."),
            ("Pescador", "Alguien que pesca para ganarse la vida o como hobby."),
            ("Marea", "Movimiento regular del agua del mar, causado por la gravedad."),
            ("Isla", "Una porción de tierra rodeada de agua."),
            ("Anémona", "Una especie de animal marino que vive cerca de los corales."),
            ("Estrella de mar", "Un animal marino con forma estrellada y tentáculos."),
            ("Naufragio", "Cuando un barco se hunde en el mar."),
            ("Marisco", "Almejas, mejillones y camarones son ejemplos de estos deliciosos manjares marinos."),
        ]
        self.user_points = {}  # Diccionario para almacenar puntos de los usuarios

    async def event_ready(self):
        print(f'✅ Bot conectado como {self.nick}')
        self.loop.create_task(self.challenge_task())  # Inicia la tarea de los retos

    async def event_message(self, message):
        if not message.content:
            return

        if message.author.name.lower() == self.nick.lower():
            return  # Evita responderse a sí mismo

        print(f'Mensaje recibido: {message.content}')
        await self.handle_commands(message)  # Procesa los comandos

        msg_normalized = normalize_text(message.content)  # Normalizamos el texto

        # Respuestas a palabras clave sobre el proyecto
        if "acuaponia" in msg_normalized:
            await message.channel.send("🌿 La acuaponía es un sistema que combina el cultivo de plantas y peces en un mismo ecosistema.")
        elif "pep" in msg_normalized:
            await message.channel.send("🐟 PEP es nuestro pez estrella, tiene 1 mes y medio de vida en nuestro sistema de acuaponía.")
        elif "olimpiadas" in msg_normalized or "upct" in msg_normalized:
            await message.channel.send("🏆 Estamos participando en las Olimpiadas de Telecomunicaciones de la UPCT con este proyecto!")

        # Más interacción con palabras clave divertidas
        elif "agua" in msg_normalized:
            await message.channel.send("💧 ¡El agua es fundamental para nuestro sistema de acuaponía!")
        elif "pez" in msg_normalized:
            await message.channel.send("🐠 ¡Los peces son clave en la acuaponía, y PEP es el más crack!")
        elif "plantas" in msg_normalized:
            await message.channel.send("🌱 ¡Las plantas crecen gracias a los nutrientes del agua!")

        # Comprobación de retos
        if self.secret_word and normalize_text(self.secret_word) in msg_normalized:
            await message.channel.send(f'🎉 {message.author.name} ha acertado la palabra secreta: {self.secret_word} 🎊')
            # Sumar puntos por respuesta correcta
            if message.author.name not in self.user_points:
                self.user_points[message.author.name] = 0
            self.user_points[message.author.name] += 10  # Sumar 10 puntos
            self.secret_word = None  # Resetea el reto

    @commands.command()
    async def ranking(self, ctx):
        """ Comando para ver el ranking de puntos """
        ranking = sorted(self.user_points.items(), key=lambda x: x[1], reverse=True)
        ranking_msg = "🏆 **Ranking de puntos** 🏆\n"
        for idx, (user, points) in enumerate(ranking, 1):
            ranking_msg += f"{idx}. {user}: {points} puntos \n"
        await ctx.send(ranking_msg)

    @commands.command()
    async def reglas(self, ctx):
        """ Comando para mostrar las reglas del juego """
        reglas_msg = (
            "📜 **Reglas del juego** 📜\n"
            "1. El bot hace retos periódicos donde debes adivinar una palabra secreta.\n"
            "2. Si adivinas correctamente, ganarás puntos.\n"
            "3. Los puntos se suman a tu cuenta personal, ¡y puedes ver tu ranking!\n"
            "4. Usa el comando '!ranking' para ver quién tiene más puntos.\n"
            "5. ¡Diviértete aprendiendo sobre acuaponía y el mar!"
        )
        await ctx.send(reglas_msg)

    async def challenge_task(self):
        while True:
            await asyncio.sleep(90)  # Espera 5 minutos entre retos
            self.secret_word, self.hint = random.choice(self.challenges)
            await self.connected_channels[0].send(f'🎯 ¡Nuevo reto! Adivina la palabra secreta. Pista: {self.hint}')

bot = Bot()
bot.run()
