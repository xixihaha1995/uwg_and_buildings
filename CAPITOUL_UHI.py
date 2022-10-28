from uwg import UWG
# import configparser, os
# config_file_name = input("Enter the name of the config file: ") or "capitoul_mnp.ini"
#
# config = configparser.ConfigParser()
# project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# config_path = os.path.join(project_path, config_file_name)
# config.read(config_path)

# Define the .epw, .uwg paths to create an uwg object.
# epw_path = "resources/SGP_Singapore.486980_IWEC.epw" # available in resources directory.
epw_path = "resources/Mondouzil_tdb_td_rh_P_2004.epw" # available in resources directory.

# # Initialize the UWG model by passing parameters as arguments, or relying on defaults
# model = UWG.from_param_args(epw_path=epw_path, bldheight=10, blddensity=0.5,
#                             vertohor=0.8, grasscover=0.1, treecover=0.1, zone='1A', nday=30)

# Uncomment these lines to initialize the UWG model using a .uwg parameter file
param_path = "initialize_singapore.uwg"  # available in resources directory.
model = UWG.from_param_file(param_path, epw_path=epw_path)

model.generate()
model.simulate()

# Write the simulation result to a file.
model.write_epw()