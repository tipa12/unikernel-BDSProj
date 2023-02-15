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
#include <stdbool.h>
#include <time.h>
#include <errno.h>
#include <uk/plat/time.h>

#include "network.h"
#include "tuple.h"

bool filter_operator(TupleIn *tupl) {
    return tupl->a > 0;
}

TupleOut map_operator(TupleIn *tupl) {
    return (TupleOut) {tupl->a, tupl->b, tupl->c, tupl->d, tupl->e, ukplat_monotonic_clock()};
}


#define RECEIVE_BUFFER_SIZE 2048
// generous with the send buffer, as map may increase the total json size
#define SEND_BUFFER_SIZE (RECEIVE_BUFFER_SIZE * 2)
char receive_buffer[RECEIVE_BUFFER_SIZE + 1];
char send_buffer[SEND_BUFFER_SIZE];

int is_corrupted(char *buffer) {
    int open = 0;
    int close = 0;
    int i = 0;
    while (buffer[i] != '\0') {
        if (buffer[i] == '{') open++;
        if (buffer[i] == '}') close++;
        UK_ASSERT(i <= RECEIVE_BUFFER_SIZE);
        i++;
    }
    int diff = open - close;
    diff = diff < 0 ? -diff : diff;

    return diff > 1;
}

int process_tuples() {
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

    if (source_fd < 0 || destination_fd < 0) {
        fprintf(stderr, "Failed to connect to source or destination: %d, %d\n", source_fd, destination_fd);
        goto end;
    }

    const char *request_tuple_message = "SEND TUPLES!";
    size_t request_tuple_message_len = strlen(request_tuple_message);

    rc = send(source_fd, request_tuple_message, request_tuple_message_len, 0);

    if (rc < 0) {
        fprintf(stderr, "Failed to send request for tuples: %d\n", rc);
        goto close;
    }


    start_timestamp = ukplat_monotonic_clock();
    while (1) {
        rc = recv(source_fd, receive_buffer, RECEIVE_BUFFER_SIZE, 0);

        if (rc < 0) {
            uk_pr_crit("Source was closed: %d\n", rc);
            goto close;
        }

        total_number_of_bytes_received += rc;

        // zero terminate receive_buffer
        receive_buffer[rc] = '\0';
#ifndef CONFIG_NETWORK_PERFORMANCE_EVALUATION
        if (is_corrupted(receive_buffer)) {
            uk_pr_crit("Receive buffer appears to be corrupted\n");
        }
#endif //CONFIG_NETWORK_PERFORMANCE_EVALUATION
        bool is_done = false;
        bool has_more = false;
        bool adjust_backpressure = false;
        size_t current_send_buffer_position = 0;

        while (true) {
            TupleIn current_tuple = get_next_tuple(receive_buffer, rc, &has_more, &is_done, &adjust_backpressure);


            if (is_done) {
                if (current_send_buffer_position > 0)
                    send(destination_fd, send_buffer, current_send_buffer_position, 0);

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
                rc = send(source_fd, "ACK", strlen("ACK"), 0);
                break;
            }

            if (!has_more) break;

            total_number_of_tuples_received++;
            if (current_tuple.b != next_tuple_id) {
                UK_ASSERT(false);
                skipped++;
            }
            next_tuple_id = current_tuple.b + 1;

#ifdef CONFIG_APPTESTOPERATOR_DBG_SHOW_TUPLES
            print_data(&current_tuple);
#endif
            if (filter_operator(&current_tuple)) {
                number_of_tuples_passing++;
                TupleOut t_out = map_operator(&current_tuple);
                write_tuple(send_buffer, &current_send_buffer_position, &t_out);
            }
        }

#ifndef CONFIG_NETWORK_PERFORMANCE_EVALUATION
        printf("%ld\n", current_send_buffer_position);
        send_buffer[current_send_buffer_position] = '\0';
        if (is_corrupted(send_buffer)) {
            printf("send_buffer is corrupted\n");
            printf("send_buffer: %s\n", send_buffer);
            UK_ASSERT(false);
        }
#endif //CONFIG_NETWORK_PERFORMANCE_EVALUATION

        send(destination_fd, send_buffer, current_send_buffer_position, 0);
    }


    close:
    uk_pr_crit(
            "Total Number of Bytes Received %ld\nNumber of Tuples Process: %ld of which %ld passed the predicate!\nSkipped Tuples: %ld\nLast TupleID: %d\n",
            total_number_of_bytes_received, total_number_of_tuples_received, number_of_tuples_passing, skipped,
            next_tuple_id - 1);

    __nsec sec = ukarch_time_nsec_to_sec(stop_timestamp - start_timestamp);
    __nsec rem_usec = ukarch_time_subsec(stop_timestamp - start_timestamp);

    uk_pr_crit("%ld.%08lds passed after the first tuple received\n", sec, rem_usec);
    uk_pr_crit("%ldns passed after the first tuple received\n", stop_timestamp - start_timestamp);
    uk_pr_crit("start: %ld, stop: %ld\n", start_timestamp, stop_timestamp);
    stats_display();
    close(source_fd);
    close(destination_fd);
    end:
    return rc;
}

static void millisleep(unsigned int millisec) {
    struct timespec ts;
    int ret;

    ts.tv_sec = millisec / 1000;
    ts.tv_nsec = (millisec % 1000) * 1000000;
    do
        ret = nanosleep(&ts, &ts);
    while (ret && errno == EINTR);
}

int main(int argc __attribute__((unused)),
         char *argv[] __attribute__((unused))) {
    struct netif *netif = netif_find("en1");
    while (netif_dhcp_data(netif)->state != 10) {
        millisleep(1);
    }

    uk_pr_crit("DHCP Ready\n");
    sent_boot_packet();
    millisleep(1000);
    process_tuples();
    return 0;
}
