import CustomGoogleCloudStorage as gcs

def evaluateDataset(datasetId, unikernelFunction, evaluationId):
    data = gcs.downloadDataset(datasetId)
    acceptedTuples = 0
    rejectedTuples = 0

    if unikernelFunction == 'filter':
        for tuple in data:
            if tuple[0] > 0:
                acceptedTuples += 1
            else:
                rejectedTuples += 1
    elif unikernelFunction == 'map':
        acceptedTuples = len(data)
    else:
        print("Error: Unikernel function not recognized")

    updateDict = {
        "acceptedTuples": acceptedTuples,
        "rejectedTuples": rejectedTuples
    }

    gcs.updateFirestore('evaluations', evaluationId, updateDict)

def createEvaluation(messageData, logger):
    if 'datasetId' not in messageData:
        logger.error("No datasetId given")
        return
    if 'unikernelFunction' not in messageData:
        logger.error("No unikernelFunction given")
        return
    if 'evaluationId' not in messageData:
        logger.error("No evaluationId given")
        return
    
    datasetId = messageData['datasetId']
    unikernelFunction = messageData['unikernelFunction']
    evaluationId = messageData['evaluationId']

    evaluateDataset(datasetId, unikernelFunction, evaluationId)