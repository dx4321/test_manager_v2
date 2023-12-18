from typing import Optional, List

from TestManager.main_logic.testing.states import TestState
from TestManager.main_logic.utils.READ_CONFIG import StandModel, KitModel, TestingPOModel


class TestStatus:
    """ Класс родитель для описания общих полей всех тестов """
    current_id: int = 0

    def __init__(self, soft_name: str, last_build: str):
        TestStatus.current_id += 1
        self.test_id: int = TestStatus.current_id
        self.state: TestState
        self.soft_name = soft_name
        self.last_build = last_build


class TestingStandStatus(TestStatus):
    """ Тесты на виртуальных машинах на которых установлена программа с привязкой к стендам """

    def __init__(
            self,
            vm_name: str,
            vm_for_clone_name: str,
            s: StandModel,
            soft_name: str,
            last_build: str,
    ):
        super().__init__(soft_name, last_build)
        self.vm_name = vm_name
        self.vm_for_clone_name = vm_for_clone_name
        self.stand_name = s.stand_name
        self.path_to_test = s.path_to_test
        self.state: TestState = TestState(vm_for_clone_name)  # Состояния для отображения в браузере
        self.state_of_the_prepared_block: bool = False


class VmsPreparatoryTests(TestStatus):
    """ Тесты на подготовку ВМ """

    def __init__(
            self,
            create_snapshot: bool,
            clone_name: str,
            vm_name: str,
            soft_name: str,
            last_build: str,
    ):
        super().__init__(soft_name, last_build)
        self.create_snapshot = create_snapshot
        self.vm_name: str = vm_name
        self.vm_to_clone_name: str = clone_name
        self.state: TestState = TestState(vm_name)  # Состояния для отображения в браузере


class TestingKitStatus:
    """ Тесты на экземпляр ПО """

    def __init__(
            self,
            k: KitModel,
            soft_name: str,
            last_build: str,
    ):
        self.soft_name = soft_name
        self.last_build = last_build
        self.kit_name: str = k.kit_name
        self.snapshot_name = k.snapshot_name
        self.create_snapshot: Optional[bool] = k.create_snapshot
        self.path_to_test_install_check_license: str = k.path_to_test_install_check_license
        self.vms_tests: List[VmsPreparatoryTests] = []
        self.stands_tests_for_vms: Optional[List[TestingStandStatus]] = []

        for i, vm in enumerate(k.vms):
            clone_name = f"{soft_name} {vm} {self.kit_name} clone"
            self.vms_tests.append(
                VmsPreparatoryTests(
                    self.create_snapshot, clone_name, vm,
                    soft_name, last_build
                )
            )
            if k.stands:
                for j, stand in enumerate(k.stands):
                    self.stands_tests_for_vms.append(
                        TestingStandStatus(
                            f"{clone_name}", f"{clone_name} {stand.stand_name}", stand, soft_name, last_build
                        )
                    )
        self.state: TestState = TestState(self.kit_name)


class TestingPOStatus:
    """ Статус тестируемого ПО """

    def __init__(
            self,
            po: TestingPOModel,
            last_bild: str
    ):
        from TestManager.main_logic.TestManager import Task_for_test

        self.soft_name: str = po.name
        self.teamcity_build_number: str = po.last_build
        self.kit_prepare_is_created: bool = False

        self.list_testing_kits: List[TestingKitStatus] = []
        self.tasks: Optional[List[Task_for_test]] = []

        for i, kit in enumerate(po.kits):
            if kit.tests_are_active:
                self.list_testing_kits.append(TestingKitStatus(kit, self.soft_name, last_bild))

        self.state: TestState = TestState(po.name)