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
        self.secret_hint = None
        self.user_points = {}
        self.duelo = None
        self.duelo_active = False
        self.challenge_task_running = False

        self.question_pool = [
            ("¿Cómo se llama el pez que ayuda a limpiar el acuario?", "pleco", "Es un pez que vive pegado al vidrio"),
            ("¿Qué planta flota en el agua y da sombra a los peces?", "lenteja", "Su nombre también es una legumbre"),
            ("¿Qué animal produce el abono en acuaponia?", "pez", "Vive en el agua y nada"),
            ("¿Cómo se llama el proceso que convierte los desechos del pez en nutrientes para las plantas?", "nitrificacion", "Empieza con 'nitri'"),
            ("¿Qué líquido necesitan los peces para vivir?", "agua", "Lo bebes todos los días"),
            ("¿Qué parte de la planta absorbe el agua y nutrientes?", "raiz", "Está debajo de la tierra o flotando en el agua"),
            ("¿Qué gas necesitan los peces para respirar?", "oxigeno", "También lo respiras tú"),
            ("¿Dónde crecen las plantas en un sistema de acuaponia?", "agua", "No es tierra"),
            ("¿Qué animal marino tiene ocho patas?", "pulpo", "Empieza por 'pul'"),
            ("¿Cómo se llama el mar más cercano a España?", "mediterraneo", "Empieza por 'medi'"),
            ("¿Qué pez es famoso por inflarse?", "pez globo", "Cuando se asusta, se hincha"),
            ("¿Qué es lo que más contamina el océano?", "plastico", "Está en muchas botellas y bolsas"),
            ("¿Qué dispositivo usamos para medir el pH del agua?", "phmetro", "Tiene 'ph' en el nombre"),
            ("¿Qué concurso promueve ideas tecnológicas entre jóvenes?", "olimpiadas", "Es una competencia escolar"),
            ("¿Qué órgano usan los peces para respirar?", "branquias", "Están en los lados de su cabeza"),
            ("¿Qué parte del océano es la más profunda?", "fosa", "Fosa de las Marianas, por ejemplo"),
            ("¿Qué día se celebra el Día Mundial del Agua?", "22 marzo", "Es en marzo"),
            ("¿Qué tipo de energía se usa a veces en sistemas sostenibles?", "solar", "Viene del sol"),
            ("¿Qué especie vegetal crece bien en acuaponia y se usa en ensaladas?", "lechuga", "Empieza con L"),
            ("¿Qué es un NFT en el contexto de las Olimpiadas de Telecomunicaciones?", "tecnologia", "No es arte, es...")
        ]

    async def event_ready(self):
        print(f'Bot conectado como {self.nick}')
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
            await message.channel.send(f"Hola, {message.author.name}. ¿Listo para aprender algo nuevo?")

        if self.secret_answer:
            if msg_normalized == normalize_text(self.secret_answer):
                user = message.author.name
                self.user_points[user] = self.user_points.get(user, 0) + 5
                await message.channel.send(f"Correcto, {user}. Has ganado 5 puntos.")
                self.secret_question = None
                self.secret_answer = None
                self.secret_hint = None

        if self.duelo_active and self.duelo:
            correct_answer = normalize_text(self.duelo['current_answer'])
            if msg_normalized == correct_answer and message.author.name in [self.duelo['p1'], self.duelo['p2']]:
                await self.register_duel_answer(message.author.name, message.channel)

    @commands.command()
    async def comandos(self, ctx):
        msg = (
            "**Comandos disponibles**\n"
            "!duelo @usuario – Reta a otro usuario a un duelo de trivia (Bo5)\n"
            "!acepto – Acepta un duelo\n"
            "!ranking – Muestra el ranking de puntos\n"
            "!reglas – Muestra las reglas del juego\n"
            "!pista – Pide una pista de la pregunta actual\n"
        )
        await ctx.send(msg)

    @commands.command()
    async def reglas(self, ctx):
        reglas_msg = (
            "**Reglas del juego**\n"
            "1. Adivina palabras o responde preguntas para ganar puntos.\n"
            "2. Puedes retar a otros con !duelo.\n"
            "3. Los duelos son al mejor de 5 preguntas.\n"
            "4. Usa !ranking para ver tu puntuación.\n"
            "5. Usa !pista si necesitas ayuda.\n"
            "6. ¡Diviértete y aprende con el proyecto Piscis!"
        )
        await ctx.send(reglas_msg)

    @commands.command()
    async def ranking(self, ctx):
        ranking = sorted(self.user_points.items(), key=lambda x: x[1], reverse=True)
        if not ranking:
            await ctx.send("Nadie tiene puntos todavía.")
            return
        ranking_msg = "**Ranking de puntos**\n"
        for idx, (user, points) in enumerate(ranking, 1):
            ranking_msg += f"{idx}. {user}: {points} puntos\n"
        await ctx.send(ranking_msg)

    @commands.command()
    async def pista(self, ctx):
        if self.secret_question and self.secret_hint:
            await ctx.send(f"Pista: {self.secret_hint}")
        else:
            await ctx.send("No hay ninguna pregunta activa ahora mismo.")

    @commands.command()
    async def duelo(self, ctx):
        if self.duelo_active:
            await ctx.send("Ya hay un duelo en curso. Espera a que termine.")
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
        await ctx.send(f"{ctx.author.name} ha retado a {target} a un duelo de trivia. {target}, escribe !acepto para comenzar.")

    @commands.command()
    async def acepto(self, ctx):
        if not self.duelo or self.duelo['p2'] != ctx.author.name:
            return

        self.duelo['accepted'] = True
        self.duelo_active = True
        await ctx.send(f"{ctx.author.name} ha aceptado el duelo. Comienza el juego.")
        await asyncio.sleep(2)
        await self.next_duel_round()

    async def next_duel_round(self):
        if not self.duelo:
            return

        self.duelo['round'] += 1
        question, answer, _ = random.choice(self.question_pool)
        self.duelo['current_answer'] = answer
        await self.duelo['channel'].send(f"Ronda {self.duelo['round']}: {question}")

    async def register_duel_answer(self, winner, channel):
        self.duelo['score'][winner] += 1
        await channel.send(f"{winner} respondió correctamente y gana la ronda.")
        await asyncio.sleep(1)

        if self.duelo['score'][winner] == 3:
            self.duelo_active = False
            self.user_points[winner] = self.user_points.get(winner, 0) + 15
            await channel.send(f"{winner} ha ganado el duelo al mejor de 5. Gana 15 puntos.")
            self.duelo = None
        else:
            await self.next_duel_round()

    async def challenge_task(self):
        await self.wait_for_ready()
        while True:
            await asyncio.sleep(180)
            if not self.secret_answer:
                question, answer, hint = random.choice(self.question_pool)
                self.secret_question = question
                self.secret_answer = answer
                self.secret_hint = hint
                await self.connected_channels[0].send(f"Pregunta rápida: {question}")

    async def reminder_task(self):
        await self.wait_for_ready()
        while True:
            await asyncio.sleep(600)
            await self.connected_channels[0].send("¿Ya conoces los comandos? Usa !comandos para saber todo lo que puedes hacer.")

# Bucle principal con autoreinicio
while True:
    try:
        bot = Bot()
        bot.run()
    except Exception as e:
        print(f"Error: {e}")
        print("Reiniciando bot en 5 segundos...")
        time.sleep(5)
