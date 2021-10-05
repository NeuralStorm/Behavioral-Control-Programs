
# IMPORTANT NOTES

* The path the repo is placed at should not contain the strings "Touch" or "targ"
or the game will break on windows (any system with backslash as the default path delimeter)

* On systems that allow it (mac, linux) the path the repo is placed at should not contain
backslashes

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

misc dev notes  
https://kivy.org/doc/stable/guide/lang.html
