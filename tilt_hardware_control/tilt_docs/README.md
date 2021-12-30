# Hardware Documentation


## Platform Details

![Platform Blueprint](https://github.com/NeuralStorm/Behavioral-Control-Programs/raw/kev-readme/tilt_hardware_control/tilt_docs/platform_drawing_top.png)

The platform consists of three individual plates, covered by a plexiglass layer, which are fixed on top of a number of sensors that rely on [strain gauge](https://en.wikipedia.org/wiki/Strain_gauge) readings to measure the force and torque along the X, Y, and Z axes for each individual sensor. The platforms are arranged in such a way that two limbs on one side (in the context of the Moxon Neurorobotics Laboratory, generally the hindlimbs) may be recorded individually while the two limbs on the other side (generally the forelimbs) are recorded using a single sensor.

## Center of Pressure Calculation

The center of pressure is calculated using a set of equations established in [this paper](https://github.com/NeuralStorm/Behavioral-Control-Programs/blob/kev-readme/tilt_hardware_control/tilt_docs/cop-paper.pdf).

The `x` and `y` coordinates (for each foot placement) are based on the center of each respective sensor, and are offset based on both the location of the sensors relative to each other, and to account for the thickness of the plexiglass layer (using the `z` value).:

![X and Y Formulas](https://imgur.com/OzYHFp4.png)

Where `F` represents the translation **force** components along their respective axes, and the `T` represents the **torque** component about their respect axes. These individual foot placements and the [Ground Reaction Forces](https://en.wikipedia.org/wiki/Ground_reaction_force)[^grfnote] are then combined to obtain the center of pressure of the entire subject:

![CoP Formulas](https://imgur.com/7oFQUpp.png)


## Processing Pipeline

Any data recorded using this set-up is generally fed into [GRF Python](https://github.com/NeuralStorm/Behavior-Analysis-Programs/tree/master/grf_python) (assuming it was recorded the Moxon Neurorobotics tilt task control software), which converts the strain gauge data collected into [Ground Reaction Force](https://en.wikipedia.org/wiki/Ground_reaction_force) data. Related neural data (`.plx`/`.pl2`) is generally fed into the [Matlab Offline Neural Analysis (MONA)](https://github.com/NeuralStorm/MATLAB-offline-neural-analysis) program, which can parse this data and generate relative response matrices, as well as create Peri-Stimulus Time Histograms and run various different kinds of analyses.

[^grfnote]: It is crucial that all users understand that the Ground Reaction Forces are **not** the raw values obtained using the tilt recording software. The Ground Reaction Forces are calculated from the raw strain gauge data the tilt task recording software saves to a `.csv` file.