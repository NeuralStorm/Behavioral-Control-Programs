
# Setup

copy `<project>/example_config.hjson` to `./config.hjson`

using python 3.11  
run `pip install .[hw]`

# Running

modify `./config.hjson` as needed

in bash
```sh
export nidaq=Dev3
export plexon=1
one-targ
```

Press a to begin the task.

See comments in [example_config.hjson](./example_config.hjson) for descriptions of config parameters.

# Hotkeys

`~` - exit game  
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

example  
position at -1920,0
size 1920 by 1086
```sh
export pos='-1920,0<-1920x1086'
```

---
### `plexon` [flag]

enable plexdo output to trigger the juice reward

---
### `nidaq`

nidaq device to use for event signal outputs. if not set nidaq output will be disabled

example
```sh
export nidaq=Dev3
```

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
