import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation

plt.rcParams["figure.figsize"] = [7.50, 3.50]
plt.rcParams["figure.autolayout"] = True

fig = plt.figure()
ax = plt.axes(xlim=(0, 2), ylim=(-2, 2))
line, = ax.plot([], [], lw=2)

def init():
   line.set_data([], [])
   return line,

def read_sensor_data(i, x):
    return np.sin(2 * np.pi * (x - 0.01 * i))

def animate(i):
   x = np.linspace(0, 2, 1000)
   y = read_sensor_data(i, x)
   line.set_data(x, y)
   return line,

anim = animation.FuncAnimation(fig, animate, init_func=init, frames=200, interval=20, blit=True)
plt.show()
    


