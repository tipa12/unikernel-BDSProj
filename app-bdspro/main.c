/* SPDX-License-Identifier: BSD-3-Clause */
/*
 * Authors: Simon Kuenzer <simon.kuenzer@neclab.eu>
 *
 * Copyright (c) 2019, NEC Laboratories Europe GmbH, NEC Corporation.
 *                     All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 3. Neither the name of the copyright holder nor the names of its
 *    contributors may be used to endorse or promote products derived from
 *    this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define LISTEN_PORT 8123

#define BUFLEN 2048
static char recvbuf[BUFLEN];
static char response_buffer[40];

int main(int argc __attribute__((unused)),
         char *argv[] __attribute__((unused))) {
  int rc = 0;
  int counter = 0;
  int srv, client;
  ssize_t n;
  struct sockaddr_in srv_addr;

  srv = socket(AF_INET, SOCK_STREAM, 0);
  if (srv < 0) {
    fprintf(stderr, "Failed to create socket: %d\n", errno);
    goto out;
  }

  srv_addr.sin_family = AF_INET;
  srv_addr.sin_addr.s_addr = INADDR_ANY;
  srv_addr.sin_port = htons(LISTEN_PORT);

  rc = bind(srv, (struct sockaddr *)&srv_addr, sizeof(srv_addr));
  if (rc < 0) {
    fprintf(stderr, "Failed to bind socket: %d\n", errno);
    goto out;
  }

  /* Accept one simultaneous connection */
  rc = listen(srv, 1);
  if (rc < 0) {
    fprintf(stderr, "Failed to listen on socket: %d\n", errno);
    goto out;
  }

  printf("Listening on port %d...\n", LISTEN_PORT);
  while (1) {
    client = accept(srv, NULL, 0);
    if (client < 0) {
      fprintf(stderr, "Failed to accept incoming connection: %d\n", errno);
      goto out;
    }

    /* Receive some bytes (ignore errors) */
    read(client, recvbuf, BUFLEN);

    if (!strncmp(recvbuf, "PING", 4)) {
      snprintf(response_buffer, sizeof(response_buffer) - 1, "PING%d",
               counter++);
      n = write(client, response_buffer, strlen(response_buffer) + 1);
    } else {
      n = write(client, "SAY PING!", sizeof("SAY PING!"));
    }

    if (n < 0)
      fprintf(stderr, "Failed to send a reply\n");
    else
      printf("Sent a reply\n");

    /* Close connection */
    close(client);
  }

out:
  return rc;
}
