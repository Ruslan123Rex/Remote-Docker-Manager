import paramiko
import time




def run_command(ssh_client: paramiko.SSHClient, command: str, timeout: int = 30):
    """Run a command via SSH and return (stdout, stderr) as strings."""
    if ssh_client is None:
        raise ValueError('Нет SSH подключения')
    stdin, stdout, stderr = ssh_client.exec_command(command, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    return out, err

def check_docker(ssh_client: paramiko.SSHClient) -> str:
    """Check if Docker is installed by running 'docker --version'."""
    try:
        out, err = run_command(ssh_client, 'docker --version')
        if out:
            return f'Docker установлен: {out.strip()}'
        # sometimes docker is available via sudo
        out, err = run_command(ssh_client, 'sudo docker --version')
        if out:
            return f'Docker установлен (требуется sudo): {out.strip()}'
        # if neither returned output, consider docker not installed
        return 'Docker не найден на удалённом сервере.'
    except Exception as e:
        return f'Ошибка при проверке Docker: {e}'

def list_containers(ssh_client: paramiko.SSHClient) -> str:
    """Return a human-friendly list of running docker containers."""
    try:
        out, err = run_command(ssh_client, 'docker ps --format "{{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Status}}"')
        if out.strip():
            lines = out.strip().splitlines()
            # build readable output
            result = ['Запущенные контейнеры:']
            for line in lines:
                parts = line.split('\t')
                result.append(f'ID: {parts[0]} | Image: {parts[1]} | Name: {parts[2]} | Status: {parts[3]}')
                return '\n'.join(result)
        else:
            return 'Нет запущенных контейнеров.'
    except Exception as e:
        return f'Ошибка при получении списка контейнеров: {e}'




def stop_container(ssh_client: paramiko.SSHClient, container_id_or_name: str) -> str:
    """Stop container by ID or name and return command output."""
    try:
        # try stopping directly
        out, err = run_command(ssh_client, f'docker stop {container_id_or_name}')
        if out.strip():
            return f'Остановлено: {out.strip()}'
        if err.strip():
            # sometimes error message arrives in stderr but useful
            return f'Сообщение: {err.strip()}'
        return 'Команда выполнена (нет вывода).'
    except Exception as e:
        # try with sudo if direct stop failed
        try:
            out, err = run_command(ssh_client, f'sudo docker stop {container_id_or_name}')
            if out.strip():
                return f'Остановлено с sudo: {out.strip()}'
            if err.strip():
                return f'Сообщение (sudo): {err.strip()}'
            return 'Команда с sudo выполнена (нет вывода).'
        except Exception as e2:
            return f'Ошибка при остановке контейнера: {e2}'
        
def install_docker(ssh_client):
    """Устанавливает Docker в зависимости от дистрибутива (Ubuntu/Debian/CentOS)."""
    try:
        # Определяем ОС
        out, err = run_command(ssh_client, "cat /etc/os-release")
        if "Ubuntu" in out or "Debian" in out:
            cmds = [
                "sudo apt-get update -y",
                "sudo apt-get install -y ca-certificates curl gnupg lsb-release",
                "sudo mkdir -p /etc/apt/keyrings",
                "curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo $ID)/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
                "echo \\\"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo $ID) $(lsb_release -cs) stable\\\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null",
                "sudo apt-get update -y",
                "sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
                "sudo systemctl enable docker",
                "sudo systemctl start docker",
            ]
        elif "CentOS" in out or "Red Hat" in out:
            cmds = [
                "sudo yum install -y yum-utils",
                "sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo",
                "sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin",
                "sudo systemctl enable docker",
                "sudo systemctl start docker",
            ]
        else:
            return "Неподдерживаемая ОС. Установка Docker невозможна."

        # Выполняем все команды по очереди
        output = []
        for cmd in cmds:
            output.append(f"> {cmd}")
            out, err = run_command(ssh_client, cmd)
            if out.strip():
                output.append(out.strip())
            if err.strip():
                output.append(err.strip())
        return "\\n".join(output) + "\\n✅ Docker успешно установлен!"
    except Exception as e:
        return f"Ошибка при установке Docker: {e}"


def run_container(ssh_client, image_name):
    """Запускает Docker-контейнер по имени образа."""
    try:
        if not image_name.strip():
            return "Ошибка: имя образа не указано."

        cmd = f"sudo docker run -d {image_name}"
        out, err = run_command(ssh_client, cmd)
        if out.strip():
            return f"✅ Контейнер запущен:\n{out.strip()}"
        elif err.strip():
            return f"Сообщение:\n{err.strip()}"
        else:
            return "Команда выполнена (нет вывода)."
    except Exception as e:
        return f"Ошибка при запуске контейнера: {e}"


def install_container(ssh_client, image_name):
    """Загружает (pull) Docker-образ по имени."""
    try:
        if not image_name.strip():
            return "Ошибка: имя образа не указано."

        cmd = f"sudo docker pull {image_name}"
        out, err = run_command(ssh_client, cmd)
        result = []
        if out.strip():
            result.append(out.strip())
        if err.strip():
            result.append(err.strip())
        if not result:
            result.append("Команда выполнена (нет вывода).")
        return "\\n".join(result) + "\\n✅ Образ успешно установлен!"
    except Exception as e:
        return f"Ошибка при установке контейнера: {e}"
    

def reboot_server(ssh_client, sudo_password=None):
    """Перезагружает сервер с передачей пароля sudo через stdin (без отображения пароля)."""
    try:
        command = "sudo -S reboot"
        stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=True)

        if sudo_password:
            # Передаём пароль, но не выводим его в консоль
            stdin.write(sudo_password + "\n")
            stdin.flush()

        out = stdout.read().decode(errors="ignore")
        err = stderr.read().decode(errors="ignore")

        # Удаляем из вывода строки, где отображается sudo prompt или пароль
        filtered_output = []
        for line in (out + "\n" + err).splitlines():
            if "[sudo]" in line or sudo_password in line:
                continue
            filtered_output.append(line.strip())

        if not filtered_output:
            filtered_output.append("Команда выполнена (нет вывода).")

        return "\n".join(filtered_output).strip() + "\n🔄 Сервер перезагружается!"
    except Exception as e:
        return f"Ошибка при перезагрузке сервера: {e}"


