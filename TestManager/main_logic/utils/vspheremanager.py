import asyncio
import random
import re
from typing import List, Any

from pyvmlib import *

from TestManager.main_logic.utils.READ_CONFIG import TestManagerConfig, read_test_manager_config, read_yaml_config
import paramiko

from TestManager.main_logic.utils.logger import get_logger


class VSphereManager:
    def __init__(self, app_config: TestManagerConfig, log):
        """Класс для взаимодействия с vSphere, управления виртуальными машинами и USB-устройствами."""
        self.snapshot_ref = None
        self.vsphere_config = app_config.vsphere
        self.list_vms_names_for_ranorex_tests: List = list(self.vsphere_config.all_vms_and_auth.keys())

        self.data_store = self.vsphere_config.data_store

        self.logger = log

    def __get_connect(self) -> Connection:
        """Получение подключения к vSphere."""
        conn = Connection(
            self.vsphere_config.host,
            self.vsphere_config.user,
            self.vsphere_config.password,
            ignore_ssl_error=True
        )
        return conn

    def host_get_all_info_about_usb(self) -> List[Any]:
        """Получение информации о всех USB-устройствах на хосте."""
        with self.__get_connect() as c:
            return c.list_usb_devices_on_host()

    def host_get_the_entire_list_of_unused_usb(self) -> List[Any]:
        """Получение информации о неиспользуемых USB-устройствах на хосте."""
        list_usb_dev = self.host_get_all_info_about_usb()
        return [usb for usb in list_usb_dev if usb.summary is None]

    def host_get_the_entire_usb_list(self) -> List[str]:
        """Получение списка всех USB-устройств на хосте."""
        list_usb_dev = self.host_get_all_info_about_usb()
        all_vms_if_summary_is_none = [usb.physicalPath for usb in list_usb_dev]
        return all_vms_if_summary_is_none

    def host_show_information_about_unused_vm(self) -> None:
        """Вывод информации о неиспользуемых USB-устройствах на хосте."""
        usb_dont_use = self.host_get_the_entire_list_of_unused_usb()
        self.logger.debug(f"Всего не используемых USB - {len(usb_dont_use)}")
        for usb in usb_dont_use:
            self.logger.debug(usb.name, usb.vendor, usb.physicalPath, usb.description, usb.product, usb.speed)

    def host_check_if_the_required_usb_is_connected(self, usb_path: str) -> bool:
        """Проверка подключения конкретного USB-устройства к хосту."""
        checker = False
        for usb in self.host_get_the_entire_usb_list():
            if usb == usb_path:
                checker = True
        return checker

    def vm_restore_by_name(
            self, vm_name: str = "Fishzone_windows 7",
            snapshot_name: str = "Все готово к авто тестам"
    ) -> None:
        """Восстановление виртуальной машины из снимка."""
        with self.__get_connect() as c:
            for vm in c.list_vms():
                if vm["name"] in self.list_vms_names_for_ranorex_tests:
                    if vm["name"] == vm_name:
                        c.revert_vm_to_snapshot(vm["name"], snapshot_name)
                        self.logger.debug(f"Виртуальная машина -> {vm['name']}, "
                                          f"ip_adr -> {c.get_ip_addresses(c.get_vm(vm['name']))} -> "
                                          f"восстановлена")

    async def vm_insert_usb_into_virtual_machine(self, vm_name: str, list_usb: List[str]) -> None:
        """Вставка USB-устройств в виртуальную машину."""
        with self.__get_connect() as c:
            for vm in c.list_vms():
                if vm["name"] == vm_name:
                    await asyncio.sleep(1)
                    for usb_path in list_usb:
                        try_count = 3
                        while 0 != try_count:
                            try:
                                await asyncio.sleep(random.randint(1, 4))
                                c.insert_usb_device(vm["name"], usb_path)
                                self.logger.debug(f"Для {vm_name}, usb -> {usb_path} -> прокинуто")
                                break
                            except Exception as e:
                                self.logger.exception(
                                    f"Произошла ошибка подключения USB к вм {vm_name} {' '.join(list_usb)} {e}"
                                )
                                try_count -= 1

    def vm_show_usb_info(self, vm_name: str) -> None:
        """Вывод информации о USB-устройствах, подключенных к виртуальной машине."""
        with self.__get_connect() as c:
            for vm in c.list_vms():
                if vm["name"] in self.list_vms_names_for_ranorex_tests:
                    if vm["name"] == vm_name:
                        self.logger.debug(f"Виртуальная машина -> {vm['name']}, "
                                          f"ip_adr -> {c.get_ip_addresses(c.get_vm(vm['name']))}")
                        for dev in c.list_usb_devices_on_guest(vm["name"]):
                            self.logger.debug(dev)

    async def vm_remove_usb(self, vm_name: str, list_usb: List[str]) -> None:
        """Удаление USB-устройств из виртуальной машины."""
        with self.__get_connect() as c:
            vm = c.get_vm(vm_name)
            self.logger.debug(f"Виртуальная машина - {vm_name}")
            for usb_path in list_usb:
                await asyncio.sleep(1.5)
                try:
                    c.remove_usb_device(vm, usb_path)
                    self.logger.debug(f"usb -> {usb_path} -> убрано из вм")
                except Exception as ex:
                    self.logger.exception(f"Произошла ошибка при попытке изъятия USB {usb_path}, {ex}")

    def clone_vm_from_snapshot(self, connect: Connection, ds: Any, folder: Any, resource_pool: Any,
                               source_vm: Any, snapshot_name: str, vm_name: str) -> Any:
        """Клонирование виртуальной машины из снимка."""
        from pyVmomi import vim
        """
        Linked-clone a VM with a shapshot, to a VM.

        Arguments:
        :param ds: The datastore for the clone (see `get_datastore`)
        :param folder: The folder for the clone (see `get_folder`)
        :param resource_pool: The resource pool for the clone (see
                `get_resourcepool`)
        :param source_vm: The VM Template to clone (see `get_vm`)
        :param vm_name: The new name for the resulting VM
        """

        self.logger.info("Cloning %s to %s...", source_vm.name, vm_name)
        self.snapshot_ref = False

        def get_child_snap(childSnapshotList):
            """ Проверить дочерний снапшот """
            # Итерация по дочернему снапшоту (если он есть)
            # for snap in tree.childSnapshotList:
            for snap in childSnapshotList:
                if snap.name == snapshot_name:
                    self.snapshot_ref = snap.snapshot
                    break
                else:
                    if len(snap.childSnapshotList) > 0:
                        get_child_snap(snap.childSnapshotList)

        for tree in source_vm.snapshot.rootSnapshotList:
            get_child_snap(tree.childSnapshotList)
            # Если дочерний снапшот найдет отдать его
            if self.snapshot_ref:
                break
            # Если найден родительский снапшот, то отдать его
            if tree.name == snapshot_name:
                self.snapshot_ref = tree.snapshot
                break

        else:
            raise ValueError("VM %r does not have snapshot %r" % (
                source_vm.name, snapshot_name))
        relocate_spec = vim.vm.RelocateSpec()
        relocate_spec.datastore = ds
        relocate_spec.pool = resource_pool
        relocate_spec.diskMoveType = "createNewChildDiskBacking"
        clone_spec = vim.vm.CloneSpec()
        clone_spec.location = relocate_spec
        clone_spec.snapshot = self.snapshot_ref
        clone_spec.powerOn = False
        clone_spec.template = False
        connect.wait_for_tasks(
            [source_vm.Clone(folder=folder, name=vm_name, spec=clone_spec)])

        vm = connect.get_vm(vm_name, folder=folder, required=True)

        return vm

    async def vm_create_a_copy_by_snapshot(self, vm_name: str, snapshot_name: str, new_wm_name: str) -> str:
        """Создание копии виртуальной машины по заданному снимку.

        Вернет - IP адрес
        """

        with self.__get_connect() as c:
            await asyncio.sleep(1)
            try:
                data_store = c.get_datastore(self.data_store)
            except Exception as ex:
                self.logger.exception(f"Произошла ошибка при попытке получить датастор {ex, ex.__traceback__}")
            await asyncio.sleep(1)

            vm = c.get_vm(vm_name)

            await asyncio.sleep(1)
            folder = c.get_folder(vm.parent.name)
            await asyncio.sleep(1)
            resource_pool = c.get_resourcepool(vm.resourcePool.name)

            new_wm = self.clone_vm_from_snapshot(
                connect=c,
                ds=data_store,
                folder=folder,
                resource_pool=resource_pool,
                source_vm=vm,
                snapshot_name=snapshot_name,
                vm_name=new_wm_name
            )

            self.logger.debug(f"New vm is create -> {new_wm.name}")
            await asyncio.sleep(1)
            c.power_on_vm(new_wm)

            self.logger.debug(f"{new_wm.name} -> power is on")

            await asyncio.sleep(1)
            ip_adr_for_new_wn = await self.vm_wait_ip_adr(new_wm)

            self.logger.debug(f"ip adr -> {ip_adr_for_new_wn}")

            return ip_adr_for_new_wn

    async def vm_wait_ip_adr(self, vm: Any) -> str:
        """Ожидание получения виртуальной машиной IP-адреса."""

        with self.__get_connect() as c:
            await asyncio.sleep(1)
            if isinstance(vm, str):
                await asyncio.sleep(2)
                vm = c.get_vm(vm)

            while True:
                await asyncio.sleep(2)
                ip_adr = c.get_ip_addresses(vm)
                await asyncio.sleep(1)

                if len(ip_adr) > 0:
                    return ip_adr

    async def wm_power_off_and_delete(self, vm_name: str):
        """Выключение и удаление виртуальной машины.

        Добавить проверку, что вм не в списке для соло тестов
        """

        try_count = 3

        while try_count != 0:
            try:
                with self.__get_connect() as c:
                    await asyncio.sleep(random.randint(1, 3))
                    vm = c.get_vm(vm_name)
                    if vm.name not in c.list_vms():
                        await asyncio.sleep(1)
                        c.power_off_vm(vm)

                        await asyncio.sleep(1.5)
                        c.delete_vm(vm)
                        self.logger.debug(f"Виртуальная машина - {vm_name} - удалена")

                        return True
            except:
                try_count -= 1
                await asyncio.sleep(3)

    async def vm_power_off(self, vm_name: str) -> bool:
        """Выключение виртуальной машины."""

        with self.__get_connect() as c:
            await asyncio.sleep(random.randint(1, 3))
            vm = c.get_vm(vm_name)
            if vm.name not in c.list_vms():
                await asyncio.sleep(1)
                c.power_off_vm(vm)

                self.logger.debug(f"Виртуальная машина - {vm_name} - выключена")

                return True

    async def vm_change_ip_address(self, vm, vm_username, vm_password, new_ipaddress, gateway):
        """Изменение IP-адреса виртуальной машины."""

        try:
            with self.__get_connect() as c:
                if isinstance(vm, str):
                    await asyncio.sleep(1)

                await asyncio.sleep(2)

                arguments = f"start-process powershell -verb runas -ArgumentList " \
                            f"'netsh interface ip set address {self.vsphere_config.network_card_name} " \
                            f"static {new_ipaddress} 255.255.255.0 {gateway}' "

                self.logger.debug(arguments)

                proc = c.start_process_in_vm(
                    c.get_vm(vm),
                    vm_username=vm_username,
                    vm_password=vm_password,
                    command=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                    arguments=arguments
                )

                self.logger.debug(f"Процесс запущен {proc}")

                await asyncio.sleep(4)

                arguments = f"start-process powershell -verb runas -ArgumentList " \
                            f"'netsh interface ipv4 add " \
                            f"dns {self.vsphere_config.network_card_name} {self.vsphere_config.dns}'"

                self.logger.debug(arguments)

                proc = c.start_process_in_vm(
                    c.get_vm(vm),
                    vm_username=vm_username,
                    vm_password=vm_password,
                    command=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                    arguments=arguments,
                )

                self.logger.debug(f"Процесс запущен {proc}")
                await asyncio.sleep(17)
                ip_addr = await self.vm_wait_ip_adr(vm)

                await asyncio.sleep(1)

                if str(ip_addr) == new_ipaddress or ip_addr[0] == new_ipaddress:
                    self.logger.info("ip адрес установлен")
                elif ip_addr[0] == new_ipaddress or ip_addr[1] == new_ipaddress:
                    self.logger.info("ip адрес установлен")
                else:
                    self.logger.exception("ip ошибка установки ip адреса, устанавливаем снова")
                    await asyncio.sleep(2)
                    await self.vm_change_ip_address(vm, vm_username, vm_password, new_ipaddress, gateway)

        except Exception as e:
            self.logger.exception(f"Произошла ошибка установки IP адреса {e}, пробуем снова")
            await asyncio.sleep(5)
            await self.vm_change_ip_address(vm, vm_username, vm_password, new_ipaddress, gateway)

        return new_ipaddress

    async def vm_create_snapshot_for(self, vm_name: str, snapshot_name: str):
        """Создание снимка для виртуальной машины."""

        with self.__get_connect() as c:
            vm = c.get_vm(vm_name)
            description = "Test description"
            # Read about dumpMemory :
            #   http://pubs.vmware.com/vi3/sdk/ReferenceGuide/vim.VirtualMachine.html#createSnapshot
            dumpMemory = False
            quiesce = True
            await asyncio.sleep(1)
            c.wait_for_tasks([vm.CreateSnapshot(snapshot_name, description, dumpMemory, quiesce)])
            await asyncio.sleep(1)

    async def delete_vm(self, vm: Any) -> None:
        """Удаление виртуальной машины."""
        with self.__get_connect() as c:
            c.delete_vm(c.get_vm(vm))
            await asyncio.sleep(1)

    async def delete_all_clone(self, pattern: str) -> None:
        """ Удаление всех клонов виртуальных машин по шаблону вхождения слова "pattern" """

        async def delete_clone_task(vm):
            with self.__get_connect() as c:
                await self.wm_power_off_and_delete(vm)

        vms_for_delete_tasks = []

        with self.__get_connect() as c:
            list_vms = c.list_vms()

            for vm in list_vms:
                if pattern in vm["name"]:
                    vms_for_delete_tasks.append(asyncio.create_task(delete_clone_task(vm['name'])))

            await asyncio.gather(*vms_for_delete_tasks)

    async def usb_by_id(self, vm_name="Fishzone_Win10x64"):
        """Подключение USB-устройств к виртуальной машине по их идентификаторам."""

        def hid_to_normal_id(iSerial="080000000000000F"):
            length = int(iSerial[:2], 16)  # получаем длину строки из первых двух символов
            device_id_hex = iSerial[2:]  # отрезаем первые два символа
            device_id = str(int(device_id_hex, 16)).zfill(
                length)  # конвертируем в десятичное число и дополняем нулями до нужной длины
            # print("Device ID: ", device_id)
            return device_id

        hid_to_normal_id()

        def ssh_get_info(command: str, pty=False):
            """ Получить вывод команды ssh """
            # Создаем объект SSHClient
            ssh = paramiko.SSHClient()
            # Отключаем проверку ключей SSH
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            # Подключение к серверу с использованием пароля
            ssh.connect('192.168.202.5', username='root', password='0Bolid0Bolid')
            # Выполняем команду на удаленном сервере
            stdin, stdout, stderr = ssh.exec_command(
                command,
                get_pty=pty
            )
            data = stdout.read().decode()
            # print(data)
            # Закрываем соединение
            # ssh.close()
            return data

        def convert_usb_info(_usb_data):
            # Извлечь информацию об устройствах с помощью регулярного выражения
            pattern = r"Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+(\w{4}:\w{4}).*\n\s+iSerial\s+\d+\s+([^\s\n]+)?\n"
            matches = re.findall(pattern, _usb_data)

            # Добавить информацию об устройствах в список
            usb_devices = [{"Bus": match[0], "Device": match[1], "ID": match[2], "Serial Number": match[3]} for match in
                           matches]

            # Вывести список устройств
            for device in usb_devices:
                print(device)
                if device['Serial Number']:
                    device['Serial Number'] = hid_to_normal_id(device['Serial Number'])
                print(device)

        # Получить вывод инфы по USB устройствам
        usb_data = ssh_get_info("""lsusb -v | grep -e Bus -e iSerial""")
        # Конвертировать в удобный формат данных и конвертировать iSerial
        convert_usb_info(usb_data)

        usb_path_data = ssh_get_info("""lsusb -t""", True)
        print(usb_path_data)

        # self.vm_show_usb_info(vm_name)
        # self.get_all_usb_devices()
        self.test_test()

    def test_test(self):

        with self.__get_connect() as c:
            vm = c.get_vm("Fishzone_Win10x64")

            # Подключение к vCenter Server или ESXi хосту
            devices = c.list_usb_devices_on_guest(vm)

            for device in devices:
                print('Device:', device)

            # devices = c.list_usb_devices_on_host(vm)
            # for device in devices:
            #     print('Device:', device)

    def get_all_usb_devices(self):
        """Получение информации о всех USB-устройствах."""

        with self.__get_connect() as c:
            # time.sleep(5)
            vm = c.get_vm('Fishzone_Win10x64')

            # Получаем объект-менеджер хоста
            host = c.si.RetrieveContent().rootFolder.childEntity[0].hostFolder.childEntity[0]

            # Получаем список всех виртуальных машин
            vm_list = c.content.viewManager.CreateContainerView(c.content.rootFolder, [vim.VirtualMachine], True).view

            # поиск первого найденного объекта HostSystem
            host_system = c.container.view[0]

            # получение списка всех USB-контроллеров на хосте
            usb_controllers = host_system.hardware.usbInfo.usbController

            # перебор всех контроллеров и вывод информации об устройствах
            for controller in usb_controllers:
                # получение списка всех устройств на контроллере
                devices = controller.device
                for device in devices:
                    # проверка, что устройство - USB-устройство
                    if isinstance(device, vim.host.UsbDevice):
                        # вывод информации об устройстве и его серийном номере
                        print('Устройство: {}, Серийный номер: {}'.format(device.deviceInfo.label,
                                                                          device.iSerialNumber))


# Костыль для подключения и распознания новых USB
# def determine_which_new_flash_drives_are_inserted_into_the_vsphere(_vsphere: VSphereManager):
#     """ (Костыль для добавления ЮСБ path) Функция помогает находить новые флешки которые будут вставлены в VSphere """
#
#     usb_list_up_to_expected_connections = _vsphere.host_get_the_entire_usb_list()
#     logger.debug(f'Получили список юсб на данный момент, их - {len(usb_list_up_to_expected_connections)} - штук\n')
#     logger.debug("Вставьте нужные USB в usb sxi hub и нажмите любую кнопку\n")
#
#     input()
#
#     all_update_usb_list = _vsphere.host_get_the_entire_usb_list()
#     logger.debug(f'Получили новый список юсб, теперь их - {len(usb_list_up_to_expected_connections)} - штук')
#
#     new_usb_list = []
#
#     for usb in all_update_usb_list:
#         if usb not in usb_list_up_to_expected_connections:
#             new_usb_list.append(usb)
#
#     # Вывести список новых ЮСБ
#     logger.debug(f"Новых USB - {len(new_usb_list)} - штук \n")
#     logger.debug(f"Новые USB -> ")
#
#     for new_usb in new_usb_list:
#         logger.debug(new_usb)


# Tests VM
async def test_create_vm_and_delete_vm():
    data = read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml")
    _config_app: TestManagerConfig = read_test_manager_config(data)
    _vsphere = VSphereManager(_config_app, logger)

    vm_name = "Fishzone_win2012"
    vm_to_clone_name = "Fishzone_win2012 clone TEST"
    snapshot_name = "test"

    await _vsphere.vm_create_a_copy_by_snapshot(
        vm_name,
        snapshot_name,
        vm_to_clone_name
    )
    await _vsphere.wm_power_off_and_delete("Fishzone_Win10x64 clone TEST")


# Test snapshot
def test_create_snapshot():
    data = read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml")
    _config_app: TestManagerConfig = read_test_manager_config(data)
    _vsphere = VSphereManager(_config_app, logger)
    _vsphere.vm_create_snapshot_for("Fishzone_Win11x64", "bloc0")


# Tests ip addresses
async def test_get_ip_adr():
    data = read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml")
    _config_app: TestManagerConfig = read_test_manager_config(data)
    _vsphere = VSphereManager(_config_app, logger)
    get_ip_adr = await _vsphere.vm_wait_ip_adr('name_vm')
    # Вместо текста указать имя тестируемой виртуальной машины в ESXI


def test_change_ip_address():
    """ Тест проверки смены IP адресов """

    data = read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml")
    _config_app: TestManagerConfig = read_test_manager_config(data)
    _vsphere = VSphereManager(_config_app, logger)

    list_names_vm: list = list(_config_app.vsphere.all_vms_and_auth.keys())

    asyncio.run(
        _vsphere.vm_change_ip_address(
            "orion_pro Fishzone_Win8.1x64 win_preparation_2 clone use_os",
            _config_app.vsphere.all_vms_and_auth[list_names_vm[2]].login,
            _config_app.vsphere.all_vms_and_auth[list_names_vm[2]].password,
            _config_app.vsphere.static_ip_address_pool[1],
            _config_app.vsphere.gateway
        )
    )


# Test usb
def test_find_usb():
    data = read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml")
    _config_app: TestManagerConfig = read_test_manager_config(data)
    _vsphere = VSphereManager(_config_app, logger)


def remove_usb_in_vm():
    data = read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml")
    _config_app: TestManagerConfig = read_test_manager_config(data)
    _vsphere = VSphereManager(_config_app, logger)
    asyncio.run(_vsphere.vm_remove_usb("Fishzone_Win10x64", ['path:0/1/5/3/1']))


def test_insert_usb():
    data = read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml")
    _config_app: TestManagerConfig = read_test_manager_config(data)
    _vsphere = VSphereManager(_config_app, logger)
    asyncio.run(
        _vsphere.vm_insert_usb_into_virtual_machine("Fishzone_Win10x64", ['path:0/1/5/3/1'])
    )


def test_get_all_vms():
    data = read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml")
    _config_app: TestManagerConfig = read_test_manager_config(data)
    _vsphere = VSphereManager(_config_app, logger)
    print(_vsphere.host_check_if_the_required_usb_is_connected("path:0/1/5/1"))


def test_usb_info_by_id():
    data = read_yaml_config(r"/TestManager/configs/CONFIG.yaml")
    _config_app: TestManagerConfig = read_test_manager_config(data)
    _vsphere = VSphereManager(_config_app, logger)
    asyncio.run(_vsphere.usb_by_id())
    # _vsphere.test_test()
    # _vsphere.get_all_usb_devices()


async def test_create_3_vm():
    data = read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml")
    _config_app: TestManagerConfig = read_test_manager_config(data)
    _vsphere = VSphereManager(_config_app, logger)

    vm_name = "Fishzone_Win10x64"
    vm_to_clone_name = "Fishzone_Win10x64 clone 1"
    snapshot_name = "ranorex10"

    await _vsphere.vm_create_a_copy_by_snapshot(
        vm_name,
        snapshot_name,
        vm_to_clone_name
    )

    vm_name = "Fishzone_Win10x64"
    vm_to_clone_name = "Fishzone_Win10x64 clone 2"
    snapshot_name = "ranorex10"

    await _vsphere.vm_create_a_copy_by_snapshot(
        vm_name,
        snapshot_name,
        vm_to_clone_name
    )

    vm_name = "Fishzone_Win10x64"
    vm_to_clone_name = "Fishzone_Win10x64 clone 3"
    snapshot_name = "ranorex10"

    await _vsphere.vm_create_a_copy_by_snapshot(
        vm_name,
        snapshot_name,
        vm_to_clone_name
    )


async def clear_os():
    sphere = VSphereManager(TestManagerConfig(**test_manager_config), logger)
    await sphere.delete_all_clone("clone")


# Tests
if __name__ == '__main__':
    CONFIG_FILE = r'/CONFIG.yaml'
    test_manager_config = read_test_manager_config(read_yaml_config(CONFIG_FILE))
    logger = get_logger(test_manager_config)

    # remove_usb_in_vm()
    # test_insert_usb()
    # test_change_screen_resolution_for_virtual_machine()
    # test_get_all_vms()

    # test_usb_info_by_id()
    # test_create_vm_and_delete_vm()
    # test_change_ip_address()
    # asyncio.run(test_create_3_vm())
    test_manager_config = read_yaml_config(
        r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml"
    )

