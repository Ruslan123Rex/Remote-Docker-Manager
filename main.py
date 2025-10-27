# GUI application that connects to a remote server via SSH and opens a control panel
# The left side contains buttons; the right side is a terminal-like Text widget
# The button logic (SSH commands) is implemented in a separate file actions.py


import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
import threading
import paramiko
import queue
import actions # our separate file with button functions

# Global queue for thread-safe communication to GUI
output_queue = queue.Queue()

class SSHConnection:
    """Simple wrapper for paramiko SSHClient stored on successful connect."""
    def __init__(self):
        self.client = None

    def connect(self, host: str, username: str, password: str, port: int = 22, timeout: int = 5):
        # create a new SSHClient and attempt to connect
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=host, port=port, username=username, password=password, timeout=timeout)
        self.client = client

    def close(self):
        if self.client:
            self.client.close()
            self.client = None


def append_output(text_widget, text: str):
    # insert text into the scrolledtext widget in a thread-safe manner
    text_widget.configure(state='normal')
    text_widget.insert(tk.END, text + "\n")
    text_widget.see(tk.END)
    text_widget.configure(state='disabled')


def output_worker(text_widget):
    # worker that pulls from output_queue and updates the GUI
    while True:
        try:
            line = output_queue.get()
        except Exception:
            break
        if line is None:
            break
        # schedule on main thread
        text_widget.after(0, append_output, text_widget, line)
        output_queue.task_done()


def open_control_panel(root, ssh_conn: SSHConnection):
    # create new Toplevel window with left buttons and right command area
    panel = tk.Toplevel(root)
    panel.title("Remote Docker Manager")
    panel.geometry('900x500')


    # left frame for buttons
    left = tk.Frame(panel, width=250)
    left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)


    # right frame for terminal output and command entry
    right = tk.Frame(panel)
    right.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=10, pady=10)


    # scrolled text for command output
    output_area = scrolledtext.ScrolledText(right, state='disabled')
    output_area.pack(expand=True, fill=tk.BOTH)


    # start output worker thread
    t = threading.Thread(target=output_worker, args=(output_area,), daemon=True)
    t.start()


    # Command entry and run button
    cmd_frame = tk.Frame(right)
    cmd_frame.pack(fill=tk.X, pady=(5, 0))
    cmd_entry = tk.Entry(cmd_frame)
    cmd_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

    #Manual command
    def run_manual_command():
        cmd = cmd_entry.get().strip()
        if not cmd:
            messagebox.showinfo('Info', 'Введите команду для выполнения')
            return

        # Если команда начинается с sudo — запросим пароль в главном потоке
        sudo_pass = None
        if cmd.startswith("sudo"):
            sudo_pass = simpledialog.askstring(
                'Пароль sudo',
                'Введите пароль пользователя для sudo:',
                show='*',
                parent=panel
            )
            if sudo_pass is None:
                output_queue.put("Отмена: пароль не введён")
                return

        # Поток для выполнения команды
        def worker():
            output_queue.put(f"> {cmd}")
            try:
                if sudo_pass:
                    stdin, stdout, stderr = ssh_conn.client.exec_command(cmd, get_pty=True)
                    stdin.write(sudo_pass + "\n")
                    stdin.flush()
                else:
                    stdin, stdout, stderr = ssh_conn.client.exec_command(cmd, get_pty=True)

                # Построчный вывод stdout и stderr, без отображения пароля
                for line in iter(stdout.readline, ""):
                    if sudo_pass and sudo_pass in line:
                        continue  # игнорируем строки с паролем
                    if "[sudo]" in line:
                        continue  # игнорируем запрос sudo
                    output_queue.put(line.rstrip())

                for line in iter(stderr.readline, ""):
                    if sudo_pass and sudo_pass in line:
                        continue
                    if "[sudo]" in line:
                        continue
                    output_queue.put(line.rstrip())

            except Exception as e:
                output_queue.put(f"Ошибка выполнения команды: {e}")

        threading.Thread(target=worker, daemon=True).start()

    # Кнопка запуска команды
    run_btn = tk.Button(cmd_frame, text='Выполнить', command=run_manual_command)
    run_btn.pack(side=tk.RIGHT, padx=(5, 0))






    # Buttons on left that call functions from actions.py
    def btn_check_docker():
        # call actions.check_docker in background
        def worker():
            try:
                res = actions.check_docker(ssh_conn.client)
                output_queue.put(res)
            except Exception as e:
                output_queue.put(f"Ошибка: {e}")
        threading.Thread(target=worker, daemon=True).start()

    #List Docker conteiner
    def btn_list_containers():
        def worker():
            try:
                res = actions.list_containers(ssh_conn.client)
                output_queue.put(res)
            except Exception as e:
                output_queue.put(f"Ошибка: {e}")
        threading.Thread(target=worker, daemon=True).start()
 
    #Stop Docker conteiner
    def btn_stop_container():
        # ask which container to stop
        cid = simpledialog.askstring('Остановить контейнер', 'Введите ID или имя контейнера для остановки', parent=panel)
        if not cid:
            return
        def worker():
            try:
                out = actions.stop_container(ssh_conn.client, cid)
                output_queue.put(out)
            except Exception as e:
                output_queue.put(f"Ошибка: {e}")
        threading.Thread(target=worker, daemon=True).start()
    
    
    #Install Docker
    def btn_install_docker():
        def worker():
            try:
                res = actions.install_docker(ssh_conn.client)
                output_queue.put(res)
            except Exception as e:
                output_queue.put(f"Ошибка: {e}")
        threading.Thread(target=worker, daemon=True).start()
    
    
    #Run Docker conteiner
    def btn_run_container():
        # спрашиваем имя образа
        image = simpledialog.askstring('Запуск контейнера', 'Введите имя Docker-образа (например: nginx, ubuntu, mysql:latest)', parent=panel)
        if not image:
            return
        def worker():
            try:
                res = actions.run_container(ssh_conn.client, image)
                output_queue.put(res)
            except Exception as e:
                output_queue.put(f"Ошибка: {e}")
        threading.Thread(target=worker, daemon=True).start()


    #Install Docker conteiner
    def btn_install_container():
        image = simpledialog.askstring('Установить контейнер', 'Введите имя Docker-образа (например: nginx, mysql:latest)', parent=panel)
        if not image:
            return
        def worker():
            try:
                res = actions.install_container(ssh_conn.client, image)
                output_queue.put(res)
            except Exception as e:
                output_queue.put(f"Ошибка: {e}")
        threading.Thread(target=worker, daemon=True).start()
    
    #Reboot server
    def btn_reboot_server():
        if not messagebox.askyesno('Перезагрузка сервера', 'Вы действительно хотите перезагрузить сервер?'):
            return
        sudo_pass = simpledialog.askstring('Пароль sudo', 'Введите пароль пользователя для sudo:', show='*', parent=panel)
        def worker():
            try:
                res = actions.reboot_server(ssh_conn.client, sudo_pass)
                output_queue.put(res)
                
                    # Если команда успешно отправлена, закрываем панель управления и возвращаемся к окну подключения
                if "The system will reboot now!" in res.lower():
                    messagebox.showinfo("Перезагрузка", "Сервер перезагружается. Окно панели управления будет закрыто.")
                    panel.destroy()  # закрываем текущее окно управления
                    open_connection_window()  # открываем окно подключения заново
                
            except Exception as e:
                output_queue.put(f"Ошибка: {e}")
            finally:
                panel.destroy()
                
        threading.Thread(target=worker, daemon=True).start()
        
    
    # create buttons
    b1 = tk.Button(left, text='Проверить Docker', width=30, command=btn_check_docker)
    b1.pack(pady=10)
    b2 = tk.Button(left, text='Установить Docker', width=30, command=btn_install_docker)
    b2.pack(pady=10)
    b3 = tk.Button(left, text='Показать запущенные контейнеры', width=30, command=btn_list_containers)
    b3.pack(pady=10)
    b4 = tk.Button(left, text='Остановить контейнер', width=30, command=btn_stop_container)
    b4.pack(pady=10)
    b5 = tk.Button(left, text='Запустить контейнер', width=30, command=btn_run_container)
    b5.pack(pady=10)
    b6 = tk.Button(left, text='Установить контейнер', width=30, command=btn_install_container)
    b6.pack(pady=10)
    b7 = tk.Button(left, text='Перезагрузка сервер', width=30, bg='red', fg='white', command=btn_reboot_server)
    b7.pack(pady=10)
    
    
    # Close handler to stop threads gracefully (put None into queue)
    def on_close():
        output_queue.put(None)
        ssh_conn.close()
        panel.destroy()


    panel.protocol('WM_DELETE_WINDOW', on_close)


def show_connect_window():
    # main connect window where user enters IP, username and password
    root = tk.Tk()
    root.title('Connect to Remote Server')
    root.geometry('350x280')


    tk.Label(root, text='IP адрес:').pack(pady=(10, 0))
    ip_entry = tk.Entry(root)
    ip_entry.pack(fill=tk.X, padx=20)


    tk.Label(root, text='Порт (по умолчанию 22):').pack(pady=(5, 0))
    port_entry = tk.Entry(root)
    port_entry.insert(0, '22')
    port_entry.pack(fill=tk.X, padx=20)


    tk.Label(root, text='Имя пользователя:').pack(pady=(5, 0))
    user_entry = tk.Entry(root)
    user_entry.pack(fill=tk.X, padx=20)


    tk.Label(root, text='Пароль:').pack(pady=(5, 0))
    pass_entry = tk.Entry(root, show='*')
    pass_entry.pack(fill=tk.X, padx=20)


    ssh_conn = SSHConnection()


    def try_connect():
        host = ip_entry.get().strip()
        port = int(port_entry.get().strip() or '22')
        username = user_entry.get().strip()
        password = pass_entry.get()
        if not host:
            messagebox.showerror('Ошибка', 'IP адрес не указан')
            return


        # try connect in background to avoid freezing
        def worker():
            try:
                ssh_conn.connect(host, username, password, port=port)
            except Exception as e:
                # if error, show messagebox on main thread
                root.after(0, lambda err=e: messagebox.showerror('Ошибка', f'Сервер не найден или ошибка подключения:\n{err}'))
                return
            # on success, open control panel
            root.after(0, lambda: open_control_panel(root, ssh_conn))
        
        threading.Thread(target=worker, daemon=True).start()


    connect_btn = tk.Button(root, text='Ок', command=try_connect)
    connect_btn.pack(pady=10)


    root.mainloop()


if __name__ == '__main__':
    show_connect_window()