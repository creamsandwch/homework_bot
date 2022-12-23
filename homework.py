import os
import time
import logging
import sys
from http import HTTPStatus
import json

import requests
import telegram
from dotenv import load_dotenv

import settings
from exceptions import NoNewStatus


log_format = (
    '%(asctime)s, %(levelname)s, %(funcName)s, '
    '%(lineno)d, %(message)s, %(name)s')

formatter = logging.Formatter(
    fmt=log_format,
)

console_logger = logging.StreamHandler()
console_logger.setLevel(logging.INFO)

file_logger = logging.FileHandler('logs.log')
file_logger.setLevel(logging.DEBUG)

logging.basicConfig(
    handlers=(console_logger, file_logger),
    format=log_format,
    level=logging.DEBUG,
)


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность токенов в виртуальном окружении."""
    return all([TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, PRACTICUM_TOKEN])


def send_message(bot: telegram.Bot, message: str):
    """Отправляет сообщение от бота в чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Бот отправил сообщение.')
    except Exception as error:
        logging.error(f'{error}: ошибка при отправке сообщения ботом.')


def get_api_answer(timestamp: int) -> dict:
    """Получает ответ от API яндекс.домашки в формате .json."""
    params = {'from_date': int(timestamp)}
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params,
        )
    except requests.RequestException as error:
        logging.error(
            f'{error}: Что-то пошло не так при доступе к API яндекс.Домашки'
        )

    if response.status_code != HTTPStatus.OK:
        raise Exception(
            'Ошибка при доступе к API яндекс.Домашки. '
            f'status_code {response.status_code}'
        )
    logging.info(
        'Запрос от API яндекс.Домашки получен. '
        f'status_code: {response.status_code}'
    )

    try:
        json.loads(response)
    except ValueError as error:
        logging.error(
            f'{error}: Невалидный ответ от API. '
            'Строка не может быть декодирована в .json.'
        )
    response = response.json()

    return response


def check_response(response: dict) -> list:
    """Получаем из ответа API яндекс.Домашки последнюю домашнюю работу."""
    if type(response) != dict:
        raise TypeError(
            'Некорретный тип данных объекта response, '
            'переданного в check_response.'
        )
    for key in ['homeworks', 'current_date']:
        if key not in response:
            raise KeyError(f'Нет ключа "{key}" в ответе от API.')

    if type(response.get('homeworks')) != list:
        raise TypeError('Некорректный тип данных объекта homeworks.')

    if type(response.get('current_date')) != int:
        raise TypeError('Некорректный тип данных обьекта current_date')

    homeworks = response.get('homeworks')

    if not homeworks:
        raise NoNewStatus('В ответе от API нет новых статусов домашки.')
    logging.info(
        'Из ответа API получен список ДЗ '
        f'из {len(homeworks)} объектов.'
    )
    return homeworks[0]


def parse_status(homework):
    """Получаем статус домашнего задания для сообщения бота."""
    if not homework.get('homework_name'):
        logging.error('Нет ключа "homework_name" в словаре "homework".')
        raise KeyError('Нет ключа "homework_name" в словаре "homework".')

    homework_name = homework.get('homework_name')
    status = homework.get('status')

    if status not in HOMEWORK_VERDICTS:
        raise Exception(
            f'Неожиданный статус домашнего задания "{homework_name}". '
            'Статус отсутствует в словаре HOMEWORK_VERDICTS'
        )
    verdict = HOMEWORK_VERDICTS.get(status)
    logging.info(
        f'Получен статус {status} проверки работы : {homework_name}'
    )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens():
        logging.info('Все токены загружены в виртуальное окружение.')
    else:
        logging.critical('Один или несколько токенов недоступны.')
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    cached_message = ''
    timestamp = int(time.time())

    # изменил получение timestamp, такой вариант присылает сообщения.
    # старый вариант не присылал.

    while True:
        try:
            ya_api_response = get_api_answer(timestamp)
            last_homework = check_response(ya_api_response)
            message = parse_status(last_homework)
        except NoNewStatus as info:
            logging.info(f'Статус дз: {info}')
            message = cached_message
        except Exception as error:
            logging.error(f'Сбой: {error}')
            message = f'{error}'
        finally:
            if message != cached_message:
                cached_message = message
                send_message(bot, message)
            if ya_api_response:
                timestamp = ya_api_response.get('current_date')
            time.sleep(settings.RETRY_PERIOD)


if __name__ == '__main__':
    main()
