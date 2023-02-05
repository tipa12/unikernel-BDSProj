import uuid
import datetime

def generateUniqueDatasetId():
    # Generate a unique ID
    uniqueId = str(uuid.uuid4())

    # Get the current date and time
    now = datetime.datetime.now()

    # Format the date and time as a string
    dateTimeStr = now.strftime("%Y-%m-%dT%H-%M-%S")

    # Concatenate the unique ID and the date/time string
    uniqueIdWithDateTime = 'ds_' + dateTimeStr + '-' + uniqueId

    return uniqueIdWithDateTime

def generateUniqueEvaluationId():
    # Generate a unique ID
    uniqueId = str(uuid.uuid4())

    # Get the current date and time
    now = datetime.datetime.now()

    # Format the date and time as a string
    dateTimeStr = now.strftime("%Y-%m-%dT%H-%M-%S")

    # Concatenate the unique ID and the date/time string
    uniqueIdWithDateTime = 'ev_' + dateTimeStr + '-' + uniqueId

    return uniqueIdWithDateTime

def generateUniqueExperimentId():
    # Generate a unique ID
    uniqueId = str(uuid.uuid4())

    # Get the current date and time
    now = datetime.datetime.now()

    # Format the date and time as a string
    dateTimeStr = now.strftime("%Y-%m-%dT%H-%M-%S")

    # Concatenate the unique ID and the date/time string
    uniqueIdWithDateTime = 'experiment_' + dateTimeStr + '-' + uniqueId

    return uniqueIdWithDateTime