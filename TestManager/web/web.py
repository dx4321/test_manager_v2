import asyncio
import logging
import os
import re
import threading
from collections import defaultdict
from functools import wraps
from pathlib import Path
from typing import Tuple, List, Optional

from flask import flash, send_from_directory, \
    send_file, Flask, render_template, request, redirect, url_for, session, jsonify
from ruamel.yaml import round_trip_load, round_trip_dump

from TestManager.main_logic.utils.logger import get_logger
from TestManager.runner_manager import ManagerStarter
from TestManager.main_logic.utils.READ_CONFIG import read_test_manager_config, read_yaml_config

# Путь к папке с конфигами
config_folder = os.path.join(os.getcwd(), 'TestManager', 'configs')


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'logged_in' in session:
            return view(*args, **kwargs)
        else:
            return redirect(url_for('login'))

    return wrapped_view


class TestManagerWebApp:
    def __init__(self, logger: logging.Logger, log_file_path):

        self.manager: Optional[ManagerStarter] = None

        self.app = Flask(__name__)
        self.app.secret_key = 'test123'
        self.log_file_path = log_file_path

        self.logger = logger
        self.manager_lock = threading.Lock()

        self.app.route('/login', methods=['GET', 'POST'])(self.login)
        self.app.route('/')(self.index)
        self.app.route('/<path:path>')(self.serve_file)
        self.app.route('/download')(self.download_file)
        self.app.route('/read_log', methods=['GET'])(self.read_log)
        self.app.route('/logs', methods=['GET'])(self.logs)
        self.app.route('/config', methods=['GET'])(self.edit_config)
        self.app.route('/config/mailing_module', methods=['GET', 'POST'])(self.edit_email_config)
        self.app.route('/config/vsphere_module', methods=['GET', 'POST'])(self.edit_vsphere_config)
        self.app.route('/config/teamcity_config', methods=['GET', 'POST'])(self.save_teamcity_config)
        self.app.route('/config/programs_for_tests', methods=['GET', 'POST'])(self.program_for_test_config)
        self.app.route('/config/scheduler', methods=['GET', 'POST'])(self.scheduler_config)
        self.app.route('/config/ranorex', methods=['GET', 'POST'])(self.ranorex)
        self.app.route('/status', methods=['GET', 'POST'])(self.status)
        self.app.route('/apply-config', methods=['GET', 'POST'])(self.apply_config)
        self.app.route('/stop-manager', methods=['GET', 'POST'])(self.stop_manager)
        self.app.route('/clear-clones', methods=['GET', 'POST'])(self.clear_tests_vm_os)

    def read_config(self):
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as file:
                config = round_trip_load(file)
                return config
        except Exception as e:
            print(f"Ошибка при чтении конфигурационного файла: {e}")
            return None

    def write_config(self, config):
        try:
            with open(self.log_file_path, 'w', encoding='utf-8') as file:
                round_trip_dump(config, file)
        except Exception as e:
            print(f"Ошибка при записи в конфигурационный файл: {e}")

    @staticmethod
    def login():
        if request.method == 'POST':
            password = request.form['password']
            if password == '311':
                session['logged_in'] = True
                return redirect(url_for('edit_config'))
            else:
                return render_template('login.html', error='Invalid password')
        return render_template('login.html')

    @login_required
    def index(self):
        config = self.read_config()
        return render_template('index.html', config=config)

    @staticmethod
    def serve_file(path):
        directory, filename = os.path.split(path)
        return send_from_directory('//' + directory, filename)

    @staticmethod
    def get_folders_and_files_in_folder(folder_path) -> Tuple[List[str], List[str]]:
        folders = [item.name for item in folder_path.iterdir() if item.is_dir()]
        files = [item.name for item in folder_path.iterdir() if item.is_file()]
        return folders, files

    def create_report_for_this_day(self):
        """ Создать отчет о пройденных тестах за день

        Необходима сделать сводную информацию о пройденных тестах всех ПО, всех vm, всех наборов тестов.
        Нужно указать сколько было пройденных тестов, сколько тестов сломалось. Должна быть сводная информация

        """
        ...

    def download_file(self):
        def is_valid_file_path(_file_path, _network_folder):
            return _file_path.startswith(_network_folder)

        config = self.read_config()
        network_folder = config['Ranorex']['dir_to_logs']
        file_path = request.args.get('file')

        if file_path and is_valid_file_path(file_path, network_folder):
            return send_file(file_path, as_attachment=True)
        else:
            return 'Файл не указан или недопустимый путь.'

    @staticmethod
    def read_log():
        file = request.args.get('file')
        with open(file, 'r') as f:
            log_content = f.read()

        return render_template('log.html', log_content=log_content)

    @staticmethod
    def starts_with_digit(string):
        if string[0].isdigit():
            return True
        else:
            return False

    def logs(self):
        config = self.read_config()
        network_folder = config['Ranorex']['dir_to_logs']
        current_folder = request.args.get('folder', network_folder)
        current_folder_path = Path(network_folder).joinpath(current_folder)

        path_parts = current_folder.split('/')
        paths = [{'name': part, 'path': '/logs?folder=' + '/'.join(path_parts[:i + 1])} for i, part in
                 enumerate(path_parts)
                 if '/'.join(path_parts[:i + 1]) != network_folder]

        folders, files = self.get_folders_and_files_in_folder(current_folder_path)
        regex_pattern = r'(^\w+ )(\w+?_)(\w+)(.+)'
        regex_math = r'\3\4'

        report_files = defaultdict(list)
        for file in files:
            if file.endswith(('.log', '.pdf', 'rxzlog')):
                clear_name = re.sub(regex_pattern, regex_math, file.split('.')[0])
                report_files[clear_name].append(file)

        for folder in folders:
            folder_path = current_folder_path.joinpath(folder)
            html_files = [item for item in Path(folder_path).iterdir() if item.is_file() and item.suffix == '.html']
            if html_files:
                folder_files = [file for file in html_files if file not in report_files]
                for html_file in folder_files:
                    if self.starts_with_digit(folder):
                        clear_assembly_number = folder
                        file_path = Path(folder_path).joinpath(html_file)
                        report_files[clear_assembly_number].append(str(file_path.absolute()))
                    else:
                        clear_assembly_number = re.sub(regex_pattern, regex_math, folder)
                        file_path = Path(folder_path).joinpath(html_file)
                        report_files[clear_assembly_number].append(str(file_path.absolute()))

        for file in files:
            if ".rxzlog" in current_folder_path.joinpath(file).name:
                build_number = current_folder_path.joinpath(file).parent.parent.name
                return render_template('logs.html', report_files=report_files, current_folder=current_folder,
                                       full_path=paths, build_number=build_number)

        return render_template('logs.html', report_files=report_files, folders=folders, files=files,
                               current_folder=current_folder, full_path=paths)

    @login_required
    def edit_config(self):
        config = self.read_config()
        if request.method == 'POST':
            # Получаем название выбранного конфига
            selected_config = request.form['config']

            # Действия при выборе конфига
            # Например, загрузка выбранного конфига и его применение

            # Получаем список всех конфигов в папке
        all_configs = os.listdir(config_folder)
        return render_template('config.html', configs=all_configs)

    # Функция для создания нового конфига

    # def create_config(self):
    #     if request.method == 'POST':
    #         # Получаем данные для создания нового конфига
    #         # Например, название и содержимое нового конфига
    #         new_config_name = request.form['new_config_name']
    #         new_config_content = request.form['new_config_content']
    #
    #         # Создаем новый конфиг
    #         with open(os.path.join(config_folder, new_config_name), 'w') as file:
    #             file.write(new_config_content)
    #
    #         # Действия после создания нового конфига
    #         # Например, применение нового конфига
    #
    #     return render_template('create_config.html')

    def edit_email_config(self):
        config = self.read_config()
        email_config = config['Email']

        if request.method == 'POST':
            email_config['server'] = request.form['email_server']
            email_config['port'] = int(request.form['email_port'])
            email_config['send_from'] = request.form['email_send_from']
            email_config['login'] = request.form['email_login']
            email_config['password'] = request.form['email_password']

            if request.form['new_soft_key_input']:
                email_config['soft'][request.form['new_soft_key_input']] = []

            for key, value in email_config['soft'].copy().items():
                new_emails = request.form.getlist(f'new_email_{key}')
                existing_emails = request.form.getlist(f'email_{key}')
                all_emails = [email for email in existing_emails if email] + new_emails
                email_config['soft'][key] = all_emails
                if key.startswith("new_email_"):
                    soft_key = key.replace("new_email_", "")
                    email_config['soft'][soft_key].append(value)

            for key in email_config['soft']:
                email_config['soft'][key] = [val for val in email_config['soft'][key] if val]

            removed_soft_key = request.form.get('removed_soft_key')

            if removed_soft_key:
                if removed_soft_key in email_config['soft']:
                    del email_config['soft'][removed_soft_key]
                else:
                    flash(f'Софт с ключом "{removed_soft_key}" не найден', 'error')

            self.write_config(config)
            config = self.read_config()

        return render_template('config/mailing_module.html', config=config)

    def edit_vsphere_config(self):
        config = self.read_config()
        vsphere_config = config['VSphere']

        if request.method == 'POST':
            vsphere_config['host'] = request.form['vsphere_host']
            vsphere_config['user'] = request.form['vsphere_user']
            vsphere_config['password'] = request.form['vsphere_password']
            vsphere_config['data_store'] = request.form['vsphere_data_store']

            all_vms_and_auth = {}
            for key in request.form:
                if key.startswith('vsphere_vm_login_'):
                    vm_name = key.replace('vsphere_vm_login_', '')
                    password_key = f'vsphere_vm_password_{vm_name}'
                    login_value = request.form[key]
                    password_value = request.form[password_key]
                    all_vms_and_auth[vm_name] = {'login': login_value, 'password': password_value}

            for key in request.form:
                if key.startswith('vsphere_vm_login_'):
                    vm_name = key.replace('vsphere_vm_login_', '')
                    login = request.form[key]
                    password_key = 'vsphere_vm_password_' + vm_name
                    if password_key in request.form:
                        password = request.form[password_key]
                        config['VSphere']['all_vms_and_auth'][vm_name] = {'login': login, 'password': password}

            removed_vm = request.form.get('removed_vm_input')
            if removed_vm:
                vsphere_config['all_vms_and_auth'].pop(removed_vm, None)

            vsphere_config['all_vms_and_auth'] = all_vms_and_auth
            vsphere_config['network_card_name'] = request.form['vsphere_network_card_name']

            static_ip_addresses = []
            if request.form['new_static_ip']:
                static_ip_addresses.append(request.form['new_static_ip'])
            for ip_address in request.form.getlist('vsphere_static_ip'):
                if ip_address:
                    static_ip_addresses.append(ip_address)

            vsphere_config['static_ip_address_pool'] = static_ip_addresses
            vsphere_config['gateway'] = request.form['vsphere_gateway']
            vsphere_config['dns'] = request.form['vsphere_dns']

            self.write_config(config)
            config = self.read_config()

        return render_template('config/vsphere_module.html', config=config)

    def save_teamcity_config(self):
        config = self.read_config()

        if request.method == 'POST':
            teamcity_token = request.form['teamcity_token']
            check_for_the_latest_release = request.form['activation_option'].lower() == 'true'
            history_file_path = request.form['history_file_path']

            programs = []
            for key in request.form:
                if key.startswith('program['):
                    program_index = key.split('[')[1].split(']')[0]
                    program = {
                        'soft_name': request.form.get(f"program[{program_index}][soft_name]"),
                        'last_build': request.form.get(f"program[{program_index}][last_build]"),
                        'distro_full_path_for_download': request.form.get(f"program[{program_index}][distro_full_path]")
                    }
                    programs.append(program)

            unique_softwares = []
            seen = set()
            for software in programs:
                software_tuple = tuple(software.items())
                if software_tuple not in seen:
                    unique_softwares.append(software)
                    seen.add(software_tuple)

            config['TeamCity']['token'] = teamcity_token
            config['TeamCity']['check_for_the_latest_release'] = check_for_the_latest_release
            config['TeamCity']['HistoryFilePath'] = history_file_path
            config['TeamCity']['for_test_programs_info'] = unique_softwares

            self.write_config(config)

        return render_template('config/teamcity_config.html', config=config)

    def program_for_test_config(self):
        config = self.read_config()  # Функция для чтения конфигурации (замените её на свою логику чтения конфигурации)

        if request.method == 'POST':
            # Добавление программ
            program_names_from_form = [
                program_name.replace("_name", "") for program_name in request.form if program_name.endswith('_name')
                                                                                      and not any(
                    x in program_name for x in ['win_preparation', 'snapshot'])
            ]
            program_names_from_config = [program['name'] for program in config['ProgramsForTests']]
            program_names_to_delete = list(set(program_names_from_config) - set(program_names_from_form))

            # Удалить программу
            config['ProgramsForTests'] = [program for program in config['ProgramsForTests'] if
                                          program['name'] not in program_names_to_delete]

            for program in config['ProgramsForTests']:
                # Обновление названия программы и ее полей
                program_name = program['name']
                program_name_key = f"{program_name}_name"
                val = request.form[f"{program['name']}_tests_are_active"]
                program['tests_are_active'] = True if val.lower() == "true" else False
                if program_name_key in request.form:
                    new_program_name = request.form[program_name_key]
                    if new_program_name:
                        program['name'] = new_program_name

                program_last_build_key = f"{program_name}_last_build"
                if program_last_build_key in request.form:
                    program['last_build'] = request.form[program_last_build_key]

                list_config_keys = [kit for kit in program['kits']]
                list_form_keys = [key for key in request.form.keys()]
                program['kits'] = []
                for key_conf in list_config_keys:
                    for key in list_form_keys:
                        if key_conf['kit_name'] in key:
                            program['kits'].append(key_conf)
                            break

                # Удаление kit
                for kit in program['kits']:
                    kit_name = kit['kit_name']

                    kit_name_key = f"{program_name}_{kit_name}_kit_name"

                    # Проверить изменения с веб интерфейса по отключенным наборам
                    val = request.form[f"{program['name']}_{kit_name}_tests_are_active"]
                    kit['tests_are_active'] = True if val.lower() == "true" else False

                    if kit_name_key in request.form:
                        new_kit_name = request.form[kit_name_key]
                        if new_kit_name != kit_name:  # проверяем, есть ли изменения в названии набора тестов
                            kit['kit_name'] = new_kit_name  # обновляем только название набора тестов

                    key_snapshot_name = f"{program_name}_{kit_name}_snapshot_name"
                    if key_snapshot_name in request.form:
                        kit['snapshot_name'] = request.form[key_snapshot_name]

                    kit_path_key = f"{program_name}_{kit_name}_path_to_test_install_check_license"
                    if kit_path_key in request.form:
                        kit['path_to_test_install_check_license'] = request.form[kit_path_key]

                    vms = []
                    vm_keys = [key for key in request.form if key.startswith(f"{program_name}_{kit_name}_vms")]
                    for vm_key in vm_keys:
                        vm_value = request.form.get(vm_key)
                        if vm_value != "":
                            vms.append(vm_value)
                    kit['vms'] = vms

                    # Работа со стендами
                    stand_keys = [key for key in request.form if
                                  key.startswith(f"{program_name}_{kit_name}_stand_name")]
                    stands = []
                    for i, stand_key in enumerate(stand_keys):
                        path_key = f"{program_name}_{kit_name}_path_to_test[{i}]"
                        if path_key in request.form.keys():
                            s_k = request.form[stand_key]
                            p_k = request.form[path_key]
                            if s_k == "" and p_k == "":
                                pass
                            else:
                                stands.append({
                                    'stand_name': request.form[stand_key],
                                    'path_to_test': request.form[path_key]
                                })

                    kit['stands'] = stands

                # Добавление набора
                if len(request.form[f'{program_name}_new_kit_name']) > 0:
                    program['kits'].append(
                        {
                            'kit_name': request.form[f'{program_name}_new_kit_name'],
                            "tests_are_active": False,
                            'snapshot_name': request.form[f'{program_name}_new_snapshot_name'],
                            'path_to_test_install_check_license':
                                request.form[f'{program_name}_new_kit_path_to_test'],
                            'vms': [],
                            'stands': []
                        }
                    )

            # Добавление новой программы
            if request.form['new_program_name'] != "":
                config['ProgramsForTests'].append(
                    {
                        "name": request.form['new_program_name'],
                        "tests_are_active": False,
                        "last_build": "inTeamCityGetInModule",
                        'kits': [
                        ]
                    }
                )

            # Сохраняем обновленную конфигурацию в файл или базу данных
            self.write_config(config)

        return render_template('config/programs_for_tests.html', config=config)

    def scheduler_config(self):

        config = self.read_config()
        if request.method == 'POST':
            config["Scheduler"]["TimeForTestActivate"] = request.form["scheduler_time_for_test_activate"]
            config["Scheduler"]["ActivateByTime"] = request.form['activation_option'].lower() == 'true'
            # Сохраняем обновленную конфигурацию в файл или базу данных
            self.write_config(config)
        return render_template('config/scheduler.html', config=config)

    def ranorex(self):
        config = self.read_config()
        if request.method == 'POST':
            config["Ranorex"]["all_licenses"] = request.form["all_licenses"]
            config["Ranorex"]["agent_port"] = request.form['agent_port']
            config["Ranorex"]["dir_to_logs"] = request.form['dir_to_logs']
            config["Ranorex"]["path_to_pdf_converter"] = request.form['path_to_pdf_converter']
            # Сохраняем обновленную конфигурацию в файл или базу данных
            self.write_config(config)

        return render_template('/config/ranorex.html', config=config)

    def run_flask_app(self):
        """ Запускаем в два потока веб интерфейс и тест менеджер """

        self.manager = ManagerStarter(self.log_file_path)

        self.manager.start_test_manager()
        self.logger.info("Веб интерфейс запущен")

        flask_thread = threading.Thread(target=self.run_flask_task)
        flask_thread.start()

    def run_flask_task(self):
        with self.manager_lock:
            self.app.run(host='0.0.0.0')

    def status(self):
        """ Возвращает текущий статус службы """
        return jsonify(status=str(self.manager.test_manager_running))

    def apply_config(self):
        """ Применить и перезагрузить конфиг """
        config = self.read_config()

        # Сохраняем обновленную конфигурацию в файл или базу данных
        if request.method == 'POST':
            self.write_config(config)
            self.manager.stop_test_manager()
            self.manager.start_test_manager()
            return jsonify(result=str(self.manager.test_manager_running))

    def stop_manager(self):
        """ Остановить менеджер """
        config = self.read_config()

        if request.method == 'POST':
            self.write_config(config)
            self.manager.stop_test_manager()
            return jsonify(result=str(self.manager.test_manager_running))

    def clear_tests_vm_os(self):
        """ Почистить виртуальные машины """
        config = self.read_config()

        if request.method == 'POST':
            self.write_config(config)
            try:
                asyncio.run(self.manager.test_manager.clear_os())
                return jsonify(result=str("OK"))
            except Exception as ex:
                return jsonify(result=str(f"Произошла ошибка {ex}"))


if __name__ == '__main__':
    CONFIG_FILE = r'/CONFIG.yaml'

    config_app = read_yaml_config(CONFIG_FILE)
    logger = get_logger(read_test_manager_config(config_app))

    test_manager_wb = TestManagerWebApp(logger, CONFIG_FILE)
    flask_thread = threading.Thread(target=test_manager_wb.run_flask_app)
    flask_thread.start()
