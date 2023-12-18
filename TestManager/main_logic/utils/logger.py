import asyncio
import logging
import os
from datetime import date
from pathlib import Path
from typing import Optional
from TestManager.main_logic.utils.READ_CONFIG import TestManagerConfig, read_yaml_config, read_test_manager_config


def get_logger(
        config: TestManagerConfig,
        file_name: Optional[str] = None,
        log_dir: Optional[Path] = None
) -> logging.Logger:
    if file_name:
        logger: logging.Logger = logging.getLogger(file_name)
    else:
        logger: logging.Logger = logging.getLogger(__name__)

    if not logger.handlers:  # Проверяем, есть ли уже у логгера обработчики
        logger.setLevel(logging.DEBUG)

        # Создание обработчика для консоли
        console_handler: logging.StreamHandler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter: logging.Formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_filename = os.path.join(log_dir, f'{file_name}.log')
        else:
            cur_date = str(date.today())
            log_dir = Path(config.ranorex.dir_to_logs).joinpath(cur_date).absolute()
            log_dir.mkdir(parents=True, exist_ok=True)
            log_filename: str = os.path.join(log_dir, f'test_manager_running_{cur_date}.log')

        file_handler: logging.FileHandler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)
        file_formatter: logging.Formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


if __name__ == "__main__":
    CONFIG_FILE = r'C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml'

    config_app = read_yaml_config(CONFIG_FILE)
    logger = get_logger(read_test_manager_config(config_app))

    logger.info("test")
    logger.debug("x")
