/* Import user configuration: */
#ifdef __Unikraft__
#include <uk/config.h>
#endif /* __Unikraft__ */

#include <stdio.h>
#include <lwip/netif.h>
#include <lwip/stats.h>
#include <lwip/ip.h>
#include <lwip/dhcp.h>
#include <lwip/timeouts.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <time.h>
#include <errno.h>
#include <uk/plat/time.h>

typedef struct
{
	int a;
	int b;
	int c;
	int d;
	int e;
} tuple;


void print_data(const tuple* data)
{
    printf("Data:");
    printf("  a: %d", data->a);
    printf("  b: %d", data->b);
    printf("  c: %d", data->c);
    printf("  d: %d", data->d);
    printf("  e: %d\n", data->e);
}


int serialize_tuple(int buffer_len, tuple *tuple_buf, bool* is_done, bool* back_pressure)
{

	if(buffer_len == sizeof(tuple)) {
		tuple_buf->a = ntohl(tuple_buf->a);
		tuple_buf->b = ntohl(tuple_buf->b);
		tuple_buf->c = ntohl(tuple_buf->c);
		tuple_buf->d = ntohl(tuple_buf->d);
		tuple_buf->e = ntohl(tuple_buf->e);
		return 0;
	} else if(buffer_len == 4) {
		if(!strncmp((char*) tuple_buf, "DONE", 4)) {
			*is_done = true;
		} else if(!strncmp((char*) tuple_buf, "BACK", 4)) {
			*back_pressure = true;
		}
		return 0;
	} else {
		return sizeof(tuple) - buffer_len;
	}
}

void deserialize_tuple(tuple *tuple_buf)
{
    tuple_buf->a = htonl(tuple_buf->a);
    tuple_buf->b = htonl(tuple_buf->b);
    tuple_buf->c = htonl(tuple_buf->c);
    tuple_buf->d = htonl(tuple_buf->d);
    tuple_buf->e = htonl(tuple_buf->e);
}

int sent_boot_packet()
{
	int srv;
	int rc = 0;
	struct sockaddr_in srv_addr;

	srv_addr.sin_family = AF_INET;
	lwip_inet_pton(AF_INET, CONFIG_APPTESTOPERATOR_TESTBENCH_ADDR, &srv_addr.sin_addr.s_addr);
	srv_addr.sin_port = htons(CONFIG_APPTESTOPERATOR_TESTBENCH_PORT);

	srv = socket(AF_INET, SOCK_DGRAM, 0);

	if (srv < 0)
	{
		fprintf(stderr, "Failed to create UDP socket: %d\n", errno);
		goto out;
	}

	const char *boot_message = "BOOTED!";
	size_t boot_message_len = strlen(boot_message);

	rc = sendto(srv, boot_message, boot_message_len, 0, (const struct sockaddr *)&srv_addr, sizeof(struct sockaddr_in));
	printf("Boot package sent to %s:%d!\n", CONFIG_APPTESTOPERATOR_TESTBENCH_ADDR, CONFIG_APPTESTOPERATOR_TESTBENCH_PORT);
	if (rc < 0)
	{
		fprintf(stderr, "Failed to send a reply\n");
		goto out;
	}

	close(srv);

out:
	return rc;
}

int filter_operator(tuple *tupl)
{
	return tupl->a > 0;
}

int connect_source()
{
	int source_fd;
	int rc = 0;
	struct sockaddr_in src_addr;

	src_addr.sin_family = AF_INET;
	lwip_inet_pton(AF_INET, CONFIG_APPTESTOPERATOR_SOURCE_ADDR, &src_addr.sin_addr.s_addr);
	src_addr.sin_port = htons(CONFIG_APPTESTOPERATOR_SOURCE_PORT);

	printf("Connecting to Source %s:%d\n", CONFIG_APPTESTOPERATOR_SOURCE_ADDR, CONFIG_APPTESTOPERATOR_SOURCE_PORT);
	source_fd = socket(AF_INET, SOCK_STREAM, 0);

	if (source_fd < 0)
	{
		fprintf(stderr, "Failed to create TCP socket: %d\n", errno);
		goto end;
	}

	rc = connect(source_fd, (const struct sockaddr *) &src_addr, sizeof(struct sockaddr_in));

	if (rc < 0)
	{
		fprintf(stderr, "Failed to Connect: %d\n", rc);
		goto close;
	}

	printf("Connected to Source!\n");
	return source_fd;

close:
	close(source_fd);
end:
	return rc;
}

int connect_destination()
{
	int destination_fd;
	int rc = 0;
	struct sockaddr_in src_addr;

	src_addr.sin_family = AF_INET;
	lwip_inet_pton(AF_INET, CONFIG_APPTESTOPERATOR_DESTINATION_ADDR, &src_addr.sin_addr.s_addr);
	src_addr.sin_port = htons(CONFIG_APPTESTOPERATOR_DESTINATION_PORT);

	printf("Connecting to Destination %s:%d\n", CONFIG_APPTESTOPERATOR_DESTINATION_ADDR, CONFIG_APPTESTOPERATOR_DESTINATION_PORT);
	destination_fd = socket(AF_INET, SOCK_STREAM, 0);

	if (destination_fd < 0)
	{
		fprintf(stderr, "Failed to create TCP socket: %d\n", errno);
		goto end;
	}

	rc = connect(destination_fd, (const struct sockaddr *) &src_addr, sizeof(struct sockaddr_in));

	if (rc < 0)
	{
		fprintf(stderr, "Failed to Connect: %d\n", rc);
		goto close;
	}

	printf("Connected to Destination!\n");
	return destination_fd;

close:
	close(destination_fd);
end:
	return rc;
}

int process_tuples()
{
	int rc = 0;
	int source_fd = connect_source();
	int destination_fd = connect_destination();
	size_t total_number_of_tuples_received = 0;
	size_t number_of_tuples_passing = 0;
	size_t total_number_of_bytes_received = 0;
	int next_tuple_id = 0;
	__nsec start_timestamp = -1;
	__nsec stop_timestamp = -1;
	size_t skipped = 0;

	if (source_fd < 0 || destination_fd < 0)
	{
		fprintf(stderr, "Failed to connect to source or destination: %d, %d\n", source_fd, destination_fd);
		goto end;
	}

	const char *request_tuple_message = "SEND TUPLES!";
	size_t request_tuple_message_len = strlen(request_tuple_message);

	rc = send(source_fd, request_tuple_message, request_tuple_message_len, 0);

	if (rc < 0)
	{
		fprintf(stderr, "Failed to send request for tuples: %d\n", rc);
		goto close;
	}


	tuple current_tuple;

	rc = recv(source_fd, &current_tuple, sizeof(tuple), 0);
	start_timestamp = ukplat_monotonic_clock();

	while (1)
	{
		if (rc < 0)
		{
			fprintf(stderr, "Source was closed: %d", rc);
			goto close;
		}

		total_number_of_bytes_received += rc;

		bool is_done = false;
		bool adjust_backpressure = false;

		int more_bytes = 0;
		do {
			more_bytes = serialize_tuple(rc, &current_tuple, &is_done, &adjust_backpressure);

			if(more_bytes == 0)
				break;

			rc += recv(source_fd, ((void*)&current_tuple) + sizeof(tuple) - more_bytes, more_bytes, 0);
		}while(true);


		if(is_done) {

			stop_timestamp = ukplat_monotonic_clock();
			uk_pr_crit("Data stream was closed, terminating connections\n");
			uk_pr_crit("Sending 'DONE' package to destination\n");
			rc = send(destination_fd, "DONE", strlen("DONE"), 0);
			uk_pr_crit("Sending 'ACK' package to source\n");
			rc = send(source_fd, "ACK", strlen("ACK"), 0);
			uk_pr_crit("Waiting for 'ACK' package from destination\n");
			char ack[3];
			rc = recv(destination_fd, &ack, 3, 0);
			uk_pr_crit("Received 'ACK' package from destination\n");

			goto close;

		} else if (adjust_backpressure) {
			uk_pr_crit("Backpressure Adjusted\n");
			rc = send(source_fd, "ACK", strlen("ACK"), 0);
		} else {
			total_number_of_tuples_received++;
			if(current_tuple.b != next_tuple_id) {
				print_data(&current_tuple);
				printf("rc: %d\n", rc);
				uk_pr_crit("skipped %d to %d\n", next_tuple_id, current_tuple.b);
				skipped++;
			}
			next_tuple_id = current_tuple.b + 1;

	#ifdef CONFIG_APPTESTOPERATOR_DBG_SHOW_TUPLES
				print_data(&current_tuple);
	#endif
			if (filter_operator(&current_tuple))
			{
				number_of_tuples_passing++;
				deserialize_tuple(&current_tuple);
				send(destination_fd,&current_tuple, sizeof(tuple),0 );
			}
		}


		rc = recv(source_fd, &current_tuple, sizeof(tuple), 0);
	}



close:
	uk_pr_crit("Total Number of Bytes Received %ld\nNumber of Tuples Process: %ld of which %ld passed the predicate!\nSkipped Tuples: %ld\nLast TupleID: %d\n", total_number_of_bytes_received, total_number_of_tuples_received, number_of_tuples_passing, skipped, next_tuple_id-1);

	__nsec sec = ukarch_time_nsec_to_sec(stop_timestamp - start_timestamp);
	__nsec rem_usec = ukarch_time_subsec(stop_timestamp - start_timestamp);

	uk_pr_crit("%ld:%8lds passed after the first tuple received\n", sec, rem_usec);
	uk_pr_crit("%ldns passed after the first tuple received\n", stop_timestamp - start_timestamp);
	uk_pr_crit("start: %ld, stop: %ld\n", start_timestamp, stop_timestamp);
	stats_display();
	close(source_fd);
	close(destination_fd);
end:
	return rc;
}

static void millisleep(unsigned int millisec)
{
	struct timespec ts;
	int ret;

	ts.tv_sec = millisec / 1000;
	ts.tv_nsec = (millisec % 1000) * 1000000;
	do
		ret = nanosleep(&ts, &ts);
	while (ret && errno == EINTR);
}

int main(int argc __attribute__((unused)),
		 char *argv[] __attribute__((unused)))
{
	struct netif *netif = netif_find("en1");
	while (netif_dhcp_data(netif)->state != 10)
	{
		millisleep(1);
	}

	uk_pr_crit("DHCP Ready\n");
	sent_boot_packet();
	millisleep(1000);
	process_tuples();
	return 0;
}
