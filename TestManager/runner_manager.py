# Функция для запуска менеджера тестов
import asyncio
import logging
import threading
from typing import Optional

from TestManager.main_logic.TestManager import TestManager
from TestManager.main_logic.TestManager import read_yaml_config, TestManagerConfig
from TestManager.main_logic.utils.READ_CONFIG import read_test_manager_config
from TestManager.main_logic.utils.logger import get_logger


class ManagerStarter:
    def __init__(self, config_file):
        """
        Вспомогательный класс который следит за состоянием работы сервиса тест менеджер
        """
        self.logger = None

        self.test_manager_running: str = "Инициализация менеджера"
        self.test_manager_thread = None  # Добавьте эту строку для объявления переменной test_manager_thread
        self.config_file = config_file

        self.test_manager: Optional[TestManager] = None
        self.manager = None
        self.config_app = None

        self.init_config()

    def init_config(self):
        config_app = read_yaml_config(self.config_file)
        logger = get_logger(read_test_manager_config(config_app))

        self.logger: logging.Logger = logger
        self.config_app = read_yaml_config(self.config_file)
        self.manager: TestManagerConfig = TestManagerConfig(**self.config_app)
        self.test_manager = TestManager(self.config_file)

    def __run_test_manager(self):
        """ Запустить тест менеджер """

        self.init_config()

        self.logger.info(f"TestManager Start")

        if self.manager.scheduler.activate_by_time:
            self.test_manager_running = "Тест менеджер запущен 'в планировщике'"
            asyncio.run(self.test_manager.run_schedule_for_test_manager())
        else:
            self.test_manager_running = "Тест менеджер запущен 'сейчас'"
            asyncio.run(self.test_manager.start_app_manager())
            # Если запускаем сейчас, то после того как пройдет тестирование нужно запустить в планировщике
            asyncio.run(self.test_manager.run_schedule_for_test_manager())

    def start_test_manager(self):
        """ Запустить тест менеджер в потоке """

        self.init_config()

        if self.test_manager_thread is None or not self.test_manager_thread.is_alive():
            test_manager_thread = threading.Thread(target=self.__run_test_manager)
            test_manager_thread.start()

    def stop_test_manager(self):
        """ Остановить тест менеджер """

        self.logger.info(f"Тест менеджер остановлен")
        self.test_manager_running = "Тест менеджер остановлен"

        # Дождитесь завершения потока менеджера тестов
        if self.test_manager_thread is not None and self.test_manager_thread.is_alive():
            self.test_manager_thread.join()
