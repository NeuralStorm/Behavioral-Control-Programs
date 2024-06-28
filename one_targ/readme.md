
# Setup

copy `<project>/example_config.hjson` to `./config.hjson`

using python 3.11  
run `pip install .[hw]`

### Ubuntu 20 notes

To disable multi touch gestures in gnome the following extension can be installed.

https://extensions.gnome.org/extension/1140/disable-gestures/
```sh
gnome-extensions install disable-gestures@mattbell.com.au.v2.shell-extension.zip
gnome-extensions enable disable-gestures@mattbell.com.au
killall -3 gnome-shell
```

# Running

modify `./config.hjson` as needed

in bash
```sh
export nidaq=Dev3
export output_device=plexdo
one-targ
```

Press a to begin the task.

See comments in [example_config.hjson](./example_config.hjson) for descriptions of config parameters.

### Ubuntu 20 notes

If mouse input stops working after touch screen input `killall -3 gnome-shell` can resolve the issue.

# Hotkeys

\` (grave accent) - exit game  
`a` - start game  
`s` - stop game  
`f` - toggle fullscreen  
`c` - toggle calibration square (always 200x200 px)  

# Environment Variables

For environment variables marked [flag] any value that is set and not an empty string will enable the functionality.  
For example (bash)
```bash
export plexon=1
```

---
### `config_path`

use config file at path if no path is specified on the command line
default: `./config.hjson`

---
### `pos`

position the window with a specific location and size  
format {pos_x},{pos_y}<-{width}x{height}

this can be used to make the game effectively full screen

this changes how the game handles fullscreen and is likely required on ubuntu 20/gnome for correct functionality

example  
position at -1920,0
size 1920 by 1086
```sh
export pos='-1920,0<-1920x1086'
```

---
### `output_device`

juicer output device

`plexdo` - use plexon plexdo library  
`bridge` - use bridge  
`none` (default) - no output

---
### `nidaq`

nidaq device to use for event signal outputs. if not set nidaq output will be disabled

example
```sh
export nidaq=Dev3
```

---
### `bridge_enabled` [flag]

enables event output to the bridge server, enabled by default on linux  
if set to "`no`" bridge event output will be disabled

---
### `no_audio` [flag]

disables audio

---
### `photodiode_flash_duration`

photodiode marker flash duration in seconds, set to 0 to disable the photodiode marker flash  
default: 0.018

---
### `output_dir`

directory for output files  
default: `./output`

---
### `px_per_cm`

pixels per cm used to convert cm input values to pixels
default: 20.08

# misc dev notes

https://github.com/NeuralStorm/Behavioral-Control-Programs/tree/61a9baa6d198e3dc13d30326901ea78bd42dc77f/touchscreen_co/Touchscreen/One%20Targ
