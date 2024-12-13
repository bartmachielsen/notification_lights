# Notification Lights

A Home Assistant custom integration that uses your smart lights to display visual notifications. With **Notification Lights**, you can define groups of lights and trigger notifications with specific colors and patterns. Once the notification sequence completes, your lights return to their previous states—ensuring that notifications don’t permanently alter your preferred lighting settings.

## Features

- **UI-based Configuration:**  
  Add and configure the integration directly from the Home Assistant UI. No YAML required.
  
- **Notification Groups:**  
  Create and manage groups of lights that will act as a unit when a notification is triggered.
  
- **Colors and Patterns:**  
  Set notifications to use a specified color (if supported by the light) and define blink patterns, durations, and repetition counts.

- **State Restoration:**  
  After the notification ends, the lights return to their original state, preserving brightness, color, and on/off status.

## Installation

1. **HACS (Recommended):**  
   If you use [HACS](https://hacs.xyz/):
   - Go to **HACS → Integrations**.
   - Click the three dots in the top-right corner and choose **Custom repositories**.
   - Add your repository URL and select **Integration** as the category.
   - Once added, find **Notification Lights** in HACS and click **Install**.

2. **Manual Installation:**
   - Download the contents of this repository.
   - Create a `notification_lights` folder in your Home Assistant `custom_components` directory:
     ```
     <config_directory>/custom_components/notification_lights/
     ```
   - Copy all files from the repository’s `custom_components/notification_lights/` folder into the newly created directory.
   - Restart Home Assistant.

## Setup & Configuration

1. **Add the Integration:**
   - Go to **Settings → Devices & Services → Add Integration** in Home Assistant.
   - Search for **Notification Lights**.
   - Click **Configure** to finalize the setup.

2. **Manage Groups:**
   - After adding the integration, select **Configure** on the integration card.
   - Use the Options flow to:
     - Add new notification groups (by giving them a name and adding one or more light entities).
     - Edit or remove existing groups as desired.

3. **Trigger Notifications:**
   Use the `notification_lights.trigger_notification` service to trigger a notification. For example:
   ```yaml
   service: notification_lights.trigger_notification
   data:
     group_name: "alarm_alert"
     color: "#FF0000"
     pattern:
       on: 1.0
       off: 1.0
       repeat: 3
     restore: true
   ```
   This will blink the lights in the `alarm_alert` group in red, three times, then restore their previous states.

## Service Parameters

- `group_name`: **(required)** The name of the notification group to notify.
- `color`: A color in `#RRGGBB` format or another supported color format. If not supported by the lights, they will simply turn on/off.
- `pattern`: A dictionary defining the blink pattern. For example:
  ```yaml
  pattern:
    on: 1.0
    off: 1.0
    repeat: 3
  ```
  If no pattern is given, the lights will turn on with the given color for the `duration` and then restore.
- `duration`: The number of seconds to keep the lights on if no pattern is defined.
- `restore`: Boolean (`true`/`false`). If `true`, the previous states are restored after the notification finishes.

## Example Automations

**Triggering a Notification When a Door Opens:**
```yaml
alias: Door Open Alert
trigger:
  - platform: state
    entity_id: binary_sensor.front_door
    to: "on"
action:
  - service: notification_lights.trigger_notification
    data:
      group_name: "door_alert"
      color: "#FFA500"
      pattern:
        on: 0.5
        off: 0.5
        repeat: 5
      restore: true
```

## Troubleshooting

- **No Groups Available:**  
  Make sure you’ve created a group in the integration’s Options flow.
  
- **No Color Changes:**  
  Check if your lights support color changes. If they don’t, the notification will only turn them on and off.

- **Not Restoring State:**  
  Ensure `restore` is set to `true` in your service call.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

## License

[MIT License](LICENSE)
