
# IMPORTANT NOTES

* The path the repo is placed at should not contain the strings "Touch" or "targ"
or the game will break on windows (any system with backslash as the default path delimeter)

* On systems that allow it (mac, linux) the path the repo is placed at should not contain
backslashes

* the program targets python 3.8

# Setup

copy `./example_config.hjson` to `./config.hjson`

run `pip install -r requirements.txt`

If running with actual hardware  
`pip install nidaqmx==0.5.7`

# Running

modify `./config.hjson` as needed

run `python main.py`  
without hardware `python main.py --test`

# Poetry (alternative to pip/python commands above)

`poetry update`  
`poetry run python main.py -- --test`

# Other Things

### Output file save location (maybe)  
```
on systems with forward slash as the default path delimeter (mac, linux)
    if <working dir>/data/ exists
        files will be saved to `<working dir>/data/`
    else
        files will be saved to `<working dir>/data_tmp_<date>/`

on systems with backslash as the default path delimeter (windows)
    if <repo root>/touchscreen_co/data/ exists
        files will be saved to `<repo root>/touchscreen_co/data/`
    else
        files will be saved to `<repo root>/touchscreen_co/data_tmp_<date>/`
```

saving HDF5 file requires https://www.pytables.org/

## misc dev notes  
https://kivy.org/doc/stable/guide/lang.html

`poetry env use ~/.pyenv/versions/3.8.12/bin/python`
`set -x KIVY_NO_ARGS 1`
