from typing import Optional, List
from peewee import SqliteDatabase, Model, CharField, AutoField
from TestManager.main_logic.utils.READ_CONFIG import TestManagerConfig, read_yaml_config, read_test_manager_config
from TestManager.main_logic.utils.logger import get_logger


class DataBase:
    def __init__(self, _app_config: TestManagerConfig, log: get_logger):
        self._app_config = _app_config
        self.logger = log
        self.db = SqliteDatabase(_app_config.team_city.history_file_path)

        class BaseModel(Model):
            class Meta:
                database = self.db

        class TestBuilds(BaseModel):
            id = AutoField(primary_key=True)
            soft_name = CharField()
            build_number = CharField()

        self.db.connect()
        self.db.create_tables([TestBuilds], safe=True)

        self.TestBuilds = TestBuilds

    def __enter__(self) -> 'DataBase':
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.db.close()

    def save_build_number(self, soft_name: str, build_number: str) -> None:
        with self.db.atomic():
            try:
                # Попробуйте получить существующую запись
                existing_build = self.TestBuilds.get(self.TestBuilds.soft_name == soft_name)
                # Если запись уже существует, обновите значение build_number
                existing_build.build_number = str(build_number)
                existing_build.save()  # сохраняем обновленную запись
            except self.TestBuilds.DoesNotExist:
                # Если запись отсутствует, создаем новую запись с указанным soft_name и build_number
                self.TestBuilds.create(soft_name=soft_name, build_number=build_number)

    def get_build_number_for_soft(self, soft_name: str) -> Optional[str]:
        try:
            build = self.TestBuilds.get(self.TestBuilds.soft_name == soft_name)
            return build.build_number
        except self.TestBuilds.DoesNotExist:
            return None


if __name__ == '__main__':
    CONFIG_FILE: str = r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml"
    data = read_yaml_config(CONFIG_FILE)

    test_manager_config: TestManagerConfig = read_test_manager_config(read_yaml_config(CONFIG_FILE))
    logger = get_logger(test_manager_config)

    with DataBase(test_manager_config, logger) as xl:
        program_builds: List[str] = [po.soft_name for po in test_manager_config.team_city.for_test_programs_info]

        # Сохранение данных для всех программ
        for program in program_builds:
            xl.save_build_number(program, "1")

        # Получение последних данных для всех программ
        for program in program_builds:
            last_build: Optional[str] = xl.get_build_number_for_soft(program)
            if last_build is not None:
                print(f"Last build number for {program}: {last_build}")
            else:
                print(f"No build number found for {program}")
