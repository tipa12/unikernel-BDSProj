####
####### This Script contains the standard functions for the Google Cloud Platform
####

import datetime
import json
import logging
import pickle
import time

# Imports the Google Cloud client library
from google.cloud import firestore
from google.cloud import storage
from google.cloud import logging as glogging


def updateFirestore(collection, documentId, updateDict):
    # Create a Firestore client
    db = firestore.Client(project="bdspro")

    # Create a new document in the "datasets" collection
    docRef = db.collection(collection).document(documentId)
    updateDict.update({'lastmodified': datetime.datetime.now()})

    # Set the data for the document
    docRef.update(updateDict)


def createFirestoreDocument(collection, documentId, setDict):
    # Create a Firestore client
    db = firestore.Client()
    # Create a new document in the "datasets" collection
    docRef = db.collection(collection).document(documentId)
    setDict.update({"created": datetime.datetime.now(), 'lastmodified': datetime.datetime.now()})
    # Set the data for the document
    docRef.set(setDict)


def uploadObjectToCloudStorage(uniqueFilename, objectToUpload, bucketName):
    # Writing to tmp folder
    with open("/tmp/" + uniqueFilename + ".pkl", "wb") as file:
        # Serialize the list
        pickle.dump(objectToUpload, file)

    # Create a storage client
    storageClient = storage.Client()
    # Get a reference to the bucket
    bucket = storageClient.bucket(bucketName)
    # bucket = storage_client.get_bucket(bucketName)

    blob = bucket.blob(uniqueFilename + ".pkl")
    blob.upload_from_filename("/tmp/" + uniqueFilename + ".pkl")


def downloadDataset(datasetId):
    # Set up the Cloud Storage client
    projectId = "bdspro"
    client = storage.Client(project=projectId)

    # Set the name of the bucket and the file to download
    bucketName = "datasetbucket3245"
    fileName = datasetId + ".pkl"

    # Use the client to download the file
    bucket = client.bucket(bucketName)
    blob = bucket.blob(fileName)
    file = blob.download_as_string()

    # Deserialize the data from the file
    data = pickle.loads(file)

    return data


def store_evaluation_in_bucket(logger: logging.Logger, evaluation_data: dict, prefix: str, test_id: str):
    projectId = "bdspro"
    client = storage.Client(project=projectId)
    # Set the name of the bucket and the file to download
    bucket_name = "evaluations-1"
    bucket = client.bucket(bucket_name)

    file_name = f"{prefix}_{test_id}.json"
    json_data = json.dumps(evaluation_data)
    blob = bucket.blob(file_name)
    blob.upload_from_string(json_data)
    logger.info(f"Evaluation was saved in Bucket: /evaluations/{file_name}")


def store_evaluation(logger: logging.Logger, evaluation_data: dict, test_id: str):
    # Create a Firestore client
    db = firestore.Client()
    # Create a new document in the "datasets" collection
    evaluation_collection = db.collection("evaluations")
    evaluation_collection.add(
        {"created": datetime.datetime.now(), 'data': evaluation_data}, str(test_id))

    logger.info(f"Evaluation was saved in Firestore: /evaluations/{test_id}")


def convert_to_timestamp(perf_counter_timestamp: float) -> str:
    # convert the seconds to a UTC timestamp
    timestamp = datetime.datetime.utcfromtimestamp(perf_counter_timestamp + time.time() - time.perf_counter())

    return timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')


def get_google_cloud_network_packet_logs(unikernel_ip: str, timestamp_start: float, timestamp_stop: float):
    project_id = "bdspro"
    client = glogging.Client(project=project_id)

    # select a log to filter
    logger = client.logger("packet_logger")

    # determine the number of seconds elapsed between the arbitrary point in time and the Unix epoch

    filter_string = f"logName:(\"projects/bdspro/logs/compute.googleapis.com%2Fvpc_flows\") AND resource.labels.subnetwork_id:(288955683349170046) AND (jsonPayload.connection.dest_ip:(\"{unikernel_ip}\") OR jsonPayload.connection.src_ip:(\"{unikernel_ip}\")) AND jsonPayload.start_time >= \"{convert_to_timestamp(timestamp_start)}\" AND jsonPayload.end_time < \"{convert_to_timestamp(timestamp_stop)}\""
    filter_string = f"logName:(\"projects/bdspro/logs/compute.googleapis.com%2Fvpc_flows\")"
    print(filter_string)
    # retrieve log entries using the filter
    return list(logger.list_entries(filter_=filter_string))
