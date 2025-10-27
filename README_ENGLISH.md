Remote Docker Manager

Remote Docker Manager is a Python application with a Tkinter graphical interface that allows managing remote servers via SSH and executing Docker and system-level commands.

The application is designed for system administrators and DevOps, providing a convenient way to manage servers and containers without direct terminal access.

⚙️ Features
1. Connect to a Remote Server

When the application starts, a window opens to enter the IP address of the remote server.

After clicking OK, it connects via SSH.

If the server is unavailable, a "Server not found" message is displayed, and the IP must be re-entered.

Upon successful connection, the server control panel opens.

2. Server Control Panel

The main window consists of two sections:

Left side — buttons for server and Docker management:

Check Docker — checks if Docker is installed on the server.

Show Running Containers — lists all running Docker containers.

Stop Container — prompts for a container name and stops it.

Install Docker — installs Docker on the server (if not installed).

Start Container — starts a specified container by name.

Pull Container — downloads a specified Docker image.

Reboot Server — reboots the server, prompting for the sudo password; after sending the command, the panel window closes and a new connection is required.

Right side — a command line for executing any commands on the remote server.

Supports commands with sudo; the password is requested once via a Tkinter popup.

Command output is displayed line by line in real-time.

Commands that require input (e.g., cat without a file) are safely handled.

The sudo password is not displayed in the console.

3. Command Handling

All commands run in a separate thread to keep the GUI responsive.

Any stdout and stderr is displayed in the console on the right.

Docker and system commands are securely handled with a pseudo-terminal (get_pty=True) for sudo.

💻 Technologies

Python 3.13+

Tkinter — GUI

Paramiko — SSH connection to remote servers

Docker — manage containers on a remote server

Threading — asynchronous command execution
