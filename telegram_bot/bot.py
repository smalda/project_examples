import aiohttp
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import os
import typing as tp
import json
import random

from config import *


# webserver settings
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(os.environ.get('PORT', 5000))

HEROKU_APP_NAME = 'splendid-movie-bot'
WEBHOOK_HOST = f'https://{HEROKU_APP_NAME}.herokuapp.com'
WEBHOOK_PATH = f'/webhook/{BOT_TOKEN}'
WEBHOOK_URL = f'{WEBHOOK_HOST}{WEBHOOK_PATH}'


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

async def get_google_link(film_name):
    headers = {
        'apikey': ZENSERP_API_KEY,
    }

    params = (
        ('q', f'{film_name} watch'),
    )

    link = None
    request_url = 'https://app.zenserp.com/api/search'
    async with aiohttp.ClientSession() as session:
        async with session.get(url=request_url, headers=headers, params=params) as response:
            resp_text = await response.text()
            response = json.loads(resp_text)
            link = response['results']['left'][0]['url']
    return link

async def get_imdb_info(film_name):
    request_url = f'http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={film_name}'
    info = None
    async with aiohttp.ClientSession() as session:
        async with session.get(url=request_url) as response:
            resp_text = await response.text()
            response = json.loads(resp_text)
            info = response
    return info

async def get_tmdb_link(film_query) -> tp.List[tp.Optional[str]]:
    request_info_url = f'https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&language=en-US&query={film_query}&page=1&include_adult=false'
    link = None
    async with aiohttp.ClientSession() as session:
        async with session.get(url=request_info_url) as response:
            resp_text = await response.text()
            response = json.loads(resp_text)
            if 'results' in response and len(response['results']):
                movie_id = response['results'][0]['id']
                request_url = f'https://api.themoviedb.org/3/movie/{movie_id}/watch/providers?api_key={TMDB_API_KEY}'
                async with session.get(url=request_url) as providers_info_query:
                    resp_text = await providers_info_query.text()
                    result = json.loads(resp_text)
                    if 'results' in result and 'US' in result['results'] and 'link' in result['results']['US']:
                        link = result['results']['US']['link']
    return link

async def respond_to_search_query(film_name, chat_id):
    imdb_info = await get_imdb_info(film_name)
    if imdb_info and 'Title' in imdb_info:
        await bot.send_message(chat_id, MOVIE_FOUND_MESSAGE)

        if 'Poster' in imdb_info:
            await bot.send_photo(chat_id, imdb_info['Poster'])
        
        message = f"{(imdb_info['Title'])} ({(imdb_info['Year'])})     "
        if 'imdbRating' in imdb_info:
            try:
                message += '⭐'*round(float(imdb_info['imdbRating']) / 2.0)
            except:
                None
        if 'Runtime' in imdb_info:
            message += f"\n{imdb_info['Runtime']}"
        if 'Genre' in imdb_info:
            message += f"\n\n{imdb_info['Genre']}"
        if 'Director' in imdb_info:
            message += f"\nDirected by {imdb_info['Director']}"
        if 'Actors' in imdb_info:
            message += f"\nCasting {imdb_info['Actors']}"
        if 'Plot' in imdb_info:
            message += f"\n\n{imdb_info['Plot']}"

        await bot.send_message(chat_id, message)
    

        tmdb_link = await get_tmdb_link(imdb_info['Title'])
        if tmdb_link:
            await bot.send_message(chat_id, tmdb_link)
        else:
            await bot.send_message(chat_id, LINKS_NOT_FOUND_MESSAGE)
            link = await get_google_link(film_name)
            await bot.send_message(chat_id, link)
    else:
        await bot.send_message(chat_id, MOVIE_NOT_FOUND_MESSAGE)


@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.reply(GREETING_MESSAGE, reply_markup=start_markup)

@dp.message_handler(commands=['help'])
async def start_handler(message: types.Message):
    await message.reply(HELP_MESSAGE)
    await bot.send_message(message.chat.id, PROCEED_MESSAGE, reply_markup=shortened_markup)

@dp.message_handler()
async def default(message: types.Message):
    await message.reply(SEARCH_RESULTS_MESSAGE(message.text))
    await respond_to_search_query(message.text, message.chat.id)
    await bot.send_message(message.chat.id, PROCEED_MESSAGE, reply_markup=start_markup)


start_button = InlineKeyboardButton('Start searching 📺', callback_data='start')
help_button = InlineKeyboardButton('Learn the basics ❓', callback_data='help')
talk_to_me_button = InlineKeyboardButton('Speak with me! 💁‍♂️', callback_data='talk')
start_markup = InlineKeyboardMarkup(row_width=1).add(start_button, help_button, talk_to_me_button)
shortened_markup = InlineKeyboardMarkup(row_width=1).add(start_button, talk_to_me_button)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('start'))
async def callback_start(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, START_SEARCHING_MESSAGE)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('help'))
async def callback_start(callback_query: types.CallbackQuery):
    await bot.send_message(callback_query.from_user.id, HELP_MESSAGE)
    await bot.send_message(callback_query.from_user.id, PROCEED_MESSAGE, reply_markup=shortened_markup)

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('talk'))
async def callback_start(callback_query: types.CallbackQuery):
    phrase = BOT_LANGUAGE[random.randrange(0, len(BOT_LANGUAGE))]
    await bot.send_message(callback_query.from_user.id, phrase)
    await bot.send_message(callback_query.from_user.id, PROCEED_MESSAGE, reply_markup=start_markup)


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL,drop_pending_updates=True)

if __name__ == '__main__':
    executor.start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        skip_updates=True,
        on_startup=on_startup,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )