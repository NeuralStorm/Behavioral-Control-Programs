
# Config


### reward_thresholds

`reward duration, low threshold, high threshold, ...`

example: `0.15,0.3,0.4,0.15,1,1.25`

the first reward duration where `low < pull duration < high` is used

### images

- optional

examples:
```
dBlank.png
bOval.png,bRectangle.png,bStare.png
```

The files `aBlank.png`, `xBlack.png`, `yPrepare.png` and `zMonkey2.png` are expected to exist in the graphics dir. No files alphabetically before `aBlank.png` or after `xBlack.png` should be placed in the graphics dir.

each image's boxed variant is expected to have the same name with `b` replace with `c` and `d` replaced with `e`

##### if not set

a list of images is created from the files in the graphics dir in alphabetical order

influenced by the `Number of Events` (`n`) and `num_task_images` (`nt`) (default 3) config values, indexes are 0 indexed, ranges are inclusive

images without boxes will be image `1` through `n` and boxed images will be image `nt+1` through `nt+n`

### Number of Events

If set to 0 sets the program to perform the home zone exit task. If 0 it will be treated as 1 for image selection.

See `images` for information on how it impacts selection of images.
