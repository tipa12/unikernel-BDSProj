#pragma once

#include "stdint.h"
#include "stdio.h"
#include "stdlib.h"
#include "string.h"
#include "stdbool.h"
#include <uk/plat/time.h>

typedef struct {
    int a;
    int b;
    int c;
    int d;
    int e;
} TupleIn;

typedef enum {
    VALID,
    BACK,
    DONE,
    PARTIAL
} State;

typedef struct {
    State state;
    int number_of_bytes_consumed;
    union {
        TupleIn value;
    } data;
} SerializedItem;

typedef struct {
    int a;
    int b;
    int c;
    int d;
    int e;
    __nsec ts;
} TupleOut;


void print_data(const TupleIn *data);

TupleIn get_next_tuple(char *receive_buffer,
                     size_t receive_buffer_length,
                     bool *has_more,
                     bool *done,
                     bool *back_pressure);

void write_tuple(char *send_buffer, size_t *buffer_position, TupleOut* t);