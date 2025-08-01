# AiBot

![Python](https://img.shields.io/badge/Python-3.12-blue.svg?logo=python&logoColor=white&style=flat&labelColor=24292e)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

## Getting Started

### Prerequisites

- Python 3.12
- Discord Bot Token
- API keys for at least one AI provider (Anthropic, Google or OpenAI)

### Installation

#### 1. Clone the repository

```bash
git clone https://github.com/okirimii/aibot.git
cd aibot
```

#### 2. Install dependencies

```bash
# With uv
uv sync

# Without uv
pip install -r requirements.lock
```

#### 3. Prepare the Environment File

Configure the bot using a .env file. Follow these steps:

- Copy .env.sample and rename it to .env
- Edit .env and insert your actual credentials and settings

#### 4. Set Up System Instructions

Rename `resources/instructions-sample.yml` to `resources/instructions.yml`, and add the default system instructions to it.

> [!IMPORTANT]
> If you plan to run the bot in a public Discord server or for multiple users, it’s strongly recommended to review and configure the system instructions appropriately.

#### 5. Run the Bot

```bash
python -m src.aibot --log <log_level>
```

> [!TIP]
> The `--log <log_level>` parameter is optional and allows you to set the log level.
> Available values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL` (case-insensitive).
> If not specified, the default level is `INFO`.


## Slash Commands

<table>
    <tr>
        <th>Command</th>
        <th>Permission</th>
        <th>Description</th>
    </tr>
    <tr>
        <td><code>/chat</code></td>
        <td>All users</td>
        <td>Single-turn chat with AI using current provider and system instruction</td>
    </tr>
    <tr>
        <td><code>/fixme</code></td>
        <td>All users</td>
        <td>Code analysis and bug fixing</td>
    </tr>
    <tr>
        <td><code>/talk</code></td>
        <td>All users</td>
        <td>Create a thread for multi-turn conversation with AI</td>
    </tr>
    <tr>
        <td><code>/provider</code></td>
        <td>All users</td>
        <td>Switch between AI providers (OpenAI, Anthropic, Google)</td>
    </tr>
    <tr>
        <td><code>/create</code></td>
        <td>Beta users</td>
        <td>Create custom system instruction</td>
    </tr>
    <tr>
        <td><code>/list</code></td>
        <td>Beta users</td>
        <td>View available system instructions with preview</td>
    </tr>
    <tr>
        <td><code>/activate</code></td>
        <td>Beta users</td>
        <td>Activate a previous system instruction</td>
    </tr>
    <tr>
        <td><code>/reset</code></td>
        <td>Beta users</td>
        <td>Reset system instruction to default</td>
    </tr>
    <tr>
        <td><code>/lock</code></td>
        <td>Admin only</td>
        <td>Force default system instructions and disable user customization</td>
    </tr>
    <tr>
        <td><code>/unlock</code></td>
        <td>Admin only</td>
        <td>Re-enable user customization of system instructions</td>
    </tr>
    <tr>
        <td><code>/add-pm</code></td>
        <td>Admin only</td>
        <td>Grant beta or blocked permissions to users</td>
    </tr>
    <tr>
        <td><code>/ck-pm</code></td>
        <td>Admin only</td>
        <td>Check user permissions (beta/blocked status)</td>
    </tr>
    <tr>
        <td><code>/rm-pm</code></td>
        <td>Admin only</td>
        <td>Disable beta or blocked permissions from users</td>
    </tr>
</table>
