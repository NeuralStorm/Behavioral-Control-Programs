
# Setup

copy `./example_config.hjson` to `./config.hjson`

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

# Environment Variables

For environment variables marked [flag] any value that is set and not an empty string will enable the functionality.  
For example (bash)
```bash
export plexon=1
```

---
### `config_path`

use config file at path if no path is specified on the command line

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
### `skip_start` [flag]

automatically dismiss the start screen

# Other Things

### Output file save location  
Some previous versions of "one_targ_new" replicated the save location from "One Targ" assuming the working directory was in the same folder as the script, not the full original logic.  
The current logic does not split the path on backslashes on platforms besides windows, the original logic split the path on backslashes regardless of platform.  
```
on non windows (mac, linux)
    if ./data/ exists
        files will be saved to `<working dir>/data/`
    else
        files will be saved to `<working dir>/data_tmp_<date>/`

on windows
    where <p> is the working directory with any segments containing "Touch" or "Targ" removed
    if <p>/data/ exists
        files will be saved to `<p>/data/`
    else
        files will be saved to `<p>/data_tmp_<date>/`
```

## misc dev notes  
https://kivy.org/doc/stable/guide/lang.html

`poetry env use ~/.pyenv/versions/3.8.12/bin/python`
`set -x KIVY_NO_ARGS 1`
