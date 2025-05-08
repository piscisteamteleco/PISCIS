import os
import time
import asyncio
import random
import unicodedata
import requests
from dotenv import load_dotenv
from twitchio.ext import commands

# Carga tus tokens y llaves desde el archivo token.env
load_dotenv("token.env")

# Configuración de ThingSpeak (para el LED)
THINGSPEAK_WRITE_KEY = os.getenv("THINGSPEAK_WRITE_KEY")

# Colores disponibles y sus códigos hex
COLOR_MAP = {
    "ROJO": "FF0000",
    "AZUL": "0000FF",
    "AMARILLO": "FFFF00",
    "VERDE": "00FF00",
    "NARANJA": "FFA500",
    "MORADO": "800080",
    "BLANCO": "FFFFFF",
    "ROSA": "FFC0CB",
    "ARCOIRIS": "RAINBOW"
}

# Saca tildes y pasa todo a minúsculas para comparar respuestas
def normalize_text(text):
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = ''.join(c for c in text if c.isalnum() or c.isspace())
    return text.lower().strip()

class Bot(commands.Bot):
    def __init__(self):
        # Ajusta tu token, prefijo y canal
        super().__init__(
            token=os.getenv("TWITCH_TOKEN"),
            prefix="!",
            initial_channels=["piscisteleco"]
        )

        # Pregunta rápida cada X minutos
        self.secret_question = None
        self.secret_answer = None
        self.secret_hint = None

        # Para sumar puntos a usuarios
        self.user_points = {}

        # Datos del duelo
        self.duelo = None
        self.duelo_active = False

        # Para que las tareas de preguntas y recordatorios solo arranquen una vez
        self.challenge_task_running = False

        # Estado de la 'locura' en chat
        self.locura_active = False

        # Guarda preguntas ya usadas en duelo
        self.used_questions = set()

        # Para evitar repetir color de LED
        self.current_led_color = None

        # Banco de preguntas (puedes agregar más)
        self.question_pool = [
            ("¿De qué color es el cielo durante un día despejado?", "azul", "Pista: es el mismo color del mar."),
            ("¿Qué parte del sistema acuapónico ayuda a filtrar el agua?", "filtro", "Sirve para limpiar el agua."),
        ]

    async def event_ready(self):
        # Se llama al iniciar el bot
        print(f'Bot conectado como {self.nick}')
        if not self.challenge_task_running:
            # Arranca tareas de fondo una sola vez
            self.loop.create_task(self.challenge_task())  # Preguntas rápidas
            self.loop.create_task(self.reminder_task())   # Recordatorio de comandos
            self.challenge_task_running = True

    async def event_message(self, message):
        # Ignora mensajes sin texto o del bot mismo
        if not message.content or message.author.name.lower() == self.nick.lower():
            return

        # Procesa comandos antes de más lógica
        await self.handle_commands(message)

        texto = normalize_text(message.content)

        # Responde a 'hola'
        if "hola" in texto:
            await message.channel.send(f"Hola, {message.author.name}!")

        # Responde pregunta rápida si aciertan
        if self.secret_answer and texto == normalize_text(self.secret_answer):
            user = message.author.name
            self.user_points[user] = self.user_points.get(user, 0) + 5
            await message.channel.send(f"¡Bien, {user}! +5 puntos.")
            self.secret_question = None
            self.secret_answer = None
            self.secret_hint = None

        # Verifica respuestas durante duelo
        if self.duelo_active and self.duelo:
            correcta = normalize_text(self.duelo['current_answer'])
            if texto == correcta and message.author.name in (self.duelo['p1'], self.duelo['p2']):
                await self.register_duel_answer(message.author.name, message.channel)

        # Efectos de 'locura' si está activa
        if self.locura_active:
            if "cuac" in texto:
                await message.channel.send(f"{message.author.name} dijo CUAC!")
            if "robot" in texto:
                await message.channel.send(f"{message.author.name} habla como robot!")
            # Si escribe al revés igual
            if texto == texto[::-1] and len(texto) > 1:
                await message.channel.send(f"{message.author.name} habla al revés!")

    # ------------------
    # COMANDOS DEL BOT
    # ------------------

    @commands.command()
    async def comandos(self, ctx):
        # Muestra los comandos
        texto = (
            "!duelo @user - Reta a alguien\n"
            "!acepto - Acepta duelo\n"
            "!ranking - Ver puntos\n"
            "!reglas - Ver reglas\n"
            "!pista - Pedir pista\n"
            "!locura - Activa/desactiva locura\n"
            "!led <color> - Cambia color LED"
        )
        await ctx.send(texto)

    @commands.command()
    async def reglas(self, ctx):
        # Explica cómo jugar
        texto = (
            "1. Responde preguntas para ganar puntos.\n"
            "2. Usa !duelo para retar.\n"
            "3. Duelo al mejor de 5.\n"
            "4. Gana 15 puntos si vences."
        )
        await ctx.send(texto)

    @commands.command()
    async def ranking(self, ctx):
        # Muestra los mejores jugadores
        tabla = sorted(self.user_points.items(), key=lambda x: x[1], reverse=True)
        if not tabla:
            return await ctx.send("Todavía no hay puntos.")
        msg = "Ranking de puntos:\n"
        for i, (user, pts) in enumerate(tabla, 1):
            msg += f"{i}. {user}: {pts} pts\n"
        await ctx.send(msg)

    @commands.command()
    async def pista(self, ctx):
        # Da una pista de la pregunta rápida
        if self.secret_hint:
            await ctx.send(f"Pista: {self.secret_hint}")
        else:
            await ctx.send("No hay pregunta activa.")

    @commands.command()
    async def duelo(self, ctx, user: str):
        # Inicia un duelo contra @user
        user = user.lstrip("@")
        if self.duelo_active:
            return await ctx.send("Ya hay un duelo en curso.")
        self.duelo = {
            'p1': ctx.author.name,
            'p2': user,
            'score': {ctx.author.name: 0, user: 0},
            'round': 0,
            'accepted': False,
            'current_answer': None,
            'channel': ctx.channel
        }
        await ctx.send(f"Duelo: {ctx.author.name} vs {user}. Esperando !acepto.")

    @commands.command()
    async def acepto(self, ctx):
        # El segundo jugador acepta
        if not self.duelo or self.duelo['accepted']:
            return await ctx.send("No hay duelo pendiente.")
        if ctx.author.name != self.duelo['p2']:
            return await ctx.send("No eres el retado.")
        self.duelo['accepted'] = True
        self.duelo_active = True
        await ctx.send(f"{ctx.author.name} aceptó. ¡Empieza!")
        await asyncio.sleep(1)
        await self.next_duel_round()

    async def next_duel_round(self):
        # Envía la siguiente pregunta del duelo
        self.duelo['round'] += 1
        disponibles = [q for q in self.question_pool if q not in self.used_questions]
        if not disponibles:
            return await self.duelo['channel'].send("Se acabaron las preguntas.")
        q, a, h = random.choice(disponibles)
        self.used_questions.add((q, a, h))
        self.duelo['current_answer'] = a
        await self.duelo['channel'].send(f"Ronda {self.duelo['round']}: {q}")

    async def register_duel_answer(self, winner, channel):
        # Suma punto al ganador y revisa si ya venció
        self.duelo['score'][winner] += 1
        await channel.send(f"{winner} acierta y suma 1 punto!")
        if self.duelo['score'][winner] == 3:
            self.duelo_active = False
            self.user_points[winner] = self.user_points.get(winner, 0) + 15
            await channel.send(f"{winner} ganó el duelo! +15 puntos")
            self.duelo = None
        else:
            await self.next_duel_round()

    @commands.command()
    async def locura(self, ctx):
        # Enciende/apaga la locura en chat
        self.locura_active = not self.locura_active
        estado = "ACTIVADA" if self.locura_active else "DESACTIVADA"
        await ctx.send(f"Locura {estado}!")

    async def challenge_task(self):
        # Cada 3 minutos manda o renueva pregunta rápida
        while True:
            await asyncio.sleep(180)
            if not self.connected_channels:
                continue
            ch = self.connected_channels[0]
            if self.secret_answer:
                # Si quedó pregunta sin responder, muestra respuesta
                await ch.send(f"Tiempo! Respuesta: {self.secret_answer}")
            # Elige nueva pregunta
            q, a, h = random.choice(self.question_pool)
            self.secret_question = q
            self.secret_answer = a
            self.secret_hint = h
            await ch.send(f"Pregunta rápida: {q}")

    async def reminder_task(self):
        # Cada 10 minutos recuerda usar !comandos
        while True:
            await asyncio.sleep(600)
            if self.connected_channels:
                await self.connected_channels[0].send("Usa !comandos para ver qué puedo hacer.")

    @commands.command(name='led')
    async def led(self, ctx):
        # Cambia el color del LED con !led <COLOR>
        partes = ctx.message.content.strip().upper().split()
        if len(partes) != 2 or partes[1] not in COLOR_MAP:
            return await ctx.send("Uso: !led <COLOR>. Colores: " + ", ".join(COLOR_MAP.keys()))

        valor = COLOR_MAP[partes[1]]
        if valor == self.current_led_color:
            return await ctx.send(f"El LED ya está en {partes[1]}")

        url = f"https://api.thingspeak.com/update?api_key={THINGSPEAK_WRITE_KEY}&field3={valor}"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200 and int(r.text) > 0:
                self.current_led_color = valor
                await ctx.send(f"LED en {partes[1]} activado!")
            else:
                await ctx.send("No se pudo cambiar el color.")
        except:
            await ctx.send("Error al conectar con ThingSpeak.")

# Arranca el bot y lo reinicia si hay error
def main():
    while True:
        try:
            bot = Bot()
            print("Iniciando bot...")
            bot.run()
        except Exception as e:
            print("Error:", e)
            time.sleep(5)

if __name__ == '__main__':
    main()
