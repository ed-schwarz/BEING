import matplotlib.pyplot as plt
import numpy as np
import SpektraBsi
import EvalBoard

plt.ion()  # turning interactive mode on

# preparing the data
size = 1000
number_sensors = 1
i = 0
y = np.zeros((1, size))
x = np.linspace(0, 2, size)



socket_addr = '192.168.001.79'
evalutb = SpektraBsi.BsiInstrument()
evalutb.last_address = socket_addr


bma280 = EvalBoard.BMA280(evalutb)
res = evalutb.open_bsi(socket_addr)
print(res)




def shift(x_s, n, value):
    e = np.empty_like(x_s)
    if n >= 0:
        e[:, :n] = value
        e[:, n:] = x_s[:, :-n]
    else:
        e[: ,n:] = value
        e[:, :n] = x_s[:, -n:]
    return e

# plotting the first frame
for j in range(number_sensors):
    y_plot = y[j, :]
    graph = plt.plot(x,y_plot, color='C0')[0]
plt.ylim(-2,2)
plt.show(block=False)
plt.pause(1)
sensor_data = bma280.getAcceleration('z')
print(sensor_data)

'''
# the update loop
while(True):
    # updating the data
    sensor_data = bma280.getAcceleration('z')
    print(sensor_data)
    y = shift(y, -1, sensor_data)
    
    # removing the older graph
    graph.remove()
    
    # plotting newer graph
    for j in range(number_sensors):
        y_plot = y[j, :]
        graph = plt.plot(x,y_plot, color='C0')[0]
    plt.xlim(x[0], x[-1])
    
    # calling pause function for 0.25 seconds
    plt.pause(0.005)
    i += 1
    '''