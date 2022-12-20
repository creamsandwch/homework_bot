import os
import time
import logging
import requests

from dotenv import load_dotenv
import telegram.ext


logging.basicConfig(
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    level=logging.INFO,
    filename='logs.log',
    filemode='w',
)

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
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
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
    ]
    flag = True
    for token in tokens:
        if not token:
            logging.CRITICAL(f'Токен {token} не указан или недоступен.')
            flag = False
    if flag:
        logging.INFO('Все токены загружены в виртуальное окружение.')


def send_message(bot, message):
    """Пока ничего."""
    pass


def get_api_answer(timestamp):
    """Получает ответ от API яндекс.домашки в формате .json."""
    params = {'from_date': int(timestamp)}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params,
        )
    except Exception:
        logging.ERROR('Ответ от API яндекс.Домашки не был получен.')
    response = response.json()
    return response


def check_response(response):
    """Получаем из ответа API яндекс.Домашки последнюю домашнюю работу."""
    try:
        homeworks = response.get('homeworks')
    except KeyError:
        logging.ERROR('В ответе от API нет списка домашних заданий.')
    return homeworks[0]


def parse_status(homework):
    """Получаем статус домашнего задания для сообщения бота."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    verdict = HOMEWORK_VERDICTS.get(status)

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time_ns())

    while True:
        try:

            time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            ...
        ...


if __name__ == '__main__':
    main()
