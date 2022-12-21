import os
import sys
import time
import logging
import requests

import telegram
from dotenv import load_dotenv


log_format = '%(asctime)s, %(levelname)s, %(message)s, %(name)s'

formatter = logging.Formatter(
    fmt=log_format,
)

logging.basicConfig(
    format=log_format,
    level=logging.INFO,
)

logger = logging.StreamHandler()
logger.setLevel(logging.INFO)
logger.setFormatter(formatter)

logging.getLogger(__name__).addHandler(logger)


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность токенов в виртуальном окружении."""
    tokens = [
        (PRACTICUM_TOKEN, 'PRACTICUM_TOKEN'),
        (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'),
        (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID'),
    ]

    try:
        for token in tokens:
            if not token[0]:
                raise SystemExit(
                    f'Токен {token[1]} недоступен. '
                    'Выход из программы.'
                )
        logging.info('Все токены загружены в виртуальное окружение.')
    except SystemExit:
        logging.critical(Exception, exc_info=True)
        sys.exit()


def send_message(bot, message):
    """Отправляет сообщение от бота в чат."""
    try:
        if not message:
            raise Exception('Сообщение пустое (message == None).')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception:
        logging.error(Exception)
    logging.debug('Бот отправил сообщение.')


def get_api_answer(timestamp):
    """Получает ответ от API яндекс.домашки в формате .json."""
    params = {'from_date': int(timestamp)}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params,
        )
        print(response.status_code)
        if response.status_code != 200:
            raise (
                'Ошибка при доступе к API яндекс.Домашки. '
                f'status_code {response.status_code}'
            )
    except Exception:
        logging.error(Exception, exc_info=True)
    logging.info(
        f'Запрос от API яндекс.Домашки получен. Код: {response.status_code}'
    )
    response = response.json()
    return response


def check_response(response):
    """Получаем из ответа API яндекс.Домашки последнюю домашнюю работу."""
    try:
        if type(response) != dict:
            raise TypeError
        if 'homeworks' not in response:
            raise KeyError
        if type(response.get('homeworks')) != list:
            raise TypeError
        homeworks = response.get('homeworks')
        if not homeworks:
            raise Exception(
                'Список домашних заданий пуст.'
            )
        logging.info(
            'Из списка домашних заданий получен объект последнего задания.'
        )
        return homeworks[0]
    except TypeError as error:
        logging.error(
            f'{error}: Некорретная структура данных ответа API.'
        )
    except KeyError as error:
        logging.error(
            f'{error}: Некорректный ответ от API: .'
            'отсутствие ожидаемого ключа "homeworks".'
        )
    except Exception as error:
        logging.info(f'{error}')


def parse_status(homework):
    """Получаем статус домашнего задания для сообщения бота."""
    try:
        if homework is None:
            raise Exception('Нет новых статусов.')
        homework_name = homework.get('homework_name')
        status = homework.get('status')
        if not HOMEWORK_VERDICTS.get(status):
            raise Exception(
                f'Неожиданный статус домашнего задания {homework} '
            )
        verdict = HOMEWORK_VERDICTS.get(status)
        logging.info(
            f'Получен статус {status} проверки работы : {homework_name}'
        )
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as error:
        logging.error(
            f'{error}'
        )


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    while True:
        try:
            timestamp = time.time()
            ya_api_response = get_api_answer(timestamp)
            last_homework = check_response(ya_api_response)
            message = parse_status(last_homework)
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            type(message)
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
