# Описание состояний
class DeviceState:
    def __init__(self, name):
        self.name = name

    def str(self):
        return self.name


class StandState(DeviceState):
    BUSY = "Busy"
    FREE = "Free"


class State(DeviceState):
    FREE = "Free"  # свободно
    BUSY = "Busy"  # занят
    DONE = "Done"  # закончен


# Управление состояниями
class Device:
    def __init__(self, name):
        self.name = name


class Stand(Device):
    def __init__(self, name):
        super().__init__(name)
        self.state = StandState.FREE

    def set_busy(self):
        self.state = StandState.BUSY

    def set_free(self):
        self.state = StandState.FREE

    def __repr__(self):
        return f"Stand - ({self.name})"


class IP_Address:
    def __init__(self, address: str):
        self.address = address
        self.is_available = True

    def set_availability(self):
        """ Сделать доступным """
        self.is_available = True

    def change_availability(self):
        """ Сделать не доступным """
        self.is_available = False


class TestState(Device):
    def __init__(self, name):
        super().__init__(name)
        self.state = State.FREE

    def set_busy(self):
        self.state = State.BUSY

    def set_done(self):
        self.state = State.DONE

    def set_free(self):
        self.state = State.FREE

    def __repr__(self):
        return f"Test - ({self.name})"


# Tests
if __name__ == "__main__":
    print("Создание стенда")
    stand1 = Stand("Name1")
    print(stand1.state)
    stand1.set_busy()
    print(stand1.state)
    print(stand1)

    print("\nСостояние Теста на win_11 stand5 block1")
    test_for_win_11_stand5_block1 = TestState("win_11 stand5 block1")
    print(test_for_win_11_stand5_block1.state)
    test_for_win_11_stand5_block1.set_busy()
    print(test_for_win_11_stand5_block1.state)
    test_for_win_11_stand5_block1.set_done()
    print(test_for_win_11_stand5_block1.state)
    print(test_for_win_11_stand5_block1)

