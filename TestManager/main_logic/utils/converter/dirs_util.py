import datetime
import os
import re

from datetime import date
from pathlib import Path
from typing import Optional

from TestManager.main_logic.utils.READ_CONFIG import TestManagerConfig, read_test_manager_config, read_yaml_config


class DirManager:
    def __init__(self, app_config: TestManagerConfig, log):
        """
        Инициализация и запуск всех связанных сценариев с обработкой логов
        """
        self.app_config: TestManagerConfig = app_config
        self.cur_path_file: Optional[str] = None
        self.test_manager: TestManagerConfig = app_config

        self.logger = log

        # Получить папку с датой на сегодня
        self.date_today_str = str(date.today())
        cur_dir = Path(self.test_manager.ranorex.dir_to_logs)
        self.cur_path_file = cur_dir.joinpath(self.date_today_str)
        self.time_now = datetime.datetime.now()

    @staticmethod
    def get_folders_and_files_in_folder(folder_path):
        folders = []
        files = []
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                folders.append(item)
            else:
                files.append(item)
        return folders, files

    def get_current_reports_for_today(self, endswith=".rxzlog"):
        """ Получить текущие отчеты за сегодня """

        files = []

        # получить список файлов в ней и вернуть его
        soft = self.cur_path_file.glob('**/*')

        for dir in soft:
            vms_dir = dir.glob('**/*')

            for vm in vms_dir:
                _files = vm.glob('**/*')
                for file in _files:
                    if file.suffix == endswith:
                        files.append(file)

        return files

    @staticmethod
    def clean_report_names_from_garbage(rxzlog_file_full_path: Path):
        """ Почистить имена отчетов от мусора добавить к именам названия последних сборок """

        def get_files_and_folders_with_same_name(dir_path: Path, file_name_without_suffix: str):
            file_paths = dir_path.rglob("{}.*".format(file_name_without_suffix))
            return list(file_paths)

        # получить список файлов в ней и вернуть его
        file_name_without_suffix = rxzlog_file_full_path.stem
        dir_path = rxzlog_file_full_path.parent

        items = get_files_and_folders_with_same_name(dir_path, file_name_without_suffix)
        for file in items:
            print(file)

        for file_path in items:
            try:
                if file_path.suffix in [".rxzlog", ".log", ".pdf", ".html", ".data"]:
                    x_file = file_path
                    dir_file = x_file.parent
                    last_name = x_file.name
                    new_name = re.sub(r'(^\d+)( \w+ \w+?_)(\w+)(.+)', r'\1 \3\4', str(last_name))
                    x_file.rename(dir_file / new_name)

            except Exception as e:
                print(f"Произошла ошибка {e}")

        need_dir = Path(dir_path / file_name_without_suffix)
        if need_dir.is_dir():
            parent_dir = need_dir
            last_name = need_dir.name
            new_name = re.sub(r'(^\d+)( \w+ \w+?_)(\w+)(.+)', r'\1 \3\4', str(last_name))
            parent_dir.rename(parent_dir.parent / new_name)


def test():
    config = read_test_manager_config(
        read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\tests\masha_1_test.yaml")
    )

    rxzlog_full_path = Path(
        config.ranorex.dir_to_logs,
        str(date.today()),
        'video_lite',
        'Fishzone_Win10x64',
        f"1476 video_lite Fishzone_Win10x64 основные_тесты_на_4_стенда clone.log"
    )
    dir_manager = DirManager(config)
    dir_manager.clean_report_names_from_garbage(rxzlog_full_path)


if __name__ == "__main__":
    test()
