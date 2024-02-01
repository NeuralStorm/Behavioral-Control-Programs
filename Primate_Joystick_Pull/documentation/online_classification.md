
# Template generation

Example
```sh
js-gen-template --events output/test.json.gz --event-class tpullstart --template-out output/test_template.json --labels output/labels.json --post-time 200 --bin-size 5
```

Example labels file: https://github.com/NeuralStorm/Behavioral-Control-Programs/blob/75f3f6e869c1c8869a93ab25f6270787049ab98c/tilt_hardware_control/tilt_hardware_control/example_labels.hjson

The labels file has one parameter `channels`. The parameters of the dict are plexon channels and the values are plexon units within that channel. The labels file is the same format as those used for the tilt task.

Supported event classes
```
tpullstart
tgocue
tdiscrim
```

### Example

```sh
evt=output/TIP001_grp_cndtn_001_20231222_145029Joystick.json.gz
out=output/TIP001_grp_cndtn_001_20231222_145029Joystick_templates.json

cls=joystick_pull
post_time=200
bin_size=5

js-gen-template --events $evt --event-class $cls --template-out $out \
--post-time $post_time --bin-size $bin_size --labels labels.json
```
