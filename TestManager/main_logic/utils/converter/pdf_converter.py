import asyncio
from datetime import date
from pathlib import Path

from TestManager.main_logic.utils.READ_CONFIG import read_test_manager_config, read_yaml_config
from TestManager.main_logic.utils.cmd import CMD
from TestManager.main_logic.utils.converter.dirs_util import DirManager
from TestManager.main_logic.utils.logger import get_logger


class PdfConverter(DirManager):
    async def convert_reports_to_pdf(self, rxzlog_file_full_path: Path):
        """ Конвертировать отчеты в PDF """

        # для каждого отчета конвертировать его в PDF в ту же папку в которой лежат отчеты

        path_to_dir: Path = rxzlog_file_full_path.parent
        file_name = rxzlog_file_full_path.name
        file_name_without_extension = Path(file_name).stem

        absolute_file_path = path_to_dir.joinpath(file_name_without_extension + ".pdf").absolute()

        # создать объект CMD
        cmd = CMD(self.test_manager, self.logger)

        await cmd.open_exe_and_send_args(
            program=self.test_manager.ranorex.path_to_pdf_converter,
            arg=[
                f"{str(rxzlog_file_full_path.absolute())}",
                str(absolute_file_path)
            ],
            name_for_out=f"{file_name_without_extension}.pdf",
            path_for_out=path_to_dir.absolute()
        )


async def test():
    CONFIG_FILE = r'C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml'
    config = read_test_manager_config(
        read_yaml_config(CONFIG_FILE)
    )

    rxzlog_full_path = Path(
        config.ranorex.dir_to_logs,
        str(date.today()),
        'pprog',
        '77',
        'Fishzone_Win10x64',
        f"pprog Fishzone_Win10x64 pprog_upprog clone.rxzlog"
    )

    test_manager_config = read_test_manager_config(read_yaml_config(CONFIG_FILE))
    logger = get_logger(test_manager_config)

    html_converter = PdfConverter(config, logger)
    await html_converter.convert_reports_to_pdf(rxzlog_full_path)


if __name__ == "__main__":
    asyncio.run(test())
