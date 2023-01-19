
source "$HOME/Documents/tilt_hardware_control/setup_data_collection.sh"

tilt --config config.hjson --labels labels.hjson --monitor --live --live-secs 30 --loadcell-out "tilt_output/notilt_$(dt).csv"

post
