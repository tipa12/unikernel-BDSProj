import random
import timeit

def measure_time(func):
    def wrapper(*args, **kwargs):
        start = timeit.default_timer()
        result = func(*args, **kwargs)
        end = timeit.default_timer()
        print(f"Time taken: {end - start:.6f} seconds")
        return result
    return wrapper


@measure_time
def generate_tuples(sizeOfTuples, numberOfTuples, elementType, elementRange):
    tuples = []
    for i in range(numberOfTuples):
        if elementType == "int":
            t = tuple([random.randint(elementRange[0], elementRange[1]) for j in range(sizeOfTuples)])
        elif elementType == "float":
            t = tuple([random.uniform(elementRange[0], elementRange[1]) for j in range(sizeOfTuples)])
        tuples.append(t)
    return tuples