## Test Bench
### Setup
use the cloudbuild.yaml to set up the images and VMs in GCP. To run all at once you can use the deploy script
> ./deploy.sh --build-common


### Start the query
you can start a query using the following url. Query parameters are described within the paper, and can be modified.
> curl http://<EXTERNAL_IP_OF_FLASK_API>/newExperiment?datasetId=ds-20230105165324-976bcf5a-f8ef-41c3-b447-7fe8463b48f2&datasetId=ev-20230105171701-139e6756-4e45-48c6-a277-8acc90edf25d&delay=0&iterations=500&imageName=unikraft-filter&githubToken=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&sourceAddress=10.156.0.54&sourcePort=8081&sinkAddress=10.156.0.56&sinkPort=8081&controlAddress=10.156.0.52&controlPort=8081&operator=filter&forceRebuild=false&restarts=100&tupleFormat=json&sampleRate=100

The `logs.sh` script shows the logs of source, sink, and control. At the end of the experiment the results are uploaded to gcloud.
