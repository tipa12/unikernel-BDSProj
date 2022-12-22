# clean up
uuts=$(gcloud compute instances list --format='table(name,status,labels.list())' --zones=europe-west1-b | grep "uut=mirage-os" | cut -d' ' -f1 | tr '\n' ' ')
[[ ! -z "$uuts" ]] && echo "Deleting old instances: $uuts" && gcloud compute instances delete $uuts --zone=europe-west1-b || true
gcloud compute images delete test-operator --quiet || true
gsutil rm gs://mirage-os-binary/test_operator.tar.gz || true
rm test_operator.tar.gz || true

echo "Building and configuring the mirage os unikernel"
mirage configure -t virtio --dhcp true --addr 10.132.0.15
make depends
make

# create new image
echo "Building the RAW image"
${SOLO5_HOME}/scripts/virtio-mkimage/solo5-virtio-mkimage.sh -f tar -d -- test_operator.tar.gz dist/test-operator.virtio --ipv4-only=true
gsutil cp test_operator.tar.gz gs://mirage-os-binary/test_operator.tar.gz
gcloud compute images create test-operator \
    --project=bdspro \
    --source-uri=https://storage.googleapis.com/mirage-os-binary/test_operator.tar.gz

# launch instance
gcloud compute instances create mirage-test-operator \
    --image test-operator \
    --zone europe-west1-b \
    --machine-type f1-micro