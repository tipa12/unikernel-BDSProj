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

#define BUFLEN (sizeof(tuple) * 50)
static char recvbuf[BUFLEN];
static tuple tuple_buffer[BUFLEN / sizeof(tuple)];

void print_data(const tuple* data)
{
    printf("Data:\n");
    printf("  a: %d\n", data->a);
    printf("  b: %d\n", data->b);
    printf("  c: %d\n", data->c);
    printf("  d: %d\n", data->d);
    printf("  e: %d\n", data->e);
}


size_t serialize_tuples(char *buffer, size_t buffer_len, tuple *tuples)
{
	int number_of_tuples = buffer_len / sizeof(tuple);

	for (int i = 0; i < number_of_tuples; i++)
	{
		memcpy(&tuples[i], &buffer[i * sizeof(tuple)], sizeof(tuple));
	}

	for (int i = 0; i < number_of_tuples; i++)
	{
		tuples[i].a = ntohl(tuples[i].a);
		tuples[i].b = ntohl(tuples[i].b);
		tuples[i].c = ntohl(tuples[i].c);
		tuples[i].d = ntohl(tuples[i].d);
		tuples[i].e = ntohl(tuples[i].e);
	}

	return number_of_tuples;
}

void deserialize_tuple(char *buffer, size_t *buffer_size, const tuple *data)
{
    tuple data_copy = *data;
    data_copy.a = htonl(data_copy.a);
    data_copy.b = htonl(data_copy.b);
    data_copy.c = htonl(data_copy.c);
    data_copy.d = htonl(data_copy.d);
    data_copy.e = htonl(data_copy.e);

    size_t data_size = sizeof(tuple);
    memcpy(buffer + *buffer_size, &data_copy, data_size);
    *buffer_size += data_size;
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


	rc = recv(source_fd, recvbuf, BUFLEN, 0);
	start_timestamp = ukplat_monotonic_clock();

	while (1)
	{
		if (rc < 0)
		{
			fprintf(stderr, "Failed to receive: %d\n", rc);
			stop_timestamp = ukplat_monotonic_clock();
			goto close;
		}
		total_number_of_bytes_received += rc;

		size_t number_of_tuples = serialize_tuples(recvbuf, rc, tuple_buffer);
		size_t send_buffer_length = 0;

		for (size_t i = 0; i < number_of_tuples; i++)
		{
			total_number_of_tuples_received++;

			if(tuple_buffer[i].b != next_tuple_id) {
				skipped++;
			}
			next_tuple_id = tuple_buffer[i].b + 1;

#ifdef CONFIG_APPTESTOPERATOR_DBG_SHOW_TUPLES
			print_data(&tuple_buffer[i]);
#endif

			if (filter_operator(&tuple_buffer[i]))
			{
				number_of_tuples_passing++;
				deserialize_tuple(recvbuf, &send_buffer_length, &tuple_buffer[i]);
			}
		}


		if (send_buffer_length > 0)
		{
			rc = send(destination_fd, recvbuf, send_buffer_length, 0);
			if (rc < 0)
			{
				fprintf(stderr, "Failed to send: %d\n", rc);
				goto close;
			}
		}

		rc = recv(source_fd, recvbuf, BUFLEN, 0);
	}

close:
	uk_pr_crit("Total Number of Bytes Received %ld\nNumber of Tuples Process: %ld of which %ld passed the predicate!\nSkipped Tuples: %ld\n", total_number_of_bytes_received, total_number_of_tuples_received, number_of_tuples_passing, skipped);

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
