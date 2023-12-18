from typing import Optional, List, Union
import asyncio
from datetime import date
from pathlib import Path
import re

from TestManager.main_logic.utils.READ_CONFIG import read_test_manager_config, read_yaml_config, TestManagerConfig
from TestManager.main_logic.utils.logger import get_logger


class CMD:

    def __init__(self, test_manager_config: TestManagerConfig, log: get_logger) -> None:
        """
        Инициализация объекта CMD.

        Аргументы:
        - test_manager_config (TestManagerConfig): Конфигурация тест-менеджера.
        - log (get_logger): Логгер для записи логов.

        Возвращает:
        - None

        Пример использования:
        ```
        CONFIG_FILE = 'C:\\Users\\fishzon\\PycharmProjects\\test_manager_v2\\CONFIG.yaml'
        test_manager_config = read_test_manager_config(read_yaml_config(CONFIG_FILE))
        logger = get_logger(test_manager_config)

        cmd = CMD(test_manager_config, logger)
        ```

        """
        self.cmd_info: Optional[str] = None
        self.test_manager_config: TestManagerConfig = test_manager_config
        self.lines: List[str] = []

        self.logger = log

    async def open_exe_and_send_args(
            self,
            program: str,
            arg: Optional[Union[str, List[str]]] = None,
            name_for_out: str = None,
            path_for_out: Path = Path(r"\\192.168.202.15\ftp\1. Автоматизация\smb\Автотестирование\logs"),
            timeout: int = 18000,  # Таймаут в секундах (1 час)
    ) -> str:
        """
        Открыть exe и отправить аргументы.

        Аргументы:
        - program (str): Путь к исполняемому файлу.
        - arg (Optional[Union[str, List[str]]]): Список аргументов для передачи в программу.
          Если None, то аргументы не передаются.
        - name_for_out (str): Имя файла для вывода результатов.
        - path_for_out (Path): Путь к директории, в которой будут сохранены результаты.
        - timeout (int): Таймаут выполнения в секундах.

        Возвращает:
        - str: Строка, содержащая объединенные результаты выполнения программы.

        Пример использования:
        ```
        cmd = CMD(config_app, logger)
        await cmd.open_exe_and_send_args(
            program="my_program.exe",
            arg=["arg1", "arg2"],
            name_for_out="output.txt",
            path_for_out=Path("path/to/output/directory"),
            timeout=3600
        )
        ```

        """
        try:
            # Путь
            if isinstance(path_for_out, str):
                path_for_out = Path(path_for_out)
            if not path_for_out.is_dir():
                path_for_out.mkdir(parents=True)

            await asyncio.sleep(1)
            self.logger.debug(
                f"Запускаем {program} {arg}\n"
                f"путь до папки с отчетом - '{path_for_out}'"
            )

            proc = await asyncio.create_subprocess_exec(
                program,
                *(arg if isinstance(arg, list) else [arg]),
                cwd=path_for_out.absolute(),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            tasks = [
                asyncio.create_task(self.read_task(proc.stdout, show=True)),
                asyncio.create_task(self.read_task(proc.stderr)),
            ]

            await asyncio.wait_for(
                asyncio.gather(*tasks),
                timeout=timeout
            )

            full_path = Path(path_for_out).joinpath(name_for_out)

            if full_path.exists():
                self.logger.info(f"{name_for_out} - отчет появился - '{full_path}'")
            else:
                self.logger.error(f"{name_for_out} - отчет не появился - '{full_path}'")

            return " ".join(self.lines)

        except Exception as ex:
            self.logger.exception(f"Произошла ошибка при выполнении open_exe_and_send_args - '{ex}'")
            return ""

    async def read_task(self, stream: asyncio.StreamReader, show: bool = False) -> None:
        """ Прочитать строки в задаче.

        Аргументы:
        - stream (asyncio.StreamReader): Поток для чтения.
        - show (bool): Флаг, указывающий, нужно ли отображать строки в логе.
          По умолчанию False.

        Возвращает:
        - None

        Пример использования:
        ```
        await self.read_task(proc.stdout, show=True)
        ```

        """
        while True:
            last_line = await stream.readline()  # Ожидание следующей строки

            if not last_line:  # Если строка пустая, закончить выполнение функции
                return
            else:
                last_line = last_line.decode(encoding="CP866")  # Декодирование и очистка строки
                last_line = re.sub(r"(.+?)(\r\n$)", r"\1", last_line)
                try:
                    self.lines.append(last_line)  # Добавление строки в список
                except Exception as ex:
                    self.logger.exception(f"Произошла ошибка при добавлении строки - '{ex}'")
                if show:
                    self.logger.info(last_line)  # Вывод строки


async def test_create_test_ranorex() -> None:
    """ Запустить тест Ranorex на агенте """

    try:
        clone_name = "win test123.rxzlog"
        ip = '192.168.202.172'
        bloc = f"/agent:http://{ip}:{config_app.ranorex.agent_port}/api"
        compiled_test = (
            r"\\192.168.202.15\ftp\1. Автоматизация\smb\Автотестирование\OrionPro\Тесты "
            r"на предустановленные SQL\ADB_06_2022.exe"
        )

        cmd = CMD(config_app, logger)
        await cmd.open_exe_and_send_args(
            compiled_test,
            [bloc, "/zr", f'/zrf:{clone_name}'],
            clone_name
        )

    except Exception as ex:
        logger.exception(f"Произошла ошибка при выполнении test_create_test_ranorex - '{ex}'")


async def test_create_pdf_file(config):
    """
    Конвертировать отчет ranorex формата .rxzlog в pdf
    """
    try:
        rxzlog_full_path = Path(
            config.ranorex.dir_to_logs,
            str(date.today()),
            'pprog',
            '77',
            'Fishzone_Win10x64',
            f"pprog Fishzone_Win10x64 pprog_upprog clone.rxzlog"
        )

        path_to_dir: Path = rxzlog_full_path.parent
        file_name = rxzlog_full_path.name

        cmd = CMD(config_app, logger)
        file_name_without_extension = str(Path(file_name).stem)
        input_file = str(Path(path_to_dir.joinpath(file_name).absolute()))
        output_file = str(Path(path_to_dir.joinpath(file_name_without_extension + ".pdf").absolute()))

        await cmd.open_exe_and_send_args(
            program=config_app.ranorex.path_to_pdf_converter,
            arg=[input_file, output_file],
            name_for_out=f"{file_name_without_extension}.pdf",
            path_for_out=path_to_dir
        )

    except Exception as ex:
        logger.exception(f"Произошла ошибка при выполнении test_create_pdf_file - '{ex}'")


if __name__ == '__main__':
    CONFIG_FILE = r'C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml'
    test_manager_config = read_test_manager_config(read_yaml_config(CONFIG_FILE))

    logger = get_logger(test_manager_config)

    config_app: TestManagerConfig = read_test_manager_config(read_yaml_config(CONFIG_FILE))
    # asyncio.run(test_create_test_ranorex())
    asyncio.run(test_create_pdf_file(test_manager_config))
