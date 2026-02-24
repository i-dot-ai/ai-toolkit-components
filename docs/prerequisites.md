# Prerequisites

## For users

If you just want to run existing applications or components, you only need Docker.

### macOS and Windows

Install **[Docker Desktop](https://docs.docker.com/desktop/)**, which bundles the Docker Engine, Docker Compose, and a GUI in a single package.

- [Install Docker Desktop on Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
- [Install Docker Desktop on Windows](https://docs.docker.com/desktop/setup/install/windows-install/)

### Linux

On Linux, Docker Desktop is optional. The recommended approach is to install the **Docker Engine** and the **Docker Compose plugin** separately:

- [Install Docker Engine on Linux](https://docs.docker.com/engine/install/)
- [Install the Docker Compose plugin](https://docs.docker.com/compose/install/linux/)

### Verify your Docker installation

Once installed, confirm both tools are available by opening a terminal and running the following.

> **New to terminals?** A terminal lets you type commands directly to your computer.
> - **macOS** — open **Terminal** (search for it in Spotlight with `Cmd + Space`)
> - **Windows** — open **PowerShell** (press `Win + X` and choose *Terminal* or *PowerShell*)
> - **Linux** — open your distro's terminal emulator (often `Ctrl + Alt + T`)

```bash
docker --version
docker compose version
```

---

## For developers

If you want to build new components, run tests, or contribute to the repository, you need everything above plus Python and `uv`.

### Python

Python 3.12 or later is required.

- [Download Python](https://www.python.org/downloads/)

Verify your installation:

```bash
python --version
```

### uv

`uv` is the package manager used by this project.

**macOS** — via Homebrew:

```bash
brew install uv
```

**Windows** — via WinGet:

```bash
winget install --id=astral-sh.uv -e
```

Or via Scoop:

```bash
scoop install main/uv
```

**Linux** — via pip:

```bash
pip install uv
```

See the [uv installation docs](https://docs.astral.sh/uv/getting-started/installation/) for further options.

### Install project dependencies

Once `uv` is installed, run the following from the root of the repository to install all dependencies:

```bash
uv sync
```

Verify your installation:

```bash
uv --version
```
