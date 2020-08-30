import numpy as np
a = [1]*100
#a.extend([2]*100)
a.extend([3]*100)
#a.extend([4]*100)
np.random.shuffle(a)
b = np.arange(200)
c = ([b],[a])
d = np.transpose(a)
e = np.arange(1,201)
def countrange(start, stop):
    return np.arange(start,stop+1)




