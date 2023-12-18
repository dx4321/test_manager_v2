import asyncio
import os
import shutil
from pathlib import Path
from typing import List
import time

import requests

from TestManager.main_logic.utils.READ_CONFIG import read_test_manager_config, TestManagerConfig, read_yaml_config, \
    TeamCitySoft
from TestManager.main_logic.utils.logger import get_logger
from TestManager.main_logic.utils.sql import DataBase


class TeamCity:
    def __init__(self, app_config: TestManagerConfig, log):
        self.logger = log
        self.for_tests_links_builds: List[TeamCitySoft] = app_config.team_city.for_test_programs_info
        self.builds_counts: int = len(self.for_tests_links_builds)
        self.app_config = app_config
        self.data_base = DataBase(app_config, log)

    async def check_last_build_and_get_programs_for_tests(self, list_po: List[str]) -> List:
        list_po_for_check = [t_po for t_po in self.app_config.team_city.for_test_programs_info if
                             t_po.soft_name in list_po]

        programs_for_new_tests = []
        task_for_download_builds = []

        timestamp = int(time.time())

        for po in list_po_for_check:
            build_id, build_number = self.get_last_build_info(po.soft_name, po.last_build)

            last_build_in_excel_for_prog = self.data_base.get_build_number_for_soft(po.soft_name)

            if self.app_config.team_city.check_for_the_latest_release:
                if last_build_in_excel_for_prog != build_number:
                    self.data_base.save_build_number(po.soft_name, build_number)
                    programs_for_new_tests.append(po.soft_name)

                    for testing_po in self.app_config.program_for_tests:
                        if testing_po.name == po.soft_name:
                            testing_po.last_build = f"{build_number} {timestamp}"
                            if po.distro_full_path_for_download:
                                task_for_download_builds.append(
                                    asyncio.create_task(
                                        self.download_build(build_id, po.distro_full_path_for_download)
                                    )
                                )
                else:
                    for testing_po in self.app_config.program_for_tests:
                        if testing_po.name == po.soft_name:
                            testing_po.last_build = None
                    programs_for_new_tests.append(None)

            else:
                self.data_base.save_build_number(po.soft_name, build_number)
                programs_for_new_tests.append(po.soft_name)

                for testing_po in self.app_config.program_for_tests:
                    if testing_po.name == po.soft_name:
                        testing_po.last_build = f"{build_number} {timestamp}"
                        if po.distro_full_path_for_download:
                            task_for_download_builds.append(
                                asyncio.create_task(
                                    self.download_build(build_id, po.distro_full_path_for_download)
                                )
                            )

        await asyncio.gather(*task_for_download_builds)
        return programs_for_new_tests

    def get_last_build_info(self, soft_name: str, url: str) -> (int, int):
        headers = {
            'Authorization': f'Bearer {self.app_config.team_city.token}',
            'Accept': "application/json",
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            last_build_id = data['build'][0]['id']
            last_build_number = data['build'][0]['number']
            last_build_link = data['build'][0]['webUrl']
            self.logger.debug(f"Для софта - {soft_name} - последняя сборка: {last_build_number} {last_build_link}")
            return last_build_id, last_build_number
        else:
            raise Exception(
                f"Произошла ошибка запроса - {url}"
                f"\n код ответа -> {response.status_code}"
            )

    async def download_build(self, build_id: str, file_name: str):
        headers = {
            'Authorization': f'Bearer {self.app_config.team_city.token}',
            'Accept': "application/json",
        }
        file_name = Path(file_name)
        url = f"http://teamcity.bolid.ru/app/rest/builds/id:{build_id}/artifacts/content/{file_name.name}"

        response = requests.get(url, headers=headers, stream=True)

        if response.status_code == 200:
            with open(file_name, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            self.logger.info('Файл успешно скачан')
            file_path = os.path.abspath(file_name)
            self.logger.info(f"файл доступен по пути - {file_path}")
            await asyncio.sleep(0)
            return file_path
        else:
            raise Exception(
                f"Произошла ошибка запроса - {url}"
                f"\n код ответа -> {response.status_code}"
            )


# Tests
if __name__ == '__main__':
    # Получить конфиг
    CONFIG_FILE = r'C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml'
    test_manager_config = read_test_manager_config(read_yaml_config(CONFIG_FILE))
    logger = get_logger(test_manager_config)

    softs = [po.soft_name for po in test_manager_config.team_city.for_test_programs_info]

    tc = TeamCity(test_manager_config, logger)
    programs_new = asyncio.run(tc.check_last_build_and_get_programs_for_tests(softs))

    po = test_manager_config.team_city.for_test_programs_info[1]
    build_id, build_number = tc.get_last_build_info("video_lite", po.last_build)
    asyncio.run(tc.download_build(build_id, po.distro_full_path_for_download))
