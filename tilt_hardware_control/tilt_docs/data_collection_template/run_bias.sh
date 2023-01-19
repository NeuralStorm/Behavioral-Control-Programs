
source "$HOME/Documents/tilt_hardware_control/setup_data_collection.sh"

tilt --config config.hjson --labels labels.hjson --bias "tilt_output/bias_$(dt).csv"

post
