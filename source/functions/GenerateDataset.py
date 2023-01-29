
import random
import timeit
import CustomGoogleCloudStorage  as gcs

def measure_time(func):
    def wrapper(*args, **kwargs):
        start = timeit.default_timer()
        result = func(*args, **kwargs)
        end = timeit.default_timer()
        print(f"Time taken to generate Dataset: {end - start:.6f} seconds")
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

def checkMessageData(messageData, logger):
    # check if all required fields are present and log error + throw exception if not
    if 'datasetId' not in messageData:
        logger.error("No datasetId given")
        return
    if 'sizeOfTuples' not in messageData:
        logger.error("No sizeOfTuples given")
        return
    if 'numberOfTuples' not in messageData:
        logger.error("No numberOfTuples given")
        return
    if 'elementType' not in messageData:
        logger.error("No elementType given")
        return
    if 'elementRangeStart' not in messageData:
        logger.error("No elementRangeStart given")
        return
    if 'elementRangeEnd' not in messageData:
        logger.error("No elementRangeEnd given")
        return
    
    # check if all required fields are of correct type and log error + throw exception if not
    if not isinstance(messageData['datasetId'], str):
        logger.error("datasetId is not a string")
        return
    if not isinstance(messageData['sizeOfTuples'], int):
        logger.error("sizeOfTuples is not an integer")
        return
    if not isinstance(messageData['numberOfTuples'], int):
        logger.error("numberOfTuples is not an integer")
        return
    if not isinstance(messageData['elementType'], str):
        logger.error("elementType is not a string")
        return
    if not messageData['elementType'] in ['int', 'float']:
        logger.error("elementType is not a valid type")
        return
    if not isinstance(messageData['elementRangeStart'], int) and not isinstance(messageData['elementRangeStart'], float):
        logger.error("elementRangeStart is not a number")
        return
    if not isinstance(messageData['elementRangeEnd'], int) and not isinstance(messageData['elementRangeEnd'], float):
        logger.error("elementRangeEnd is not a number")
        return
    if messageData['elementRangeStart'] > messageData['elementRangeEnd']:
        logger.error("elementRangeStart is greater than elementRangeEnd")
        return
    
    return True

def generateDataset(messageData, logger):
     # check if all required fields are present and log error
    if not checkMessageData(messageData, logger):
        # TODO: throw exception
        return

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

    try:
        gcs.uploadObjectToCloudStorage(datasetId, listOfTuples, bucketName)
        gcs.updateFirestore('datasets', datasetId, {'uploadedToCloudStorage': True, "datasetFilename": datasetId + ".pkl"})
    except Exception as e:
        logger.error("Error uploading dataset with id: {} to cloud storage".format(datasetId))
        logger.error(e)
    
    logger.info("Dataset with id: {} generated".format(datasetId))

    return datasetId