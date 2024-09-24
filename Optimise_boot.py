import curses
import os
import re
import subprocess

# Decompile DTB to DTS using dtc
def decompile_dtb(dtb_file, output_dts):
    dtc_command = f"dtc -I dtb -O dts -o {output_dts} {dtb_file}"
    subprocess.run(dtc_command, shell=True, check=True)

# Parse DTS for disabled peripherals
def parse_disabled_peripherals(dts_file):
    disabled_peripherals = set()

    with open(dts_file, 'r') as dts:
        lines = dts.readlines()
        for i, line in enumerate(lines):
            if 'status = "disabled"' in line:
                for j in range(i-1, 0, -1):
                    match = re.search(r'(\w+)@[\da-f]+', lines[j])
                    if match:
                        disabled_peripherals.add(match.group(1))
                        break
    return disabled_peripherals

# Parse kernel config for enabled drivers
def parse_enabled_configs(config_file):
    enabled_configs = set()

    with open(config_file, 'r') as config:
        for line in config:
            if re.match(r'CONFIG_\w+=y', line):
                enabled_configs.add(line.strip().split('=')[0])

    return enabled_configs

# Function to disable the config in the .config file
def disable_config_in_file(config_file, config_name):
    with open(config_file, 'r') as f:
        lines = f.readlines()

    with open(config_file, 'w') as f:
        for line in lines:
            if line.startswith(config_name + "=y"):
                f.write(f"# {config_name} is not set\n")
            else:
                f.write(line)

# ncurses-based interactive UI
def interactive_suggestions(stdscr, disabled_peripherals, enabled_configs, config_mapping, config_file):
    curses.curs_set(0)  # Hide cursor

    # Create list of suggestions
    suggestions = []
    suggestion_map = {}
    for peripheral, config in config_mapping.items():
        if peripheral in disabled_peripherals and config in enabled_configs:
            suggestion = f"Peripheral {peripheral} is disabled, but {config} is enabled."
            suggestions.append(suggestion)
            suggestion_map[suggestion] = config

    current_selection = 0
    while True:
        stdscr.clear()

        # Show suggestions in ncurses window
        height, width = stdscr.getmaxyx()
        stdscr.addstr(0, 0, "Optimize Kernel Configurations", curses.A_BOLD | curses.A_UNDERLINE)
        stdscr.addstr(1, 0, "Use arrow keys to navigate, ENTER to select, 'q' to quit.", curses.A_DIM)

        # Display available suggestions
        if not suggestions:
            stdscr.addstr(3, 0, "All optimizations applied. No more suggestions.", curses.A_BOLD)
        else:
            for idx, suggestion in enumerate(suggestions):
                if idx == current_selection:
                    stdscr.addstr(3 + idx, 0, suggestion, curses.A_REVERSE)
                else:
                    stdscr.addstr(3 + idx, 0, suggestion)

        stdscr.refresh()

        # User input handling
        key = stdscr.getch()

        if key == curses.KEY_DOWN:
            current_selection = (current_selection + 1) % len(suggestions)
        elif key == curses.KEY_UP:
            current_selection = (current_selection - 1) % len(suggestions)
        elif key == ord('\n') and suggestions:  # Enter key to select, only if suggestions exist
            selected_suggestion = suggestions[current_selection]
            selected_config = suggestion_map[selected_suggestion]
            confirm_disable(stdscr, selected_config, config_file)

            # Remove the suggestion after disabling the config
            suggestions.remove(selected_suggestion)
            del suggestion_map[selected_suggestion]

            # Adjust current selection to avoid out-of-bound errors
            if current_selection >= len(suggestions):
                current_selection = max(0, len(suggestions) - 1)

        elif key == ord('q'):  # Quit the application
            break

    stdscr.clear()
    stdscr.refresh()

# Prompt the user to confirm disabling a config
def confirm_disable(stdscr, config_name, config_file):
    height, width = stdscr.getmaxyx()
    prompt = f"Do you want to disable {config_name}? (y/n)"
    stdscr.addstr(height//2, (width-len(prompt))//2, prompt)
    stdscr.refresh()

    while True:
        key = stdscr.getch()
        if key == ord('y'):
            # Logic to disable the config in the file
            disable_config_in_file(config_file, config_name)
            stdscr.addstr(height//2 + 2, (width-len(f"Disabled {config_name}."))//2, f"Disabled {config_name}.", curses.A_BOLD)
            stdscr.refresh()
            stdscr.getch()  # Wait for user to press a key before returning
            break
        elif key == ord('n'):
            break

# Main function
def main():
    # Input: Get the .config and .dtb paths from the user
    config_file = os.path.expanduser(input("Enter the path to the .config or defconfig file: ").strip())
    dtb_file = os.path.expanduser(input("Enter the path to the .dtb file: ").strip())

    # Decompile DTB to DTS
    dts_file = "temp_output.dts"
    decompile_dtb(dtb_file, dts_file)

    # Parse disabled peripherals in DTS
    disabled_peripherals = parse_disabled_peripherals(dts_file)

    # Parse enabled drivers in the config
    enabled_configs = parse_enabled_configs(config_file)

    # Peripheral to config mapping
    config_mapping = {
        "spi": "CONFIG_SPI",
        "usb": "CONFIG_USB_SUPPORT",
        "i2c": "CONFIG_I2C",
        "uart": "CONFIG_SERIAL",
        "ethernet": "CONFIG_NET",
        # Add more peripheral to config mappings here
    }

    # Start ncurses interface
    curses.wrapper(interactive_suggestions, disabled_peripherals, enabled_configs, config_mapping, config_file)

    # Clean up temp files
    os.remove(dts_file)

if __name__ == "__main__":
    main()

