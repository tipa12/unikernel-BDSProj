import CustomGoogleCloudStorage as gcs

def filterEvaluation(datasetId, filterValue, evaluationId):
    data = gcs.downloadDataset(datasetId)
    acceptedTuples = 0
    rejectedTuples = 0

    for tuple in data:
        if tuple[0] > filterValue:
            acceptedTuples += 1
        else:
            rejectedTuples += 1

    updateDict = {
        "acceptedTuples": acceptedTuples,
        "rejectedTuples": rejectedTuples
    }

    gcs.updateFirestore('evaluations', evaluationId, updateDict)

def mapEvaluation(datasetId, evaluationId):
    data = gcs.downloadDataset(datasetId)
    acceptedTuples = len(data)

    updateDict = {
        "acceptedTuples": acceptedTuples,
        "rejectedTuples": 0
    }

    gcs.updateFirestore('evaluations', evaluationId, updateDict)


def checkMessageData(messageData, logger):
    if 'datasetId' not in messageData:
        logger.error("No datasetId given")
        return False
    if 'unikernelFunction' not in messageData:
        logger.error("No unikernelFunction given")
        return False
    if 'evaluationId' not in messageData:
        logger.error("No evaluationId given")
        return False
    
    # check if all required fields are of correct type and log error + throw exception if not
    if not isinstance(messageData['datasetId'], str):
        logger.error("datasetId is not a string")
        return False
    if not isinstance(messageData['unikernelFunction'], str):
        logger.error("unikernelFunction is not a string")
        return False
    if not isinstance(messageData['evaluationId'], str):
        logger.error("evaluationId is not a string")
        return False
    if messageData['unikernelFunction'] not in ['map', 'filter']:
        logger.error("unikernelFunction is not 'map' or 'filter'")
        return False
    # TODO: makes sense but not implemented yet
    #if messageData['unikernelFunction'] == 'filter' and messageData['sizeOfTuples'] != 1:
    #    logger.error("unikernelFunction is 'filter' but sizeOfTuples is not 1")
    #    return False
    if messageData['unikernelFunction'] == 'filter' and 'filterValue' not in messageData:
        logger.error("unikernelFunction is 'filter' but no filterValue given")
        return False
    return True

def createEvaluation(messageData, logger):
    if not checkMessageData(messageData, logger):
        # TODO: throw exception
        return
    
    datasetId = messageData['datasetId']
    unikernelFunction = messageData['unikernelFunction']
    evaluationId = messageData['evaluationId']

    if unikernelFunction == 'filter':
        filterValue = messageData['filterValue']
        filterEvaluation(datasetId, filterValue, evaluationId)
    
    if unikernelFunction == 'map':
        mapEvaluation(datasetId, evaluationId)