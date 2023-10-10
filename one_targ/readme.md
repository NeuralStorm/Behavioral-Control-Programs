
# Setup

copy `./example_config.hjson` to `./config.hjson`

using python 3.11  
run `pip install .[hw]`

# Running

modify `./config.hjson` as needed

in bash
```sh
export nidaq=1
export plexon=1
one-targ
```

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
