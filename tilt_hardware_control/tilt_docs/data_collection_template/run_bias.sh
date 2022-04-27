
source '/c/Users/moxon/Documents/tilt_hardware_control/setup_data_collection.sh'

tilt --config config.hjson --bias "bias_$(dt).csv"

post
