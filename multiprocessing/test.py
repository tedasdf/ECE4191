from multiprocessing import Process 
import os 
import time
import random 

def info(title):
    print(title)
    print('module name:', __name__)
    print('parent process:', os.getppid())
    print('process id:', os.getpid())

def f(name):
    info(f'function f({name})')
    r = 0
    for i in range(0, 5):
        l = random.randrange(1, 5)
        for j in range(0, l *10000000):  # ← fix missing colon and parentheses
            r = r + j
        print(f'  {name} {i} {j}')

if __name__ == '__main__':
    random.seed()

    info('main line')
    execution = time.time()

    f('bob')
    f('fred')

    execution2 = time.time()
    timeon = execution2 - execution
    print('How long?', timeon)
