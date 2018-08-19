#!/usr/bin/env python3
from telethon import TelegramClient, events
from telethon import utils
from multiprocessing import Process, Queue
from googletrans import Translator
from datetime import datetime
from geolite2 import geolite2
from random import choice
import urllib.request
import youtube_dl
import asyncio
import socket
import pyowm
import time
import copy
import re
import os

# right way to use this script:
#
# $ nohup python3 -u bot.py &
#
# 'nohup' option will make your script to work in the background even if you end console process
# all data printed in stdout will be saved in a file called 'nohup.out', so basically it will store logs of all your chats
# -u: unbuffering, so script will save messages in real-time mode
# to see the log type:
#
# $ tail -f nohup.out

# message width is 55 characters
# |   1 0   |   2 0   |   3 0   |   4 0   |   50   |12345|
# 1234567891123456789112345678911234567891123456789112345|

# pyowm checks weather with API key provided below

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

FLAGLIST = {
    "ru": "🇷🇺", "ja": "🇯🇵", "en": "🇬🇧", "uk": "🇩🇪", "pl": "🇩🇪", "de": "🇩🇪", "fr": "🇫🇷", "no": "🇳🇴"}  # get right emoji

def getweather(city : str, owm : pyowm) -> str:
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

def curl(url) -> str:
    response = urllib.request.urlopen(url)
    response = str(response.info()).splitlines()
    response = [i for i in response if "set-cookie:" not in i.lower()]
    return(response)

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

# other
interact = ("/ping@moe", "/weather@moe", "/help@moe", "/getip@moe", "/geoip@moe", "/youtube@moe", "/curl@moe",
                                                                                        ["Ping-pong.", "Cat pictures are not funny.", "No",
                                                                                        "Had no time to think of the other answers"])
dummy_interact = copy.deepcopy(interact[7])
blacklist = ['12345678'] #blacklist to ignore requests from undesirable users

@client.on(events.NewMessage)
async def my_event_handler(event):
    for user_id in blacklist:
        if user_id in str(event.message.from_id):
            print(user_id, "[BLACKLISTED]")
            event = None
    if event != None:
        global dummy_interact, interact
        fromid = event.message.from_id
        entity = await client.get_entity(fromid)
        print("{} [MID: {} FROMID: {} {}]: {}".format(datetime.now(),
                                event.message.id, fromid, utils.get_display_name(entity), event.raw_text))
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
                dummy_interact = copy.deepcopy(interact[7])
                toprint = dummy_interact[number_choice]
                await event.reply(toprint)
                del dummy_interact[number_choice]
        if interact[1] in event.raw_text:
            city = event.raw_text[int(event.raw_text.rfind(
                interact[1]) + len(interact[1])):]
            city = city.strip()
            result = getweather(city, owm)
            await event.reply(result)
        if interact[2] in event.raw_text.lower():
            await event.reply(
                "Usage:\n\nFUNCTIONS:\n1. Translator: send '/tren' to get translator help\n2. Weather:\n`  \
/weather@moe [City]`\n3. Curl -I:\n`  /curl@moe http://website/`\n4. Calculator:\n`  /eval [expression]`\n5. \
IP lookup by domain:\n`  /getip@moe http://website/`\n6. GEOIP:\n`  /geoip@moe 0.1.2.3`\n7. YOUTUBE-DL\n`  \
/youtube@moe http://link.to/thevideo`\n`  /youtube@moe --q=360 http://link.to/thevideo`\n`  Will download video in 360p`\n`  \
Available quality: 360/480/720`\n\nSTUFF:\n`  /ping@moe`")
        if interact[3] in event.raw_text.lower():
            result = event.raw_text.lower()
            result = result.replace(interact[3], "").strip()
            if "http://" in result:
                result = result.replace("http://", "")
            if "https://" in result:
                result = result.replace("https://", "")
            findlink = result.find("/")
            if findlink != -1:
                result = result[:findlink]
            try:
                print(result)
                result = socket.gethostbyname(result)
                await event.reply("`{}`".format(result))
            except:
                await event.reply("An error occured:", sys.exc_info()[0])
                pass
        if interact[4] in event.raw_text.lower():
            result = event.raw_text.lower()
            reader = geolite2.reader()
            result = result.replace(interact[4], "").strip()
            result = reader.get(result)
            if result.get("subdivisions"):
                await event.reply(
                "```GEO ID: {}\nCOUNTRY: {}\nLATITUDE: {}\nLONGITUDE: {}\nTIME ZONE: {}\nISO CODE: {}\nSUBDIVISION GEO ID: {}\nSUBDIVISION: {}```".format(
                    result["country"]["geoname_id"], result["country"]["names"]["en"], result["location"]["latitude"],
                    result["location"]["longitude"], result["location"]["time_zone"], result["subdivisions"][0]["iso_code"],
                    result["subdivisions"][0]["geoname_id"], result["subdivisions"][0]["names"]["en"]))
            if not result.get("subdivisions"):
                await event.reply(
                    "```GEO ID: {}\nCOUNTRY: {}\nLATITUDE: {}\nLONGITUDE: {}```".format(
                    result["country"]["geoname_id"], result["country"]["names"]["en"], result["location"]["latitude"],
                    result["location"]["longitude"]))
        if interact[5] in event.raw_text.lower():
            result = event.raw_text
            result = result.replace(interact[5], "").strip()
            setname = choice(range(0, 999999))
            filepath = "/home/aurora/bot/{}.mp4".format(setname)
            if "vk.com/" in result:
                await event.reply("Downloading video from VK requires authorization. This is not the problem of youtube-dl itself.")
            else:
                if "youtube" and "&list=" in result:
                    findlink = result.find("&list=")
                    result = result[:findlink]
                try:
                    if "--q=360" in result:
                        ydl_opts = {
                            'outtmpl': filepath,
                            'format': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/[height <=? 360]/bestvideo+bestaudio'
                        }
                        result = result.replace("--q=360", "").strip()
                    elif "--q=480" in result:
                        ydl_opts = {
                            'outtmpl': filepath,
                            'format': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/[height <=? 480]/bestvideo+bestaudio'
                        }
                        result = result.replace("--q=480", "").strip()
                    elif "--q=720" in result:
                        ydl_opts = {
                            'outtmpl': filepath,
                            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/[height <=? 720]/bestvideo+bestaudio'
                        }
                        result = result.replace("--q=720", "").strip()
                    else:
                        ydl_opts = {
                            'outtmpl': filepath,
                            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio'
                        }
                    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([result])
                    while not os.path.isfile(filepath):
                        sleep(1)
                    # moves file to the server directory and send a link to the plain video with ability to download it
                    os.rename(filepath, "/srv/www/public_html/temp/temp/{}.mp4".format(setname))
                    link = "https://temp.neko.space/temp/{}.mp4".format(setname)
                    await event.reply(link)
                except:
                    if result != "":
                        await event.reply("An error has occured. Probably, your video is not available.")
        if interact[6] in event.raw_text.lower():
            link = event.raw_text.lower()
            try:
                link = link.replace(interact[6], "")
                if not ("http://" or "https://") in link:
                    link = "http://{}".format(link.strip())
                getcurl = curl(link.strip())

                await event.reply(
                "```{}```".format(getcurl))

            except urllib.error.HTTPError as e:
                await event.reply('''An error occurred: {}.\nThe response code was {}'''.format(
                    e, e.getcode()))
            time.sleep(3)
        if "/shrug" in event.raw_text.lower():
            await event.edit(event.raw_text.replace("/shrug", r"¯\_(ツ)_/¯"))

        if "/eval" in event.raw_text:
            if "print" in event.raw_text.lower():
                findres = event.raw_text.find("print(")
                rfindres = event.raw_text.find(")", findres)
                if findres != -1 and rfindres != -1:
                    result = event.raw_text[(findres + 6):rfindres]
                    result = result.replace('"', '')
                    await event.reply(result)
            elif "len" in event.raw_text.lower():
                findres = event.raw_text.find("len(")
                rfindres = event.raw_text.find(")", findres)
                if findres != -1 and rfindres != -1:
                    result = event.raw_text[(findres + 4):rfindres]
                    result = result.replace('"', '')
                    result = str(len(result))
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
