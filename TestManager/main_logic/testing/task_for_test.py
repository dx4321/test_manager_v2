import asyncio

import os
import random
import re
from datetime import date
import logging
from pathlib import Path
from typing import Union
from typing import Optional

from TestManager.main_logic.utils.converter.dirs_util import DirManager
from TestManager.main_logic.utils.converter.html_converter import HtmlConverter
from TestManager.main_logic.utils.converter.pdf_converter import PdfConverter
from TestManager.main_logic.utils.cmd import CMD
from .states import State
from TestManager.main_logic.utils.vspheremanager import VSphereManager
from .statuses import TestingKitStatus, VmsPreparatoryTests, TestingStandStatus
from ..utils.logger import get_logger


class Task_for_test:
    """ Описать как должен проходить конкретный тестовый случай """

    def __init__(
            self,
            manager: "Manager",
            teamcity_build_number: str,
            test_kit: TestingKitStatus,
            test_id,
            soft_name: str,
            vm_name: str,
            clone_vm_name: str,
            snapshot_name: str,
            compiled_test: str,
            block: Union[VmsPreparatoryTests, TestingStandStatus],
            stand: Optional[str] = None,
            delete_vm_after_test: bool = False,
    ):
        """
        :arg soft_name: Имя тестируемой программы.
        :arg vm_name: название виртуальной машины с которой будет копия.
        :arg clone_vm_name: название для создания клона.
        :arg snapshot_name: название снапшота для создания копии (у вм).
        :arg compiled_test: путь к скомпилированному тесту.
        :arg block: указать либо блок VmsPreparatoryTests, TestingStandStatus
        :arg stand: указать стенд для блока 2.
        """
        self.manager = manager
        self.teamcity_build_number = teamcity_build_number
        self.test_kit: TestingKitStatus = test_kit
        self.test_id = test_id
        self.soft_name = soft_name
        self.vm_name = vm_name
        self.clone_vm_name = f"{clone_vm_name}"
        self.snapshot_name = snapshot_name
        self.compiled_test = compiled_test
        self.block = block
        self.stand = stand

        self.static_ip_address: str
        self.try_count = 1

        self.delete_vm_after_test = delete_vm_after_test

        self.state: State = State.FREE

        self.win_name = self.__get_operating_system_name(self.vm_name)

        self.cur_date = str(date.today())
        self.log_dir = Path(
            self.manager.config.ranorex.dir_to_logs).joinpath(
            self.cur_date,
            self.soft_name,
            self.teamcity_build_number,
            self.win_name,
        ).absolute()
        self.logger = get_logger(self.manager.config, self.clone_vm_name, self.log_dir)

        self.vsphere = VSphereManager(self.manager.config, self.logger)  # Компонент отвечающий за работу ВМ

        # 1.1 Нужно изменить название файла отчетов
        self.dir_m = DirManager(self.manager.config, self.logger)
        self.rxzlog_full_path = self.log_dir.joinpath(
            f"{self.clone_vm_name}.rxzlog"
        )

    def __get_free_ip_address(self):
        """ Получить свободный ip адрес, вернуть ip и занять его """

        for ip in self.manager.IP_addresses:
            if ip.is_available is True:
                ip.change_availability()
                return ip.address

    async def run_test(
            self
    ):
        """ Запустить тест """

        # Подготовить вм для тестов
        try:
            await self.__prepare_a_virtual_machine_for_the_test()
        except Exception as ex:
            self.logger.exception(f"Произошла ошибка при подготовке тестов на {self.clone_vm_name} - ошибка - {ex}")

        self.logger.info("+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=")
        self.logger.info(
            f"Подготовка к тестированию на vm - {self.clone_vm_name} пройдена, установлен ip - {self.static_ip_address}"
        )
        try:
            # Запустить тест на виртуальной машине
            await self.__run_the_test_on_a_virtual_machine()
            self.logger.info(
                "+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=")
            self.logger.info(f"Запуск теста пройден")

            # Создать снапшот на блоке если блок выполнения равен VmsPreparatoryTests
            await self.__create_a_snapshot_on_the_block()
            await self.convert_rxzlog_to_pdf_html()

            self.logger.info(
                "+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=")
            self.logger.info(f"Модуль создания снапшота пройден")

        except Exception as ex:
            self.logger.exception(f"Произошла серьёзная ошибка {ex}")

        # Завершить тестирование
        await self.__teardown()
        self.logger.info("+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=")
        self.logger.info(f"Модуль завершения тестового случая пройден")

    async def __prepare_a_virtual_machine_for_the_test(self):
        """ Подготовить виртуальную машину для теста """

        self.static_ip_address = self.__get_free_ip_address()
        # Занять лицензию

        self.state = State.BUSY

        # занять тест
        for po_for_vm_test in self.test_kit.vms_tests:
            if po_for_vm_test.vm_name in self.vm_name:
                if isinstance(self.block, VmsPreparatoryTests):
                    po_for_vm_test.state.set_busy()

        # занять блок
        for po_for_stand_test in self.test_kit.stands_tests_for_vms:
            if self.vm_name in po_for_stand_test.vm_for_clone_name:
                if isinstance(self.block, TestingStandStatus):
                    self.block.state.set_busy()

        # занять стенд
        for stand in self.manager.stands:
            if stand.name == self.stand:
                stand.set_busy()

        # Клонировать вм, создать ей новое имя, получить имя вм и
        if self.clone_vm_name is not None:
            self.logger.debug(f"Клонируем вм по снапшоту {self.vm_name, self.snapshot_name, self.clone_vm_name}")
            # vsm = VSphereManager(self.manager.config.vsphere)
            # await vsm.vm_create_a_copy_by_snapshot(self.vm_name, self.snapshot_name, self.clone_vm_name)
            await self.vsphere.vm_create_a_copy_by_snapshot(self.vm_name, self.snapshot_name, self.clone_vm_name)
            await asyncio.sleep(random.randint(2, 5))

        await asyncio.sleep(1)

        # Установить статический ip адрес для клонированной ВМ (и дождаться применения нового)
        self.logger.debug(f"Попытка прокинуть ip addr - на win_name {self.win_name}, ip - {self.static_ip_address}")
        await self.vsphere.vm_change_ip_address(
            self.clone_vm_name,
            self.manager.config.vsphere.all_vms_and_auth[self.win_name].login,
            self.manager.config.vsphere.all_vms_and_auth[self.win_name].password,
            self.static_ip_address,
            self.manager.config.vsphere.gateway
        )
        await asyncio.sleep(3)

    async def __run_the_test_on_a_virtual_machine(self, enable_disabling_of_tests: bool = False):
        """
        Запустить тест на виртуальной машине

        - enable_disabling_of_tests : включить отключение тестов в случае если произошла ошибка на блоке предподготовке
        """

        # Указать путь и аргументы для запуска тестов
        self.logger.debug(f"Попытка запуска тестов - {self.static_ip_address} для блока - {self.clone_vm_name}")
        ###############################################################################################################
        cmd = CMD(self.manager.config, self.logger)

        try:
            process_test_info = await cmd.open_exe_and_send_args(
                self.compiled_test,
                [
                    f"/agent:http://{self.static_ip_address}:{self.manager.config.ranorex.agent_port}/api",
                    "/zr", f'/zrf:{self.clone_vm_name}.rxzlog'
                ],
                f"{self.clone_vm_name}.rxzlog",
                self.log_dir
            )
            if enable_disabling_of_tests:
                # ##############################################################################################################
                if "Job completed: Error" in process_test_info and isinstance(self.block, VmsPreparatoryTests):
                    # если в блоке 0 есть хотя бы 1 не пройденный тест, то нужно отменить выполнение на стендах этой вм
                    for po in self.manager.testing_po:
                        if po.soft_name == self.soft_name:
                            for task_to_test in po.tasks:
                                if task_to_test.vm_name == self.clone_vm_name:
                                    task_to_test.state = State.DONE
                                    self.logger.exception(
                                        f"В тесте на подготовку под {self.soft_name} произошла ошибка в одном из тестов\n"
                                        f" поэтому тестирование не будет проходить на "
                                        f"{', '.join([vm.clone_vm_name for vm in po.tasks if vm.vm_name == self.clone_vm_name])}"
                                    )
            if "http://<machine|ip>:<port>/api/" in process_test_info:
                self.logger.exception("Агент не поднимается - перенастройте виртуальную машину либо разберитесь в чем "
                                      "проблема")

        except Exception as j:
            self.logger.exception(f"Произошла ошибка {j}")
        ###############################################################################################################

        self.logger.debug(f'Тест на блок {self.clone_vm_name} '
                          f'в {self.clone_vm_name} для {self.soft_name} пройден')

    async def convert_rxzlog_to_pdf_html(self):
        """ Конвертировать отчеты в pdf и в html формат """

        self.logger.info(f"Конвертируем отчет в PDF")
        # 1.2. Асинхронно конвертировать отчет в html и в pdf
        pdf_converter = PdfConverter(self.manager.config, self.logger)
        try:
            await pdf_converter.convert_reports_to_pdf(
                self.rxzlog_full_path
            )
        except Exception as eeee:
            print(eeee)
            print(self.rxzlog_full_path)
        self.logger.info(f"Конвертируем отчет в HTML")
        html_converter = HtmlConverter(self.manager.config, self.logger)
        await html_converter.converter_rxzlog_to_html(
            self.rxzlog_full_path
        )

    async def __create_a_snapshot_on_the_block(self):
        """ Создать снапшот на блоке если блок выполнения равен VmsPreparatoryTests  """

        # Создать снапшот на блоке если блок выполнения равен VmsPreparatoryTests
        if isinstance(self.block, VmsPreparatoryTests):
            # Создать снапшот на клоне
            await self.vsphere.vm_create_snapshot_for(self.clone_vm_name, self.snapshot_name)
            await asyncio.sleep(1)
            await self.vsphere.vm_power_off(self.clone_vm_name)
            await asyncio.sleep(2)

    async def __teardown(self):
        """ Завершить тестирование """

        # Проверка, что тест на стенд и установка флага на завершение теста
        # Если тест на стенд то удалить вм

        # Установить состояние теста блока подготовки на windows
        for po_for_vm_test_preparation in self.test_kit.vms_tests:
            _vm_name = self.__get_operating_system_name(self.vm_name)
            if po_for_vm_test_preparation.vm_name == self.vm_name:
                po_for_vm_test_preparation.state.set_done()

        # Установить состояние стенда теста на блок windows
        for po_in_stand_test in self.test_kit.stands_tests_for_vms:
            _vm_name = self.__get_operating_system_name(self.vm_name)  # ДОЛЖНЫ ЛИ БЫТЬ ТАКИМИ ИМЕНА?
            if po_in_stand_test.vm_name == self.vm_name:
                # Выключить клон и удалить его
                po_in_stand_test.state.set_done()

        # # Удалить после теста
        if self.delete_vm_after_test:
            await self.vsphere.wm_power_off_and_delete(self.clone_vm_name)

        self.logger.debug(f"Тест {self.soft_name} на {self.clone_vm_name} - завершен")

        # Освободить ip адрес
        for ip_address in self.manager.IP_addresses:
            if ip_address.address == self.static_ip_address:
                ip_address.set_availability()

        # освободить стенд
        for stand in self.manager.stands:
            if stand.name == self.stand:
                stand.set_free()

        self.manager.config.ranorex.all_licenses += 1
        self.logger.debug(f"Лицензия возвращена, всего лицензий - {self.manager.config.ranorex.all_licenses}")

        # Присвоить тестам на стенды под подготовленную вм статус, что вм готова
        for stand in self.test_kit.stands_tests_for_vms:
            if self.clone_vm_name in stand.vm_for_clone_name:
                stand.state_of_the_prepared_block = True

        # Освободить стенд
        for manager_stand in self.manager.stands:
            if self.stand == manager_stand.name:
                manager_stand.set_free()

        # Обновить состояние теста
        self.state = State.DONE

        # 1.3. Нужно изменить название файла отчетов
        self.logger.info(f"Очищаем название отчета")

        # Удаление всех обработчиков из логгера (отключаем логгер что бы можно было переименовать log файл)
        for handler in list(self.logger.handlers):
            self.logger.removeHandler(handler)
            handler.close()

        self.dir_m.clean_report_names_from_garbage(
            self.rxzlog_full_path
        )

        # Закрытие обработчиков и удаление их из логгера, для того что бы при следующем запуске не было ошибки
        # =OSError(24, 'Too many open files')
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()

    @staticmethod
    def __get_operating_system_name(vm_name) -> str:
        """ Получить имя операционной системы до 1-го пробела """

        if " " in str(vm_name):
            return str(re.sub(r'(^\w+ )([\w|.]+)( .+)', r'\2', vm_name))
        else:
            return vm_name
