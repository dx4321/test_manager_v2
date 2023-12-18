from typing import List, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class Email(BaseModel):
    """ Информация о настройках почты и получателях отчетов (в зависимости от софта) """

    server: str
    port: int
    send_from: str
    login: str
    password: str
    soft: dict


class VSphere(BaseModel):
    """ Для конфигурации VSphere """

    class VmAuth(BaseModel):
        """ Для авторизационных данных виртуальных машин """

        login: str
        password: str

    host: str
    user: str
    password: str

    data_store: str
    all_vms_and_auth: Dict[str, VmAuth]
    # snapshot_name: str

    network_card_name: str
    static_ip_address_pool: List
    gateway: str
    dns: str


class TeamCitySoft(BaseModel):
    """ Объект софта с информацией о нем """
    soft_name: str
    last_build: str
    distro_full_path_for_download: str


class TeamCityConfig(BaseModel):
    """ Для авторизационных данных тим сити """

    token: str
    check_for_the_latest_release: bool
    for_test_programs_info: List[TeamCitySoft]
    history_file_path: str = Field(alias="HistoryFilePath")


class Ranorex(BaseModel):
    """ Информация об артефактах Ranorex """

    all_licenses: int  # Всего лицензий
    agent_port: str  # Порт на котором работает ранорекс агент
    dir_to_logs: str  # Папка для логов
    path_to_pdf_converter: str  # Путь до Ranorex PDF конвертора (.exe)


class StandModel(BaseModel):
    """ Стенд для тестов на ОС """
    stand_name: str
    path_to_test: str


class KitModel(BaseModel):
    """ Блок тестируемого приложения """

    kit_name: str
    tests_are_active: bool
    snapshot_name: str
    create_snapshot: Optional[bool]
    path_to_test_install_check_license: str
    vms: List[str]
    stands: Optional[List[StandModel]]

    # для кит модуля автоматический создать поле create_snapshot
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.stands:
            self.create_snapshot = True
        else:
            self.create_snapshot = False


class TestingPOModel(BaseModel):
    """ Программы для тестов """

    name: str
    tests_are_active: bool
    last_build: Optional[str]
    kits: List[KitModel]


class Scheduler(BaseModel):
    """ Конфигурация планировщика """

    time_for_test_activate: str = Field(alias="TimeForTestActivate")
    activate_by_time: bool = Field(alias="ActivateByTime")


class TestManagerConfig(BaseModel):
    """ Описание объекта основного модуля управления приложением """

    email: Email = Field(alias="Email")
    vsphere: VSphere = Field(alias="VSphere")
    team_city: TeamCityConfig = Field(alias="TeamCity")
    ranorex: Ranorex = Field(alias="Ranorex")
    program_for_tests: List[TestingPOModel] = Field(alias="ProgramsForTests")
    scheduler: Scheduler = Field(alias="Scheduler")


class MainConfig(BaseModel):
    current_config_is_selected: str
    path_to_the_config_list_folder: str
    ip_address: str
    port: int
    debug: bool


def read_yaml_config(path: str) -> Dict:
    """ Прочесть yaml config и вернуть структуру данных """

    with open(path, "r", encoding="utf-8") as yaml_file:
        _data = yaml.load(yaml_file, Loader=yaml.FullLoader)
        # logger.debug("Read config successful")

    return _data


def read_test_manager_config(_data: dict) -> TestManagerConfig:
    """ Прочесть конфигурацию и создать объект TestManagerConfig """

    return TestManagerConfig(**_data)


def read_main_config(_data: dict) -> MainConfig:
    """ Прочитать основной конфиг """

    return MainConfig(**_data)


# Tests
if __name__ == '__main__':
    data = read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml")
    test_manager = read_test_manager_config(data)
