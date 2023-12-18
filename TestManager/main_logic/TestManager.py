import logging
from typing import List, Optional
import asyncio

from TestManager.main_logic.testing.statuses import TestingPOStatus
from TestManager.main_logic.utils.READ_CONFIG import TestManagerConfig, read_yaml_config, read_test_manager_config
from TestManager.main_logic.utils.app_sheduller import Schedule

from TestManager.main_logic.utils.converter.zip_converter import ZipConverter
from TestManager.main_logic.utils.logger import get_logger
from TestManager.main_logic.utils.teamcity_api import TeamCity
from TestManager.main_logic.utils.vspheremanager import VSphereManager

from TestManager.main_logic.testing.states import State, Stand, IP_Address, StandState
from TestManager.main_logic.testing.task_for_test import Task_for_test


class TestManager:
    __instance: Optional['TestManager'] = None

    def __init__(self, config_path: str):
        if TestManager.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.config: TestManagerConfig = TestManagerConfig(**read_yaml_config(config_path))
            self.logger: logging.Logger = get_logger(self.config)
            self.tc: TeamCity = TeamCity(self.config, self.logger)
            self.testing_po: List[TestingPOStatus] = []
            self.stands: List[Stand] = []
            self.IP_addresses: List[IP_Address] = []
            self.testing: bool = self.__get_testing_po_statuses
            self.run_time_tasks: List[asyncio.Task] = []

    @staticmethod
    def get_instance(config):
        if TestManager.__instance is None:
            TestManager.__instance = TestManager(config)
        return TestManager.__instance

    @property
    def __get_testing_po_statuses(self) -> bool:
        """Метод для определения статусов TestingPO."""

        if len(self.testing_po) > 0:
            for po in self.testing_po:
                if len(po.tasks) > 0:
                    return True
            if len([po.state for po in self.testing_po if po.state.state == State.DONE]) \
                    == len(self.testing_po):
                return False
        return True

    async def check_new_branch_in_team_city(self, list_po: List[str]) -> List:
        """
        Проверяет новые сборки в TeamCity и сравнивает их с эксель файлом, указанным в HistoryFilePath.
        Если есть новые сборки, создает новое состояние, указывая, что тест нужно выполнить на всех машинах.
        Состояние отображает машины, на которых нужно завершить выполнение тестов,
        и на машинах, где тесты уже прошли.
        """
        list_of_programs_that_have_new_builds = await self.tc.check_last_build_and_get_programs_for_tests(list_po)
        return list_of_programs_that_have_new_builds

    async def initializing(self) -> None:
        """
        0. Проверяет, вышла ли новая сборка, и для программ, для которых вышла новая сборка, проводит инициализацию.
        1. Инициализирует объекты тестируемого ПО.
        2. Проводит инициализацию стендов.
        3. Проводит инициализацию USB-ключей.
        4. Проводит инициализацию IP-адресов.
        5. Создать очередь для тестов
        """
        # Основные проверки
        assert self.config.ranorex.all_licenses <= len(self.config.vsphere.static_ip_address_pool), \
            "количество используемых лицензий не может быть больше чем ip адресов"
        assert self.config.ranorex.all_licenses > 0, "лицензий не может быть меньше или равно 0"

        # 0. Проверить вышла ли новая сборка и для программ для которых вышла новая сборка провести инициализацию
        # метод сам обновит поле у программы last_bild
        # так же если вышла новая сборка то скачает ее по указанному пути в конфигурации
        check_new_tc_assembly: List[str] = []
        for p in self.config.program_for_tests:
            if p.tests_are_active is True:
                check_new_tc_assembly.append(p.name)

        self.logger.debug(
            f"Проверить вышла ли новая сборка для программ "
            f"{', '.join([po for po in check_new_tc_assembly])}"
        )
        list_of_programs_that_have_new_builds = await self.check_new_branch_in_team_city(check_new_tc_assembly)

        self.logger.debug(
            "1. Инициализировать объекты тестируемого по и скачать для новых сборок дистрибутивы в сетевую папку"
        )
        for i, po in enumerate(self.config.program_for_tests):
            if po.name in list_of_programs_that_have_new_builds:
                self.testing_po.append(TestingPOStatus(po, po.last_build))

        self.logger.debug("2. Провести инициализацию стендов")
        for po in self.config.program_for_tests:
            for kit in po.kits:
                if kit.stands:
                    for stand in kit.stands:
                        self.stands.append(Stand(stand.stand_name))

        self.logger.debug("3. Провести инициализацию Ip адресов")
        for ip in self.config.vsphere.static_ip_address_pool:
            self.IP_addresses.append(IP_Address(ip))

        self.logger.debug("Создать очередь для тестов")
        self.create_a_queue_from_the_configuration()

    def create_a_queue_from_the_configuration(self) -> None:
        """
        Создает очередь из конфигурации объектов.
        Если во время скачивания установки или проверки лицензии возникает ошибка,
        тестирование ПО останавливается, и выводится сообщение об ошибке.
        """
        for po in self.testing_po:
            for kit in po.list_testing_kits:
                # Добавление в список тестов на vms
                for vms_prep_test in kit.vms_tests:
                    if len(kit.stands_tests_for_vms) > 0:
                        delete_vm_after_test = False
                    else:
                        delete_vm_after_test = True

                    po.tasks.append(
                        Task_for_test(
                            manager=self,
                            teamcity_build_number=po.teamcity_build_number,
                            test_kit=kit,
                            test_id=vms_prep_test.test_id,
                            soft_name=kit.soft_name,
                            vm_name=vms_prep_test.vm_name,
                            clone_vm_name=vms_prep_test.vm_to_clone_name,
                            snapshot_name=kit.snapshot_name,
                            compiled_test=kit.path_to_test_install_check_license,
                            block=vms_prep_test,
                            stand=None,
                            delete_vm_after_test=delete_vm_after_test
                        )
                    )
                # Добавление в список на стенды
                for vms_stand_test in kit.stands_tests_for_vms:
                    po.tasks.append(
                        Task_for_test(
                            manager=self,
                            teamcity_build_number=po.teamcity_build_number,
                            test_kit=kit,
                            test_id=vms_stand_test.test_id,
                            soft_name=kit.soft_name,
                            vm_name=vms_stand_test.vm_name,
                            clone_vm_name=vms_stand_test.vm_for_clone_name,
                            snapshot_name=kit.snapshot_name,
                            compiled_test=vms_stand_test.path_to_test,
                            block=vms_stand_test,
                            stand=vms_stand_test.stand_name,
                            delete_vm_after_test=True
                        )
                    )

    async def run_tests(self) -> None:
        """
        Запускает тесты в соответствии с логикой Белова.
        """

        async def task_creator() -> None:
            """ Добавление задач в очередь задач """
            while self.testing:
                await check_if_completed()
                await asyncio.sleep(1)

                if self.config.ranorex.all_licenses > 0:
                    for po in self.testing_po:
                        for task in po.tasks:
                            if task.state == State.FREE:
                                # Если готова vms со сборкой, то запустить тест на стенд
                                if task.stand:
                                    for stand in self.stands:
                                        # Проверить что нужный стенд свободен и
                                        # проверить что vm для нужного теста на стенд готова
                                        if stand.name == task.stand and stand.state == StandState.FREE \
                                                and task.block.state_of_the_prepared_block:
                                            if self.config.ranorex.all_licenses > 0:
                                                # запустить тесты на стенд
                                                self.run_time_tasks.append(asyncio.create_task(task.run_test()))
                                                self.config.ranorex.all_licenses -= 1
                                                self.logger.debug(
                                                    f"Всего лицензий - {self.config.ranorex.all_licenses}")
                                else:
                                    if self.config.ranorex.all_licenses > 0:
                                        self.run_time_tasks.append(asyncio.create_task(task.run_test()))
                                        self.config.ranorex.all_licenses -= 1
                                        self.logger.debug(f"Всего лицензий - {self.config.ranorex.all_licenses}")

                                await asyncio.sleep(4)

            # Очистить ОС, которые остались
            await self.clear_os()

        async def check_if_completed() -> None:
            """ Проверить протестировалось ли по """

            need_testing_po: int = 0  # всего необходимых тестов
            for po in self.testing_po:
                for _task in po.tasks:
                    need_testing_po += 1

            finish_testing_po: int = 0
            for po in self.testing_po:
                for task in po.tasks:
                    if task.state == State.DONE:
                        finish_testing_po += 1

            if need_testing_po == finish_testing_po:
                self.testing = False

            await asyncio.sleep(2)

        self.logger.debug("Запуск тестов")
        await task_creator()

        if len(self.testing_po) > 0:
            self.logger.debug(f"Отправляем сообщения на почту")
            await self.file_reports()

        await self.clear_os()
        self.logger.debug("Тестирование окончено")

        # Закрытие обработчиков и удаление их из логгера, для того что бы при следующем запуске не было ошибки
        # =OSError(24, 'Too many open files')
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

    async def file_reports(self) -> None:
        """
        Отправляет отчеты на почту
        """

        zip_converter = ZipConverter(self.config, self.logger)
        zip_converter.convert_to_zip()
        zip_converter.send_email_zip_logs()

    async def clear_os(self) -> None:
        """
        Почистить виртуальные машины, если они остались после тестирования
        по шаблону вхождения слов в названии вм "clone"
        """
        sphere = VSphereManager(self.config, self.logger)
        await sphere.delete_all_clone("clone")

    async def start_app_manager(self) -> None:
        """ Запуск менеджера в текущий момент. """

        self.logger.debug(f"Тест менеджер запущен сейчас")
        await self.clear_os()
        await self.initializing()
        await self.run_tests()
        # del self

    async def run_schedule_for_test_manager(self) -> None:
        """ Запуск тест менеджера в планировщике. """

        while True:
            try:
                self.logger.debug(f"Тест менеджер запущен в планировщике")
                loop = asyncio.get_event_loop()
                schedule = Schedule(
                    self.logger,
                    self.config.scheduler.time_for_test_activate,
                    self.start_app_manager,
                )
                loop.run_until_complete(await schedule.run_schedule())
            except Exception as ex:
                self.logger.exception(str(ex))


if __name__ == '__main__':
    config_app = read_yaml_config(r'C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml')
    asyncio.run(TestManager(**config_app).clear_os())
