from multiprocessing import Process  # Simplistic comparison
import os
import time
import random

def info(title):
    print(title)
    print('module name:', __name__)
    print('parent process:', os.getppid())
    print('process id:', os.getpid())

def f(name):
    info('function f')
    r = 0
    for i in range(0, 5):
        l = random.randrange(1, 5)
        for j in range(0, l * 10000000):  # Use underscore for readability
            r = r + j
        print('hello', name, l)

if __name__ == '__main__':
    random.seed()

    info('main line')
    p = Process(target=f, args=('bob',))
    q = Process(target=f, args=('fred',))

    execution = time.time()
    p.start()
    q.start()
    p.join()
    q.join()
    execution2 = time.time()

    timeon = execution2 - execution
    print('How long?', timeon)
