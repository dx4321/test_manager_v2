// Файл: status.js

// Функция для обновления информации о статусе
function updateStatus() {
  fetch('/status')
    .then(response => response.json())
    .then(data => {
      // Получаем элемент для отображения статуса
      const statusText = document.getElementById('status-text');
      // Устанавливаем текст статуса
      statusText.innerText = data.status;
      // Устанавливаем ярко голубой цвет текста
      statusText.style.color = 'darkblue';
    })
    .catch(error => {
      console.error('Ошибка получения статуса службы:', error);
    });
}

// Функция для отображения модального окна
function openStatusModal() {
  // Создаем модальное окно
  const modal = document.createElement('div');
  modal.classList.add('status-modal');
  modal.innerHTML = `
    <div class="status-modal-content">
      <span id="status-text">Загрузка статуса менеджера тестов...</span>
      <button class="close-button" onclick="closeStatusModal()">X</button>
      <div class="status-buttons">
        <button onclick="applyConfig()">Применить конфиг сейчас и запустить менеджер</button>
        <button onclick="stopManager()">Остановить менеджер</button>
        <button onclick="clearClones()">Очистить клоны OS</button> <!-- Добавляем кнопку "Очистить клоны OS" -->
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  // Обновляем информацию о статусе
  updateStatus();
  // Обновляем информацию о статусе каждые 5 секунд
  setInterval(updateStatus, 5000);

  // Добавляем стили для модального окна
  modal.style.position = 'fixed';
  modal.style.top = '7%';
  modal.style.left = '87%';
  modal.style.transform = 'translate(-50%, -50%)';
  modal.style.width = '400px';
  modal.style.padding = '20px';
  modal.style.backgroundColor = 'white';
  modal.style.border = '2px solid black';
  modal.style.borderRadius = '10px';
  modal.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.5)';

  // Добавляем стили для кнопки "закрыть"
  const closeButton = modal.querySelector('.close-button');
  closeButton.style.position = 'absolute';
  closeButton.style.top = '10px';
  closeButton.style.right = '10px';
  closeButton.style.width = '30px';
  closeButton.style.height = '30px';
  closeButton.style.backgroundColor = 'red';
  closeButton.style.color = 'white';
  closeButton.style.border = '2px solid white';
  closeButton.style.borderRadius = '10px';
  closeButton.style.animation = 'pulse 1s infinite';

  // Добавляем стиль для мигания
  const style = document.createElement('style');
  style.appendChild(document.createTextNode(`
    @keyframes blink {
      0% {opacity: 1;}
      50% {opacity: 0.5;}
      100% {opacity: 1;}
    }
  `));
  document.head.appendChild(style);
}

function clearClones() {
  fetch('/clear-clones', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      // Обновляем информацию о статусе
      updateStatus();
      // Отображаем результат применения конфигурации
      alert('Ответ: ' + data.result);
    })
    .catch(error => {
      console.error('Ошибка применения конфигурации:', error);
    });
}

function applyConfig() {
  fetch('/apply-config', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      // Обновляем информацию о статусе
      updateStatus();
      // Отображаем результат применения конфигурации
      alert('Результат применения конфигурации: ' + data.result);
    })
    .catch(error => {
      console.error('Ошибка применения конфигурации:', error);
    });
}


function stopManager() {
  fetch('/stop-manager', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
      // Обновляем информацию о статусе
      updateStatus();
      // Отображаем результат остановки менеджера
      alert('Результат остановки менеджера: ' + data.result);
    })
    .catch(error => {
      console.error('Ошибка остановки менеджера:', error);
    });
}




// Функция для закрытия модального окна
function closeStatusModal() {
  const modal = document.querySelector('.status-modal');
  if (modal) {
    modal.remove();
  }
}

// Отображаем модальное окно при загрузке страницы
document.addEventListener('DOMContentLoaded', openStatusModal);

function removeField(button) {
  button.parentElement.remove();
}

function removeSoftKey(soft_key) {
  var softKeyElement = document.querySelector(`[data-soft-key="${soft_key}"]`);
  if (softKeyElement) {
    softKeyElement.remove();
    document.getElementById('removed_soft_key_input').value = soft_key;
    // Выполните здесь любую другую логику, связанную с удалением soft_key
  } else {
    alert(`Элемент с ключом "${soft_key}" не найден`);
  }
}

function removeVM(vm_name) {
  var vmElement = document.querySelector(`[data-vm-name="${vm_name}"]`);
  if (vmElement) {
    vmElement.remove();
    var removedVmInput = document.getElementById('removed_vm_input');
    if (removedVmInput) {
      removedVmInput.value = vm_name;
    }
  } else {
    alert(`Элемент с именем "${vm_name}" не найден`);
  }
}

function add_email_Field(soft_key) {
  var container = document.querySelector(`div[data-soft-key="${soft_key}"]`);
  var inputContainer = document.createElement('div');
  inputContainer.className = 'input-container';
  var input = document.createElement('input');
  input.type = 'text';
  input.name = `email_${soft_key}`;
  input.value = '';
  var deleteButton = document.createElement('button');
  deleteButton.className = 'delete-button';
  deleteButton.textContent = 'Удалить';
  deleteButton.onclick = function() {
    inputContainer.parentNode.removeChild(inputContainer);
  };
  inputContainer.appendChild(input);
  inputContainer.appendChild(deleteButton);
  container.insertBefore(inputContainer, container.querySelector('.input-container + hr'));
}

function addField() {
  var newSoftKeyInput = document.getElementById("new_soft_key_input");
  var softKey = newSoftKeyInput.value;

  var newSoftKeysInput = document.getElementById("new_soft_keys");
  if (newSoftKeysInput.value === "") {
    newSoftKeysInput.value = softKey;
  } else {
    newSoftKeysInput.value += "," + softKey;
  }
  newSoftKeyInput.value = "";
}


// Скрипт для сворачивания/разворачивания списка email по умолчанию
var emailLists = document.getElementsByClassName("email-list");
for (var i = 0; i < emailLists.length; i++) {
    emailLists[i].style.display = "none";
}

// Функция для сворачивания/разворачивания списка email
function toggleEmailList(soft_key) {
    var emailList = document.getElementById("email_list_" + soft_key);
    if (emailList.style.display === "none") {
          emailList.style.display = "block";
        } else {
          emailList.style.display = "none";
        }
}


function addVM() {
  var newVMNameInput = document.getElementById("new_vm_name");
  var newVMLoginInput = document.getElementById("new_vm_login");
  var newVMPasswordInput = document.getElementById("new_vm_password");

  var newVMSection = document.getElementById("new_vm_section");

  if (newVMNameInput.value && newVMLoginInput.value && newVMPasswordInput.value) {
    var vmAuthContainer = document.createElement('div');
    vmAuthContainer.className = 'vm-auth';
    vmAuthContainer.setAttribute('data-vm-name', newVMNameInput.value);

    var h4 = document.createElement('h4');
    h4.textContent = newVMNameInput.value;

    var loginLabel = document.createElement('label');
    loginLabel.textContent = 'Логин:';

    var loginInput = document.createElement('input');
    loginInput.type = 'text';
    loginInput.name = 'vsphere_vm_login_' + newVMNameInput.value;
    loginInput.value = newVMLoginInput.value;

    var passwordLabel = document.createElement('label');
    passwordLabel.textContent = 'Пароль:';

    var passwordInput = document.createElement('input');
    passwordInput.type = 'password';
    passwordInput.name = 'vsphere_vm_password_' + newVMNameInput.value;
    passwordInput.value = newVMPasswordInput.value;

    var deleteButton = document.createElement('button');
    deleteButton.className = 'delete-button';
    deleteButton.textContent = 'Удалить ' + newVMNameInput.value;
    deleteButton.onclick = function() {
      vmAuthContainer.parentElement.removeChild(vmAuthContainer);
    };

    var hr = document.createElement('hr');

    vmAuthContainer.appendChild(h4);
    vmAuthContainer.appendChild(loginLabel);
    vmAuthContainer.appendChild(loginInput);
    vmAuthContainer.appendChild(passwordLabel);
    vmAuthContainer.appendChild(passwordInput);
    vmAuthContainer.appendChild(deleteButton);
    vmAuthContainer.appendChild(hr);

    newVMSection.insertAdjacentElement('beforebegin', vmAuthContainer);

    newVMNameInput.value = '';
    newVMLoginInput.value = '';
    newVMPasswordInput.value = '';
  }
}

function removeProgramInfo(soft_name) {
  var programInfoElements = document.getElementsByClassName('program-info');
  for (var i = 0; i < programInfoElements.length; i++) {
    var programInfoElement = programInfoElements[i];
    var inputElement = programInfoElement.querySelector("input[name='program[" + i + "][soft_name]']");
    if (inputElement && inputElement.value === soft_name) {
      programInfoElement.remove();
      // Выполните здесь любую другую логику, связанную с удалением программы
      return;
    }
  }
  alert(`Программа с названием "${soft_name}" не найдена`);
}

function addNewProgram() {
  var programNameInput = document.getElementById("program_name_input");
  var buildRequestInput = document.getElementById("build_request_input");
  var downloadPathInput = document.getElementById("download_path_input");

  var newProgramInfoContainer = document.getElementById("new-program-info");

  var programInfoDiv = document.createElement("div");
  programInfoDiv.classList.add("program-info");

  var nameLabel = document.createElement("label");
  nameLabel.innerText = "Название софта:";
  var nameInput = document.createElement("input");
  nameInput.type = "text";
  nameInput.name = "program[" + programNameInput.value + "][soft_name]";
  nameInput.value = programNameInput.value;

  var requestLabel = document.createElement("label");
  requestLabel.innerText = "Запрос на последнюю сборку:";
  var requestInput = document.createElement("input");
  requestInput.type = "text";
  requestInput.name = "program[" + programNameInput.value + "][last_bild]";
  requestInput.value = buildRequestInput.value;

  var pathLabel = document.createElement("label");
  pathLabel.innerText = "Полный путь до папки в которую будет скачиваться последняя сборка:";
  var pathInput = document.createElement("input");
  pathInput.type = "text";
  pathInput.name = "program[" + programNameInput.value + "][distro_full_path]";
  pathInput.value = downloadPathInput.value;

  var deleteButton = document.createElement("button");
  deleteButton.classList.add("delete-button");
  deleteButton.onclick = function() {
    removeProgramInfo(programNameInput.value);
  };
  deleteButton.innerText = "Удалить";

  programInfoDiv.appendChild(nameLabel);
  programInfoDiv.appendChild(nameInput);
  programInfoDiv.appendChild(requestLabel);
  programInfoDiv.appendChild(requestInput);
  programInfoDiv.appendChild(pathLabel);
  programInfoDiv.appendChild(pathInput);
  programInfoDiv.appendChild(deleteButton);

  newProgramInfoContainer.appendChild(programInfoDiv);

  programNameInput.value = "";
  buildRequestInput.value = "";
  downloadPathInput.value = "";
}

// Функция для удаления VM
function removeVM2(event) {
const vmContainer = event.target.parentNode;
vmContainer.parentNode.removeChild(vmContainer);
}

function removeStand(event) {
  event.preventDefault();
  const standElement = event.target.parentNode;
  standElement.remove();
}

function removeKit(event) {
  event.preventDefault();
  const kitDiv = event.target.closest('.kit');
  kitDiv.parentNode.removeChild(kitDiv);
}

function removeProgram(event) {
    event.preventDefault();
    var programDiv = event.target.parentNode;
    programDiv.parentNode.removeChild(programDiv);
}
