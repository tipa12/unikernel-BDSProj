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
def generate_tuples(size, num_tuples, element_type, element_range):
    tuples = []
    for i in range(num_tuples):
        if element_type == "int":
            t = tuple([random.randint(element_range[0], element_range[1]) for j in range(size)])
        elif element_type == "float":
            t = tuple([random.uniform(element_range[0], element_range[1]) for j in range(size)])
        tuples.append(t)
    return tuples


tuples = generate_tuples(1, 1000000, "int", (-100, 100))
