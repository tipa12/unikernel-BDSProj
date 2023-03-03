## NES Evaluation
### Setup
use the cloudbuild.yaml to set up the images and VMs in GCP
> gcloud builds submit --config=./cloudbuild.yaml

### Start the query
> curl -d@query.json http://<EXTERNAL_IP_OF_COORDINATOR>/v1/nes/query/execute-query

You can use the logs.sh script to view the logs of the VMs
the CSV file will be written to `result.csv` in the coordinator container, which can then be copied onto your local machine for further evaluation.

### NES Modifications
Since the NES Source Repository is not public, the NES modifications are only available in a docker image.

Using the logical tuple source description of 6 ints will overwrite the attributes b,c, and d with timestamps t2, t3, and t4 

### Tuple Source
The tuple source waits for a TCP connection. Once connected, the Dataset will be sent to the worker.
The Selectivity can be modified by changing the Dataset or sending a fixed constant for the f attribute.
