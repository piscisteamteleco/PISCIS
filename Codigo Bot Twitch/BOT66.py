import os
import time
import asyncio
import random
import unicodedata
from dotenv import load_dotenv
from twitchio.ext import commands

load_dotenv("token.env")

def normalize_text(text):
    text = unicodedata.normalize('NFD', text)
    text = ''.join([c for c in text if unicodedata.category(c) != 'Mn'])
    text = text.replace("¡", "").replace("!", "").replace("¿", "").replace("?", "")
    return text.lower().strip()

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=os.getenv("TWITCH_TOKEN"),
            prefix="!",
            initial_channels=["piscisteleco"]
        )
        self.secret_question = None
        self.secret_answer = None
        self.user_points = {}
        self.duelo = None
        self.duelo_active = False
        self.question_pool = [
            ("¿Capital de Francia?", "paris"),
            ("¿Color del cielo?", "azul"),
            ("¿Animal que ladra?", "perro"),
            ("¿Principal satélite de la Tierra?", "luna"),
            ("¿Elemento químico H2O?", "agua"),
            ("¿Número de patas de una araña?", "ocho"),
            ("¿Animal rey de la selva?", "leon"),
            ("¿Montaña más alta?", "everest"),
            ("¿País con forma de bota?", "italia"),
            ("¿Lenguaje hablado en Brasil?", "portugues"),
            ("¿Nombre del creador de Microsoft?", "bill gates"),
            ("¿Planeta rojo?", "marte"),
            ("¿Instrumento con cuerdas?", "guitarra"),
            ("¿Mes con Navidad?", "diciembre"),
            ("¿Fruta amarilla curva?", "platano"),
            ("¿Animal que maúlla?", "gato"),
            ("¿Comida hecha con harina y tomate?", "pizza"),
            ("¿Día después del viernes?", "sabado"),
            ("¿Cosa que usas para escribir?", "lapiz"),
            ("¿Color de la sangre?", "rojo"),
            ("¿Nombre del océano más grande?", "pacifico"),
            ("¿Lugar donde hay arena y mar?", "playa"),
            ("¿Bebida caliente con cafeína?", "cafe"),
            ("¿Qué se usa para ver mejor a distancia?", "gafas"),
            ("¿Día de los enamorados?", "san valentin"),
            ("¿Animal con trompa?", "elefante"),
            ("¿País de los canguros?", "australia"),
            ("¿Dios del trueno nórdico?", "thor"),
            ("¿Color del pasto?", "verde"),
            ("¿Animal que pone huevos y vuela?", "pajaro"),
            ("¿Animal lento con caparazón?", "tortuga"),
            ("¿Lenguaje de España?", "espanol"),
            ("¿Pieza de ajedrez más importante?", "rey"),
            ("¿Mes con Halloween?", "octubre"),
            ("¿Cosa que da luz por la noche?", "luna"),
            ("¿Nombre del detective de Sherlock?", "watson"),
            ("¿Comida que viene del maíz?", "palomitas"),
            ("¿Animal que salta y vive en charcos?", "rana"),
            ("¿Red social de videos cortos?", "tiktok"),
            ("¿Forma del balón de fútbol?", "esfera"),
            ("¿Metal usado en cables eléctricos?", "cobre"),
            ("¿Gas necesario para respirar?", "oxigeno"),
            ("¿Comida italiana con salsa?", "pasta"),
            ("¿Nombre del ratón de Disney?", "mickey"),
            ("¿Estrella del sistema solar?", "sol"),
            ("¿Cereal que se come en la mañana?", "avena"),
            ("¿Nombre del mago de Hogwarts?", "harry"),
            ("¿Cosa que muestra la hora?", "reloj"),
            ("¿Vehículo con dos ruedas?", "bicicleta")
        ]
        self.challenge_task_running = False

    async def event_ready(self):
        print(f'✅ Bot conectado como {self.nick}')
        if not self.challenge_task_running:
            self.loop.create_task(self.challenge_task())
            self.loop.create_task(self.reminder_task())
            self.challenge_task_running = True

    async def event_message(self, message):
        if not message.content or message.author.name.lower() == self.nick.lower():
            return

        await self.handle_commands(message)

        msg_normalized = normalize_text(message.content)

        if "hola" in msg_normalized:
            await message.channel.send(f"👋 ¡Hola, {message.author.name}! ¿Listo para aprender y jugar?")

        if self.secret_answer:
            if msg_normalized == normalize_text(self.secret_answer):
                user = message.author.name
                self.user_points[user] = self.user_points.get(user, 0) + 5
                await message.channel.send(f"🎉 ¡Correcto, {user}! Has ganado 5 puntos.")
                self.secret_question = None
                self.secret_answer = None

        if self.duelo_active and self.duelo:
            correct_answer = normalize_text(self.duelo['current_answer'])
            if msg_normalized == correct_answer and message.author.name in [self.duelo['p1'], self.duelo['p2']]:
                await self.register_duel_answer(message.author.name, message.channel)

    @commands.command()
    async def comandos(self, ctx):
        msg = (
            "📜 **Comandos disponibles** 📜\n"
            "!duelo @usuario – Reta a otro usuario a un duelo de trivia (Bo5)\n"
            "!acepto – Acepta un duelo\n"
            "!ranking – Muestra el ranking de puntos\n"
            "!reglas – Muestra las reglas del juego\n"
            "¡Y saluda con 'hola' para una sorpresa!"
        )
        await ctx.send(msg)

    @commands.command()
    async def reglas(self, ctx):
        reglas_msg = (
            "📜 **Reglas del juego** 📜\n"
            "1. Adivina palabras o responde preguntas para ganar puntos.\n"
            "2. Puedes retar a otros con !duelo.\n"
            "3. Los duelos son al mejor de 5 preguntas.\n"
            "4. Usa !ranking para ver tu puntuación.\n"
            "5. ¡Diviértete y aprende con el proyecto Piscis!"
        )
        await ctx.send(reglas_msg)

    @commands.command()
    async def ranking(self, ctx):
        ranking = sorted(self.user_points.items(), key=lambda x: x[1], reverse=True)
        if not ranking:
            await ctx.send("Nadie tiene puntos todavía :(")
            return
        ranking_msg = "🏆 **Ranking de puntos** 🏆\n"
        for idx, (user, points) in enumerate(ranking, 1):
            ranking_msg += f"{idx}. {user}: {points} puntos\n"
        await ctx.send(ranking_msg)

    @commands.command()
    async def duelo(self, ctx):
        if self.duelo_active:
            await ctx.send("⚠️ Ya hay un duelo en curso. Espera a que termine.")
            return

        content = ctx.message.content.strip().split()
        if len(content) < 2:
            await ctx.send("Usa el comando así: !duelo @usuario")
            return

        target = content[1].lstrip('@')
        self.duelo = {
            'p1': ctx.author.name,
            'p2': target,
            'score': {ctx.author.name: 0, target: 0},
            'round': 0,
            'current_answer': None,
            'accepted': False,
            'channel': ctx.channel
        }
        await ctx.send(f"⚔️ {ctx.author.name} ha retado a {target} a un duelo de trivia. {target}, escribe !acepto para comenzar.")

    @commands.command()
    async def acepto(self, ctx):
        if not self.duelo or self.duelo['p2'] != ctx.author.name:
            return

        self.duelo['accepted'] = True
        self.duelo_active = True
        await ctx.send(f"✅ {ctx.author.name} ha aceptado el duelo. ¡Que empiece el juego! 🧠")
        await asyncio.sleep(2)
        await self.next_duel_round()

    async def next_duel_round(self):
        if not self.duelo:
            return

        self.duelo['round'] += 1
        question, answer = random.choice(self.question_pool)
        self.duelo['current_answer'] = answer
        await self.duelo['channel'].send(f"❓ Ronda {self.duelo['round']}: {question}")

    async def register_duel_answer(self, winner, channel):
        self.duelo['score'][winner] += 1
        await channel.send(f"🎯 {winner} respondió correctamente y gana la ronda!")
        await asyncio.sleep(1)

        if self.duelo['score'][winner] == 3:
            self.duelo_active = False
            self.user_points[winner] = self.user_points.get(winner, 0) + 15
            await channel.send(f"🏆 {winner} ha ganado el duelo al mejor de 5! +15 puntos 🎉")
            self.duelo = None
        else:
            await self.next_duel_round()

    async def challenge_task(self):
        while True:
            await asyncio.sleep(180)  # Cada 3 minutos
            if not self.secret_answer:
                question, answer = random.choice(self.question_pool)
                self.secret_question = question
                self.secret_answer = answer
                await self.connected_channels[0].send(f"🧠 Pregunta rápida: {question}")

    async def reminder_task(self):
        while True:
            await asyncio.sleep(600)
            await self.connected_channels[0].send("¿Ya conoces los comandos? Usa !comandos para saber todo lo que puedes hacer ✨")

# Bucle principal con autoreinicio
while True:
    try:
        bot = Bot()
        bot.run()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("🔁 Reiniciando bot en 5 segundos...")
        time.sleep(5)
