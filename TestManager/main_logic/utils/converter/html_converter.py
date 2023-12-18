import asyncio
import os
import zipfile
from datetime import date
from pathlib import Path

from TestManager.main_logic.utils.READ_CONFIG import read_yaml_config, read_test_manager_config
from TestManager.main_logic.utils.converter.dirs_util import DirManager


class HtmlConverter(DirManager):
    async def converter_rxzlog_to_html(self, rxzlog_file_full_path: Path):
        """ Конвертер файлов rxzlog в html """

        # Проверяем наличие файла rxzlog и отсутствие папки с его названием
        # Проверяем наличие всех файлов rxzlog и создаем для каждого папку
        print(f"Попытка конвертировать в html - '{rxzlog_file_full_path}'")
        folder_path = rxzlog_file_full_path.parent
        file_name = rxzlog_file_full_path.name
        file_name_without_suffix = os.path.splitext(file_name)[0]

        rxzlog_folder_path = folder_path.joinpath(file_name_without_suffix)

        if not os.path.exists(rxzlog_folder_path):
            os.makedirs(rxzlog_folder_path)
            zip_path = rxzlog_file_full_path.absolute()
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(rxzlog_folder_path)

                # Переименование файлов внутри папки rxzlog_folder_path
                for root, dirs, files in os.walk(rxzlog_folder_path):
                    for filename in files:
                        if filename.endswith('.rxlog'):
                            new_filename = os.path.splitext(filename)[0] + '.html'
                            os.rename(os.path.join(root, filename), os.path.join(root, new_filename))
                        elif filename.endswith('.rxlog.data'):
                            new_filename = filename.replace('.rxlog.data', '.html.data')
                            os.rename(os.path.join(root, filename), os.path.join(root, new_filename))

            except Exception as ez:
                self.logger.exception(f"Произошла ошибка - {ez}, при обработке файла {zip_path}")

        await asyncio.sleep(0)


def test():
    config = read_test_manager_config(
        read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\tests\masha_1_test.yaml")
    )

    rxzlog_full_path = Path(
        config.ranorex.dir_to_logs,
        str(date.today()),
        'video_lite',
        'Fishzone_Win10x64',
        f"1456 video_lite  Win10x64  основные_тесты_на_4_стенда clone.rxzlog"
    )
    html_converter = HtmlConverter(config)
    asyncio.run(html_converter.converter_rxzlog_to_html(rxzlog_full_path))


if __name__ == "__main__":
    test()
