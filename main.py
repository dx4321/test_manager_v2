from TestManager.main_logic.utils.READ_CONFIG import read_yaml_config, read_test_manager_config
from TestManager.main_logic.utils.logger import get_logger
from TestManager.web.web import TestManagerWebApp

if __name__ == '__main__':
    MAIN_CONFIG_FILE = r'C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml'
    # CONFIG_FILE = r'C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\test_win11.yaml'

    config_app = read_yaml_config(MAIN_CONFIG_FILE)
    logger = get_logger(read_test_manager_config(config_app))

    test_manager_wb = TestManagerWebApp(logger, MAIN_CONFIG_FILE)
    test_manager_wb.run_flask_app()
