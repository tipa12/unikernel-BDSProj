//
// Created by ls on 11.02.23.
//

#ifdef __cplusplus
extern "C" {
#endif

#include <uk/print.h>
#include "tuple.h"

#include <uk/essentials.h>

void print_data(const TupleIn *data) {
    printf("Data:");
    printf("  a: %d", data->a);
    printf("  b: %d", data->b);
    printf("  c: %d", data->c);
    printf("  d: %d", data->d);
    printf("  e: %d\n", data->e);
}


SerializedItem serialized_tuple(char *zero_terminated_buffer) {
    if (!strncmp(zero_terminated_buffer, "BACK", 4)) {
        return (SerializedItem) {BACK, 4, {.value={0, 0, 0, 0, 0}}};
    } else if (!strncmp(zero_terminated_buffer, "DONE", 4)) {
        return (SerializedItem) {DONE, 4, {.value={0, 0, 0, 0, 0}}};
    }

    SerializedItem item = {VALID, 0, {.value={0, 0, 0, 0, 0}}};
    int parsed = sscanf(zero_terminated_buffer,
                        "{ \"a\" : %d , \"b\" : %d , \"c\" : %d , \"d\" : %d , \"e\" : %d } %n",
                        &item.data.value.a,
                        &item.data.value.b,
                        &item.data.value.c,
                        &item.data.value.d,
                        &item.data.value.e,
                        &item.number_of_bytes_consumed);

    if (parsed < 5 || item.number_of_bytes_consumed == 0) {
        return (SerializedItem) {PARTIAL, 0, {.value={0, 0, 0, 0, 0}}};
    } else {
        return item;
    }
}

#define OVERFLOW_BUFFER_SIZE 400LU

static size_t current_overflow = 0;
static char overflow[OVERFLOW_BUFFER_SIZE + 1];
static size_t buffer_position = 0;

// receive_buffer is expected to be zero-terminated
// receiver_buffer_length is the strlen() of the receive_buffer so not include the terminator
TupleIn
get_next_tuple(char *receive_buffer, size_t receive_buffer_length, bool *has_more, bool *done, bool *back_pressure) {
    *back_pressure = false;
    *done = false;
    *has_more = false;

    char *buffer = receive_buffer;
    size_t buffer_len = receive_buffer_length;


    // Usual case where NO overflow from the previous socket recv has to be taken into account
    // Advance the buffer by the last used buffer position.
    // 'receive_buffer' is guaranteed to be zero terminated
    if (current_overflow == 0) {
        buffer = &receive_buffer[buffer_position];
        buffer_len = receive_buffer_length - buffer_position;
    } else {
        // Use the overflow buffer and extend it with new socket data
        // We expect 400 bytes to be plenty for a single tuple
        memcpy(&overflow[current_overflow], receive_buffer,
               MIN(OVERFLOW_BUFFER_SIZE - current_overflow, receive_buffer_length));
        // swap buffer with overflow
        buffer = overflow;
        // recv_buffer could be larger than the OVERFLOW_BUFFER_SIZE
        buffer_len = MIN(OVERFLOW_BUFFER_SIZE, receive_buffer_length + current_overflow);
        // zero terminate the buffer
        overflow[buffer_len] = '\0';
    }

#ifndef CONFIG_NETWORK_PERFORMANCE_EVALUATION
    if (is_corrupted(buffer)) {
        printf("recv: %p, overflow: %p, using: %p\n", receive_buffer, overflow, buffer);
        printf("buffer is corrupted: %s", &buffer[buffer_position]);
        printf("%s\n", &buffer[buffer_position + 1024]);
        UK_ASSERT(false);
    }

    if (buffer_len != strlen(buffer)) {
        printf("b_len: %ld, strlen: %ld", buffer_len, strlen(buffer));
        UK_ASSERT(false);
    }
#endif //CONFIG_NETWORK_PERFORMANCE_EVALUATION

    SerializedItem item = serialized_tuple(buffer);
    switch (item.state) {
        case BACK:
            *back_pressure = true;
            buffer_position = 0;
            return item.data.value;
        case DONE:
            *done = true;
            buffer_position = 0;
            return item.data.value;
        case VALID:
            *has_more = true;
            buffer_position += item.number_of_bytes_consumed - current_overflow;
            current_overflow = 0;
            return item.data.value;
        case PARTIAL:
            *has_more = false;
            buffer_position = 0;
            current_overflow = buffer_len;
            memcpy(overflow, buffer, buffer_len);
            return item.data.value;
        default:
            UK_ASSERT(false);
    }

}

void write_tuple(char *send_buffer, size_t *buffer_position, TupleOut *t) {
    *buffer_position += snprintf(&send_buffer[*buffer_position], 1000,
                                 "{\"a\":%d,\"b\":%d,\"c\":%d,\"d\":%d,\"e\":%d, \"ts\": %ld}",
                                 t->a, t->b, t->c, t->d, t->e, t->ts);
}

#ifdef __cplusplus
};
#endif