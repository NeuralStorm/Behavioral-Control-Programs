# test winsound stuff

# Might need to remake sounds and change decibals 
# Ask Ryan if he has a way to check Db on his files that he made
import winsound
import time
import random
import statistics

DiscrimStimMin = 30

DiscrimStimMax = 120
test = []
for i in range(0,1000):
    DiscrimStimDuration = round((random.randint(DiscrimStimMin,DiscrimStimMax)/60),2)
    #print(DiscrimStimDuration)
    test.append(DiscrimStimDuration)

test_avg = sum(test) / len(test)
test_min = min(test)
test_max = max(test)
test_stdev = statistics.stdev(test)
print('Stats:')
print('AVG: ', test_avg)
print('STDEV: ', test_stdev)
print('MIN: ', test_min)
print('MAX: ', test_max)



# input('start?')

# print('wrongholddur') # Quiet
# winsound.PlaySound('WrongHoldDuration.wav', winsound.SND_ASYNC)
# time.sleep(2)

# print('750Hz 1s')
# winsound.PlaySound('750Hz_1s_test.wav', winsound.SND_ASYNC)
# time.sleep(2)

# print('550Hz 1s')
# winsound.PlaySound('550Hz_1s_test.wav', winsound.SND_ASYNC)
# time.sleep(2)

# print('550Hz 0.5s') # Very Quiet / Can't hear at all???
# winsound.PlaySound('550Hz_0.5s_test.wav', winsound.SND_ASYNC)
# time.sleep(2)

# print('outofhomezone') # Very Quiet

# winsound.PlaySound('OutOfHomeZone.wav', winsound.SND_ASYNC + winsound.SND_LOOP)
# tic = time.time()
# time.sleep(1.67)
# toc1 = time.time() - tic
# winsound.PlaySound(None, winsound.SND_FILENAME) #Purge looping sounds
# toc2 = time.time() - tic
# print(toc1)
# print(toc2)

