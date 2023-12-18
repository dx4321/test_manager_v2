import zipfile
from pathlib import Path

from TestManager.main_logic.utils.READ_CONFIG import read_test_manager_config, read_yaml_config
from TestManager.main_logic.utils.converter.dirs_util import DirManager
from TestManager.main_logic.utils.logger import get_logger
from TestManager.main_logic.utils.send_email import Email


class ZipConverter(DirManager):

    def convert_to_zip(self):
        """ Создать архив с отчетами по тестам по протестированным программам """

        files = self.get_current_reports_for_today('.pdf')
        added_files = {}  # Словарь для отслеживания уже добавленных файлов

        for testing_po in self.test_manager.program_for_tests:
            # создать zip архив
            print(files)
            test = files[0].parent.parent.parent.parent
            zip_path = Path(
                test).joinpath(
                f'{testing_po.last_build} ' +
                str(testing_po.name) + f'_'
                                       f'{self.time_now.strftime("%m_%d_%Y_%H_%M")}'
                                       f'.zip'
            ).absolute()
            fantasy_zip = zipfile.ZipFile(zip_path, 'w')

            # архивировать необходимые отчеты в зип, по названию ПО
            for file in files:
                if testing_po.name in file.name and file.name.endswith('.pdf'):
                    if file.name not in added_files:  # Проверка на дублирование
                        fantasy_zip.write(file, file.name, compress_type=zipfile.ZIP_DEFLATED)
                        added_files[file.name] = True  # Добавление файла в словарь

            fantasy_zip.close()

    def send_email_zip_logs(self):
        """ Отправить на почту zip архивы с отчетами """

        def get_logs_count(soft_name):
            unique_files = set()
            for _file in self.get_current_reports_for_today('.pdf'):
                if soft_name in _file.name and _file.name.endswith('.pdf'):
                    unique_files.add(_file.name)
            return len(unique_files)

        def more_than_9_and_8_megabytes(path_file: str) -> bool:
            """ Если файл больше 9,8 мегабайт вернуть true """

            import os.path

            file_size = os.path.getsize(path_file)  # размер в байтах
            if file_size >= 10276044:  # 9,8 мегабайт в байтах
                return True
            else:
                return False

        email = Email(
            self.app_config.email.server,
            self.app_config.email.port,
            self.app_config.email.login,
            self.app_config.email.password,
            self.app_config.email.send_from
        )

        for testing_po in self.app_config.program_for_tests:
            # написать текст сообщения, и отослать файл ответственному лицу для просмотров логов

            # Найти путь к архиву с отчетом нужной по
            cur_dir = Path(self.test_manager.ranorex.dir_to_logs).joinpath(self.date_today_str).glob('**/*.zip')
            for file in cur_dir:
                logs_count = get_logs_count(testing_po.name)
                if logs_count != 0:
                    message_text = f"Для {testing_po.name} было пройдено {logs_count} блоков.\n\n" \
                                   f"{', '.join([kit.kit_name for kit in testing_po.kits])} - " \
                                   f"отвечают за переподготовку дистрибутива для " \
                                   f"дальнейших тестов, " \
                                   f"а так-же выполняет проверку образа на установку, работу базы данных в АБД\n"

                    list_kits_stands = [kit.stands for kit in testing_po.kits]

                    if len(list_kits_stands) > 0:
                        message_text += f"\nТестирование на клоне, в котором используется заранее подготовленный " \
                                        f"дистрибутив, может быть выполнено на как условном, так и реальном стенде. " \
                                        f"Во время прохождения теста проводятся основные проверки на сборку.\n "

                    if file.name.endswith('.zip') and testing_po.name in file.name:
                        path_to_file = file

                        if more_than_9_and_8_megabytes(str(path_to_file)):
                            message_text += \
                                f"\nОтчет доступен по сетевому пути: " \
                                f'"{file.absolute()}"'

                            email.send_mail(
                                self.app_config.email.soft[testing_po.name],
                                f"Отчёт о прохождении тестов за {self.date_today_str}",
                                message_text,
                            )
                        else:
                            message_text += \
                                f"\nТак-же отчет доступен по сетевому пути: " \
                                f'"{file.absolute()}"'

                            email.send_mail(
                                self.app_config.email.soft[testing_po.name],
                                f"Отчёт о прохождении тестов за {self.date_today_str}",
                                message_text,
                                [str(path_to_file)]
                            )
                        continue


def test():
    config_fail = r'C:\Users\fishzon\PycharmProjects\test_manager_v2\CONFIG.yaml'
    test_manager_config = read_test_manager_config(read_yaml_config(config_fail))
    logger = get_logger(test_manager_config)
    zip_converter = ZipConverter(test_manager_config, logger)

    zip_converter.convert_to_zip()
    zip_converter.send_email_zip_logs()


if __name__ == "__main__":
    test()
