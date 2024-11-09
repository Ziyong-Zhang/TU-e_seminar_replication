from numpy.random import rand
from numpy import nan
import pandas as pd

process_log = pd.read_csv('./box_process_data/event_data_generated_4.csv')


# Do not delete values of the box 
random_noise = rand(*process_log.shape)
random_noise[:,5] = 1 
# 1% 
noise_1 = process_log.mask(cond=random_noise<0.01, other=nan)
# 2% 
noise_2 = process_log.mask(cond=random_noise<0.02, other=nan)
# 5% 
noise_3 = process_log.mask(cond=random_noise<0.05, other=nan)
# 10% 
noise_4 = process_log.mask(cond=random_noise<0.1, other=nan)

noise_1.to_csv('./box_process_data/event_data_noise_1.csv', header=True, index=False)
noise_2.to_csv('./box_process_data/event_data_noise_2.csv', header=True, index=False)
noise_3.to_csv('./box_process_data/event_data_noise_3.csv', header=True, index=False)
noise_4.to_csv('./box_process_data/event_data_noise_4.csv', header=True, index=False)
