import numpy as np
tic = 0
samples = 1000

ticsamps = np.linspace(tic,(tic+1),samples,retstep = True)
print(len(ticsamps))

print(ticsamps)

for i in range(samples):
    ticsamps[i] = round(ticsamps[i],3)

print(ticsamps)
