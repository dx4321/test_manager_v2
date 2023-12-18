import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from typing import List, Optional

from TestManager.main_logic.utils.READ_CONFIG import read_test_manager_config, TestManagerConfig, read_yaml_config


class Email:
    def __init__(self, server: str, port: int, login: str, password: str, send_from: str):
        """
        Инициализация объекта Email.

        :param server: SMTP-сервер для отправки почты.
        :param port: Порт для подключения к SMTP-серверу.
        :param login: Логин для аутентификации на SMTP-сервере.
        :param password: Пароль для аутентификации на SMTP-сервере.
        :param send_from: Адрес отправителя.
        """
        self.server = server
        self.port = port
        self.login = login
        self.password = password
        self.send_from = send_from

    def send_mail(
            self,
            send_to: List[str],
            subject: str,
            text: str,
            files: Optional[List[str]] = None
    ) -> None:
        """
        Отправка электронной почты.

        :param send_to: Список адресов получателей.
        :param subject: Тема письма.
        :param text: Текст письма.
        :param files: Список путей к файлам для прикрепления (по умолчанию None).
        """
        assert isinstance(send_to, list), "Проверка что send_to -> являются списком получателей"

        msg = MIMEMultipart()
        msg['From'] = self.send_from
        msg['To'] = ", ".join(send_to)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject

        msg.attach(MIMEText(text))

        if files is not None:
            for f in files or []:
                with open(f, "rb") as fil:
                    part = MIMEApplication(fil.read(), Name=basename(f))
                part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
                msg.attach(part)

        smtp = smtplib.SMTP(self.server, self.port)
        smtp.starttls()
        smtp.login(self.login, self.password)
        smtp.sendmail(self.send_from, send_to, msg.as_string())
        smtp.close()


if __name__ == '__main__':
    # Тестовая отправка сообщения с заголовком и файлом
    data = read_yaml_config(r"C:\Users\fishzon\PycharmProjects\test_manager_v2\TestManager\configs\CONFIG.yaml")
    config_app: TestManagerConfig = read_test_manager_config(data)

    email = Email(
        config_app.email.server,
        config_app.email.port,
        config_app.email.login,
        config_app.email.password,
        config_app.email.send_from
    )
    email.send_mail(
        config_app.email.soft["orion_pro"],
        "Тестовое смс с файлом",
        "Текст в теле письма",
        [r"C:\Users\fishzon\PycharmProjects\test99\logs\2023-03-18\20263 orion_pro win2012 bloc1.pdf"]
    )