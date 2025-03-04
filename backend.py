import matplotlib.pyplot as plt
import random
import numpy as np

plt.ion()  # turning interactive mode on

# preparing the data
size = 10
i = 0
y = np.zeros(size)
x = np.linspace(0, 2, size)

def get_sensor_data(i):
    return np.sin(2 * np.pi * (0.1 * i))

def shift(x_s, n, value):
    e = np.empty_like(x_s)
    if n >= 0:
        e[:n] = value
        e[n:] = x_s[:-n]
    else:
        e[n:] = value
        e[:n] = x_s[-n:]
    return e

# plotting the first frame
graph = plt.plot(x,y)[0]
plt.ylim(-2,2)
plt.pause(1)

# the update loop
while(True):
    # updating the data
    sensor_data = get_sensor_data(i)
    y = shift(y, -1, sensor_data)
    
    # removing the older graph
    graph.remove()
    
    # plotting newer graph
    graph = plt.plot(x,y,color = 'g')[0]
    plt.xlim(x[0], x[-1])
    
    # calling pause function for 0.25 seconds
    plt.pause(0.25)
    i += 1