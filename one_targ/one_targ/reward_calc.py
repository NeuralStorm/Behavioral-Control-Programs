
import numpy as np

def get_reward_gen(*, perc_trials_2x, perc_trials_rew, reward_for_grasp):
    mini_block = int(2*(np.round(1./perc_trials_rew)))
    trial_cnt_bonus = 0
    
    while True:
        mini_block_array = np.zeros((mini_block))
        ix = np.random.permutation(mini_block)
        mini_block_array[ix[:2]] = reward_for_grasp[1]
        
        trial_cnt_bonus += mini_block
        if perc_trials_2x > 0:
            if trial_cnt_bonus > int(1./(perc_trials_rew*perc_trials_2x)):
                mini_block_array[ix[0]] = reward_for_grasp[1]*2.
                trial_cnt_bonus = 0
        
        for x in mini_block_array:
            yield x
