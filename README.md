# Winsomnia-ssh and Winsomnia

`winsomnia-ssh` prevents Windows from going to sleep while your ssh session is active in WSL.
It also provides a simple CLI, `winsomnia`, which allows you to pause sleep whenever you want, for however long you want.

> **Fork notice:** this is a maintained fork of [`nullpo-head/winsomnia-ssh`](https://github.com/nullpo-head/winsomnia-ssh).
> Upstream's `daemonize()` was broken on Python 3 (used the invalid `"rw"` open mode and never reached `os.dup2` for fd-level redirects, so any post-detach log write would crash with a `ValueError`). This fork rewrites the daemonization with a proper double-fork + `setsid` + `dup2`, fixes a check-prerequisites typo that silently masked a missing `winsomnia` binary, actively rejects the Microsoft Store Python stub at runtime, and ports the project from Poetry to uv with ruff + ty.

## Installation

Requires Python 3.14+ in WSL and Python for Windows (official installer — see below).

With [`uv`](https://docs.astral.sh/uv/) (recommended):

```sh
uv tool install "git+https://github.com/mattwilkinsonn/winsomnia-ssh"
```

Or with pip:

```sh
pip install "git+https://github.com/mattwilkinsonn/winsomnia-ssh"
```

`winsomnia-ssh` requires `python` both in WSL and Windows. Install Python for Windows via [the official installer](https://www.python.org/downloads/). **Do not** install Python via the Microsoft Store — the Store stub cannot be launched from WSL, and `winsomnia-ssh` will refuse to run if it detects this stub on PATH.

If you install `winsomnia-ssh` in native Windows, `winsomnia` should work without problem.
`winsomnia-ssh` may be able to work, but it's not tested or supported.

## Usage

### Prevent sleep while your ssh session in WSL is active

Add the following line to your `~/.bashrc` or an equivalent file of your environment in WSL.

```sh
winsomnia-ssh
```

As long as the shell session in WSL that launched `winsomnia-ssh` is active, it will prevent Windows from going to sleep.
It does nothing (and prints nothing) when your session is not in an ssh session, so it's safe to leave in `.bashrc` unconditionally. Pass `-v` if you want verbose logging while debugging.

Please note that the detection of ssh sessions assumes that your `sshd` is `sshd` of Linux (WSL).
For your reference, here is an example tutorial of how to set up an ssh server in WSL. [How to SSH into WSL2 on Windows 10 from an external machine - Scott Hanselman's Blog](https://www.hanselman.com/blog/how-to-ssh-into-wsl2-on-windows-10-from-an-external-machine).
Scott's article recommends that `DO NOT DO THE INSTRUCTIONS IN THIS POST` because it is simpler to use the native OpenSSH service of Windows. However, `winsomnia-ssh` depends on Linux `sshd`, so please follow the instruction. Personally, I recommend you to set up a ssh server and port forwardings in WSL2 instead of Windows, because it is more flexible when you want to have more Linux services in the future.

### Manually prevent sleep for a while by CLI

`winsomnia-ssh` provides a handy CLI tool, `winsomnia`.
`winsomnia` allows you to prevent sleep whenever you want, regardless of whether you are in an ssh session or not.

```sh
winsomnia [duration_in_minutes]
```

You can quit `winsomnia` to resume Windows Sleep.

```console
$ winsomnia
Trying to run via python.exe
Kill this program by Ctrl+C to let Windows sleep
^C
```

See `winsomnia --help` for the detailed usage.

## Development

```sh
uv sync
uv run pytest
uv run ruff check .
uv run ty check
```
