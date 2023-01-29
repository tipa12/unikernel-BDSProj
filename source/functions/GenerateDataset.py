
import random
import timeit
import CustomGoogleCloudStorage  as gcs

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

def tupleToDict(tuple):
    return {str(i): val for i, val in enumerate(tuple)}

def generateDataset(messageData, logger):
    datasetId = messageData['datasetId']
    sizeOfTuples = messageData['sizeOfTuples']
    numberOfTuples = messageData['numberOfTuples']
    elementType = messageData['elementType']
    elementRangeStart = messageData['elementRangeStart']
    elementRangeEnd = messageData['elementRangeEnd']
    
    # generate tuples
    listOfTuples = generate_tuples(sizeOfTuples, numberOfTuples, elementType, (elementRangeStart, elementRangeEnd))

    # bucket name for cloud storage
    bucketName = 'datasetbucket3245'

    gcs.uploadObjectToCloudStorage(datasetId, listOfTuples, bucketName)
    gcs.updateFirestore('datasets', datasetId, {'uploadedToCloudStorage': True, "datasetFilename": datasetId + ".pkl"})

    return datasetId