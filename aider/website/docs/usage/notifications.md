---
title: Notifications
highlight_image: /assets/notifications.jpg
parent: Usage
nav_order: 760
description: Aider can notify you when it's waiting for your input.
---

# Notifications

Aider can notify you when it's done working and is
waiting for your input. 
This is especially useful for long-running operations or when you're multitasking.

## Usage

Enable notifications with the `--notifications` flag:

```bash
aider --notifications
```

When enabled, aider will notify you when the LLM has finished generating a response and is waiting for your input.

## OS-Specific Notifications

Aider automatically detects your operating system and uses an appropriate notification method:

- **macOS**: Uses `terminal-notifier` if available, falling back to AppleScript notifications
- **Linux**: Uses `notify-send` or `zenity` if available
- **Windows**: Uses PowerShell to display a message box

## Custom Notification Commands

You can specify a custom notification command with `--notifications-command`:

```bash
aider --notifications-command "your-custom-command"
```

For example, on macOS you might use:

```bash
aider --notifications-command "say 'Aider is ready'"
```

### Remote Notifications

For remote notifications you could use [Apprise](https://github.com/caronc/apprise),
which is a cross-platform Python library for sending notifications to various services.

We can use Apprise to send notifications to Slack

```bash
aider --notifications-command "apprise -b 'Aider is ready' 'slack://your-slack-webhook-token'"
```

or Discord
```bash
aider --notifications-command "apprise -b 'Aider is ready' 'discord://your-discord-webhook-token'"
```

or even to your phone via Pushbullet
```bash
aider --notifications-command "apprise -b 'Aider is ready' 'pbul://your-pushbullet-access-token'"
```

Check more how to use and configure Apprise on their GitHub page.

## Configuration

You can add these settings to your configuration file:

```yaml
# Enable notifications
notifications: true

# Optional custom notification command
notifications_command: "your-custom-command"
```

Or in your `.env` file:

```
AIDER_NOTIFICATIONS=true
AIDER_NOTIFICATIONS_COMMAND=your-custom-command
```
