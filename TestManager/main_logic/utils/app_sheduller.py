import asyncio
import time
from typing import Callable

import aioschedule as schedule
from TestManager.main_logic.utils.READ_CONFIG import read_test_manager_config, read_yaml_config
from TestManager.main_logic.utils.logger import get_logger


class Schedule:
    def __init__(self, log, time_for_schedule: str, job_func: Callable, *args):
        """
        Инициализация объекта класса Schedule.

        Аргументы:
        - log: Логгер для записи логов.
        - time_for_schedule (str): Время, в которое нужно выполнить задание (формат "HH:MM").
        - job_func (Callable): Функция, которую нужно выполнить по расписанию.
        - args: Дополнительные аргументы для передачи в функцию.

        Пример использования:
        ```
        CONFIG_FILE = 'C:\\Users\\fishzon\\PycharmProjects\\test_manager_v2\\CONFIG.yaml'
        test_manager_config = read_test_manager_config(read_yaml_config(CONFIG_FILE))
        logger = get_logger(test_manager_config)

        loop = asyncio.get_event_loop()
        s = Schedule(logger, "11:24", test_func, "1")
        loop.run_until_complete(s.run_schedule())
        ```

        """
        self.time_for_schedule = time_for_schedule
        self.schedule = schedule
        self.set_schedule(job_func, *args)
        self.logger = log

    def set_schedule(self, job: Callable, *args) -> None:
        """
        Установка задания в шедулер.

        Аргументы:
        - job (Callable): Функция, которую нужно выполнить по расписанию.
        - args: Дополнительные аргументы для передачи в функцию.

        Возвращает:
        - None

        """
        self.schedule.every().monday.at(self.time_for_schedule).do(job, *args)
        self.schedule.every().tuesday.at(self.time_for_schedule).do(job, *args)
        self.schedule.every().wednesday.at(self.time_for_schedule).do(job, *args)
        self.schedule.every().thursday.at(self.time_for_schedule).do(job, *args)
        self.schedule.every().friday.at(self.time_for_schedule).do(job, *args)
        self.schedule.every().saturday.at(self.time_for_schedule).do(job, *args)
        self.schedule.every().sunday.at(self.time_for_schedule).do(job, *args)

    async def run_schedule(self):
        """
        Запуск шедулера.

        Возвращает:
        - None

        """
        self.logger.info("Scheduler start")

        while True:
            await self.schedule.run_pending()
            time.sleep(1)


# Пример функции, которую можно использовать в тестах
async def test_func(*args) -> None:
    """
    Тестовая функция.

    Аргументы:
    - args: Дополнительные аргументы.

    Возвращает:
    - None

    """
    logger.info("hi")
    for arg in args:
        logger.info(f"Другой аргумент из *argv: {arg}")


# Пример использования
if __name__ == "__main__":
    CONFIG_FILE = r'C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml'
    test_manager_config = read_test_manager_config(read_yaml_config(CONFIG_FILE))
    logger = get_logger(test_manager_config)

    loop = asyncio.get_event_loop()
    s = Schedule(logger, "11:24", test_func, "1")
    loop.run_until_complete(s.run_schedule())
