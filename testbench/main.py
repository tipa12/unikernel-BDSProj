import time

from testbench.common.CustomGoogleCloudStorage import get_google_cloud_network_packet_logs

print(get_google_cloud_network_packet_logs("10.132.15.220", time.perf_counter() - 2000, time.perf_counter()))