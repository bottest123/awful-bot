#!/usr/bin/env python3
from telethon import TelegramClient, events
from multiprocessing import Process, Queue
from googletrans import Translator
from datetime import datetime
from random import choice
import asyncio
import pyowm
import copy
import re

# right way to use this script:
#
# $ nohup python3 bot.py
#
# 'nohup' option will make your script to work in the background even if you end console process
# all data printed in stdout will be saved in a file called 'nohup.out', so basically it will store logs of all your chats

# message width in full window is 55 characters
# |   1 0   |   2 0   |   3 0   |   4 0   |   50   |12345|
# 1234567891123456789112345678911234567891123456789112345|

CLEARASCII = [r"     \   /     ",
              r"      .-.      ",
              r"   ― (   ) ―   ",
              r"      '-’      ",
              r"     /   \     "]
CLOUDASCII = [r"    \  /       ",
              r" __ /‘‘.-.     ",
              r"    \_(   ).   ",
              r"    /(___(__)  ",
              r"               "]
OTHERASCII = [r"      .-.      ",
              r"     (   ).    ",
              r"    (___(__)   ",
              r"   ‚‘‚‘‚‘‚‘    ",
              r"   ‚’‚’‚’‚’    "]

FLAGLIST = { # used to get right emoji for answer
    "ru": "🇷🇺", "ja": "🇯🇵", "en": "🇬🇧", "uk": "🇩🇪", "pl": "🇩🇪", "de": "🇩🇪", "fr": "🇫🇷", "no": "🇳🇴"}

def getweather(city : str, owm : pyowm) -> str:
# pyowm checks weather with API key provided below
    if city:
        getweather = owm.weather_at_place(city)
        w = getweather.get_weather()
        wtime = w.get_reference_time(timeformat='iso')
        wind, humidity, sunrise, sunset, temp, status = w.get_wind(), w.get_humidity(), w.get_sunrise_time(
        timeformat='iso'), w.get_sunset_time(timeformat='iso'), w.get_temperature('celsius'), w.get_detailed_status()
        replyascii = CLEARASCII if ("clear" or "sunny") in status else OTHERASCII
        replyascii = CLOUDASCII if "cloud" in status else replyascii
        return("```{first}{0}:\n{second} TEMP: {5}°C, {7}\n{third} HUM: {4}%  WIND: {6} m/s\n{fourth} ◓ SUNRISE: {2}\n{fifth} ◒ SUNSET: {3}```".format(
            city, wtime, sunrise, sunset, humidity, temp['temp'], wind['speed'], status,
            first=replyascii[0], second=replyascii[1], third=replyascii[2], fourth=replyascii[3], fifth=replyascii[4]))
    else:
        return("No city was set!")

def evaluater(expression : str):
    # since python is going into deadlock with piping between child and main processes with broken data
    # (multiprocessing.Queue.put(some_broken_data), and I am a pajeet
    # who don't want to code his own parser instead of great and unsafe eval, we are going to operate with file,
    # what actually is even worse, but at least works

    #if process was dropped, script will print error message below
    writeerror = open("result", "w")
    writeerror.write(
        "I did not break it, it's not true! It's bullshit! I did not break it, I did naaht! Oh, hi Mark")
    writeerror.close()
    regex = re.compile(r'[^\d.*+-/()]')
    expression = regex.sub('', expression)
    result = str(eval(expression))
    writeres = open("result", "w")
    writeres.write(result)
    writeres.close()

def translates(item : str, language : str) -> Translator:
    translator = Translator()
    item = item.replace("/tr{}".format(language), '')
    if item.strip():
        out = translator.translate(item, dest=language)
        return out
    else:
        return -1

# https://openweathermap.org/appid
# you get your OpenWeather API key here
owm = pyowm.OWM('you put your OW API key here', language='en')
# https://core.telegram.org/api/obtaining_api_id
# you get your telegram API ID and API hash here
api_id = your api ID
api_hash = 'your API hash'

# loads telegram session with its own log
client = TelegramClient('log', api_id, api_hash)
client.start()

# @iotop is my tg nickname, obviously you should change it to yours
# you should use it to avoid conflicts with other bots that can react to such phrases and sentences
interact = ("/ping@iotop", "/weather@iotop", "some chat phrase", "/help@iotop", "/eval", ["Ping-pong.", "Cat pictures are not funny.", "No",
                                                                                          "Had no time to think of the other answers"])

dummy_interact = copy.deepcopy(interact[5])
blacklist = ['12345678'] #id blacklist to ignore requests from undesirable users

@client.on(events.NewMessage)
async def my_event_handler(event):
    for user_id in blacklist:
        if user_id in str(event.message.from_id):
            print(user_id, "[BLACKLISTED]")
            event = None
    if event != None:
        global dummy_interact, interact
        print("{} [MID: {} FROMID: {}]: {}".format(datetime.now(),
                                event.message.id, event.message.from_id, event.raw_text))
        for language in FLAGLIST:
            if "/tr{}".format(language) in event.raw_text.lower():
                checktr = event.raw_text.lower()
                checkpos = checktr.rfind("/tr{}".format(language))
                if checkpos == 0:
                    get_translate = translates(event.raw_text, language)  # get translate
                    if get_translate == -1:
                        await event.reply("```Languages list:\n [ru, ja, en, uk, pl, de, fr, no]\nUsage:\n /tren text\nOr:\n /trru Omae wa mou shindeiru\n /trpl Poland can into space```")
                    else:
                        sourceflag = ' '  # source emoji
                        destflag = ' '  # destination emoji
                        for language in FLAGLIST:
                            if language in get_translate.src:
                                sourceflag = FLAGLIST[language]
                            if language in get_translate.dest:
                                destflag = FLAGLIST[language]
                        if get_translate.pronunciation and len(get_translate.pronunciation) < 20:
                            # if there is available pronunciation; limit to short phrases
                            await event.reply("```FROM {}[{}] TO {}[{}]:\n{} \nPRONUN: {}```".format(
                                sourceflag, get_translate.src, destflag, get_translate.dest, get_translate.text, get_translate.pronunciation))
                        else:
                            if get_translate.text.strip():
                                await event.reply("```FROM {}[{}] TO {}[{}]:\n{}```".format(
                                    sourceflag, get_translate.src, destflag, get_translate.dest, get_translate.text))
        if event.raw_text == interact[0]:
            # pseudorandom choice to prevent duplicates:
            number_choice = choice(range(len(dummy_interact)))
            if (len(dummy_interact) > 1):
                toprint = dummy_interact[number_choice]
                await event.reply(toprint)
                del dummy_interact[number_choice]
            else:
                dummy_interact = copy.deepcopy(interact[5])
                toprint = dummy_interact[number_choice]
                await event.reply(toprint)
                del dummy_interact[number_choice]
        if interact[1] in event.raw_text:
            city = event.raw_text[int(event.raw_text.rfind(
                "/weather@iotop") + len(interact[1])):]
            city = city.strip()
            print("asking for weather...", city)  # console log for convenience
            result = getweather(city, owm)
            await event.reply(result)

	#some chat phrase bot will answer to:
        if interact[2] in event.raw_text.lower():
            await event.reply(file="/home/aurora/bot/some_picture1.webp")

        if interact[3] in event.raw_text.lower():
            await event.reply(
                "Usage:\n/tren/trru/truk/trja [word]\n/ping@iotop\n/weather@iotop [City]\n/eval [expression]")
        if "/shrug" in event.raw_text.lower():
            await event.edit(event.raw_text.replace("/shrug", r"¯\_(ツ)_/¯"))
        if interact[4] in event.raw_text:
            if "print" in event.raw_text.lower():
                findres = event.raw_text.find("print(")
                rfindres = event.raw_text.find(")", findres)
                if findres != -1 and rfindres != -1:
                    result = event.raw_text[(findres + 6):rfindres]
                    result = result.replace('"', '')
                    print("Printed:", result)
                    await event.reply(result)
            elif "len" in event.raw_text.lower():
                findres = event.raw_text.find("len(")
                rfindres = event.raw_text.find(")", findres)
                if findres != -1 and rfindres != -1:
                    result = event.raw_text[(findres + 4):rfindres]
                    result = result.replace('"', '')
                    result = str(len(result))
                    print("Len:", result)
                    await event.reply(result)
            else:
            #we will check if eval isn't too long and then start a new process
            #to avoid hangs and breaks when someone types something like 'eval 22 ** 22 ** 22'
                if len(event.raw_text) > len("/eval"):
                    expression = event.raw_text.replace('/eval', '')
                    expression = expression.strip()
                    if "()" not in expression:
                        if len(str(expression)) >= 40:
                            await event.reply("Expression is too long.")
                        else:
                            while 1:
                                try:
                                    proc = Process(target=evaluater, args=(expression,))
                                    proc.daemon = True
                                    proc.start()
                                    proc.join(3)
                                    if proc.is_alive():
                                        proc.terminate()
                                    writeres = open("result", "r")
                                    result = writeres.read()
                                    writeres.close()
                                    await event.reply(result)
                                    break
                                except:
                                    print("It seems like we never have things going as planned.")
                                    break
client.run_until_disconnected()
